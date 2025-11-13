from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional, Set

import asyncpg
import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.core.logging import get_logger
from app.deps.admin_auth import AdminUser, verify_admin_user
from services.db_service import fetchrow


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


