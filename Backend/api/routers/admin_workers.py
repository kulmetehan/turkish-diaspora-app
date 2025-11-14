from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Set
from uuid import UUID

import asyncpg
import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.core.logging import get_logger
from app.deps.admin_auth import AdminUser, verify_admin_user
from services.db_service import fetchrow
from services.worker_runs_service import get_worker_run, list_worker_runs


router = APIRouter(
    prefix="/admin/workers",
    tags=["admin-workers"],
)

BOT_CHOICES = {"discovery", "classify", "verify", "monitor"}

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
CITIES_PATH = REPO_ROOT / "Infra" / "config" / "cities.yml"
CATEGORIES_PATH = REPO_ROOT / "Infra" / "config" / "categories.yml"

logger = get_logger()


class WorkerRunRequest(BaseModel):
    bot: str
    city: Optional[str] = None
    category: Optional[str] = None

    @field_validator("bot")
    @classmethod
    def validate_bot(cls, value: str) -> str:
        bot_norm = value.strip().lower()
        if bot_norm not in BOT_CHOICES:
            raise ValueError("unsupported bot")
        return bot_norm

    @field_validator("city")
    @classmethod
    def validate_city(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        city_key = value.strip()
        if city_key and city_key not in get_city_keys():
            raise ValueError("unknown city")
        return city_key or None

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        category_key = value.strip()
        if category_key and category_key not in get_category_keys():
            raise ValueError("unknown category")
        return category_key or None


def _load_yaml_keys(path: Path, key: str) -> Set[str]:
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Config file not found: {path}",
        )
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load config file {path}: {exc}",
        ) from exc
    section = data.get(key)
    if not isinstance(section, dict):
        return set()
    return set(section.keys())


@lru_cache(maxsize=1)
def get_city_keys() -> Set[str]:
    return _load_yaml_keys(CITIES_PATH, "cities")


@lru_cache(maxsize=1)
def get_category_keys() -> Set[str]:
    return _load_yaml_keys(CATEGORIES_PATH, "categories")


@router.post(
    "/run",
    status_code=status.HTTP_201_CREATED,
)
async def create_worker_run(
    body: WorkerRunRequest,
    admin: AdminUser = Depends(verify_admin_user),
) -> dict:
    try:
        row = await fetchrow(
            """
            INSERT INTO worker_runs (bot, city, category)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            body.bot,
            body.city,
            body.category,
        )
    except asyncpg.UndefinedTableError:
        logger.warning("worker_runs_table_missing", table="worker_runs")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "run_id": None,
                "bot": body.bot,
                "city": body.city,
                "category": body.category,
                "tracking_available": False,
                "detail": "worker_runs table is missing; worker run tracking is not available yet.",
            },
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "worker_run_insert_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create worker run",
        ) from exc

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create worker run",
        )
    run_id = row.get("id")
    return {
        "run_id": str(run_id),
        "bot": body.bot,
        "city": body.city,
        "category": body.category,
        "tracking_available": True,
    }


class WorkerRunListItem(BaseModel):
    id: UUID
    bot: str
    city: Optional[str]
    category: Optional[str]
    status: str
    progress: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_seconds: Optional[float] = None


class WorkerRunListResponse(BaseModel):
    items: List[WorkerRunListItem]
    total: int
    limit: int
    offset: int


class WorkerRunDetail(BaseModel):
    id: UUID
    bot: str
    city: Optional[str]
    category: Optional[str]
    status: str
    progress: int
    counters: Optional[dict]
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime
    duration_seconds: Optional[float] = None
    parameters: Optional[dict] = None


@router.get("/runs", response_model=WorkerRunListResponse)
async def list_worker_runs_endpoint(
    bot: Optional[str] = Query(default=None, description="Filter by bot name"),
    status: Optional[str] = Query(default=None, description="Filter by run status"),
    since: Optional[str] = Query(default=None, description="ISO timestamp; only runs started_at >= since"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    admin: AdminUser = Depends(verify_admin_user),
) -> WorkerRunListResponse:
    """
    List worker runs with optional filtering and pagination.
    """
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=400,
                detail="Invalid 'since' timestamp format. Use ISO 8601 format.",
            )

    try:
        runs, total = await list_worker_runs(
            bot=bot,
            status=status,
            since=since_dt,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.error("list_worker_runs_endpoint_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list worker runs",
        ) from exc

    items = []
    for run in runs:
        # Compute duration
        started = run.get("started_at")
        finished = run.get("finished_at")
        duration = None
        if started and finished and isinstance(started, datetime) and isinstance(finished, datetime):
            duration = (finished - started).total_seconds()

        items.append(
            WorkerRunListItem(
                id=run["id"],
                bot=run["bot"],
                city=run.get("city"),
                category=run.get("category"),
                status=run["status"],
                progress=run.get("progress", 0),
                started_at=started,
                finished_at=finished,
                duration_seconds=duration,
            )
        )

    return WorkerRunListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/runs/{run_id}", response_model=WorkerRunDetail)
async def get_worker_run_detail(
    run_id: UUID,
    admin: AdminUser = Depends(verify_admin_user),
) -> WorkerRunDetail:
    """
    Get detailed information about a specific worker run.
    """
    try:
        run = await get_worker_run(run_id)
    except Exception as exc:
        logger.error("get_worker_run_detail_failed", run_id=str(run_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch worker run",
        ) from exc

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker run {run_id} not found",
        )

    # Compute duration
    started = run.get("started_at")
    finished = run.get("finished_at")
    duration = None
    if started and finished and isinstance(started, datetime) and isinstance(finished, datetime):
        duration = (finished - started).total_seconds()

    # Derive parameters
    params = {}
    if run.get("city"):
        params["city"] = run["city"]
    if run.get("category"):
        params["category"] = run["category"]
    counters = run.get("counters")
    if counters and isinstance(counters, dict):
        for key in ["limit", "chunks", "chunk_index", "min_confidence", "model"]:
            if key in counters:
                params[key] = counters[key]

    return WorkerRunDetail(
        id=run["id"],
        bot=run["bot"],
        city=run.get("city"),
        category=run.get("category"),
        status=run["status"],
        progress=run.get("progress", 0),
        counters=counters,
        error_message=run.get("error_message"),
        started_at=started,
        finished_at=finished,
        created_at=run["created_at"],
        duration_seconds=duration,
        parameters=params if params else None,
    )


