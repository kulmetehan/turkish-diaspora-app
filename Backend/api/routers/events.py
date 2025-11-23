from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

import yaml
from fastapi import APIRouter, HTTPException, Query

from app.models.events_public import EventsListResponse
from services.event_categories_service import get_event_category_keys
from services.events_public_service import list_public_events

try:
    from app.workers.discovery_bot import load_cities_config
except ImportError:  # pragma: no cover - fallback for runtime environments without worker module

    def load_cities_config() -> Dict[str, Any]:
        config_path = Path(__file__).resolve().parents[3] / "Infra" / "config" / "cities.yml"
        with config_path.open("r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
        if not isinstance(data, dict):
            raise ValueError("cities.yml must contain a top-level object")
        return data


router = APIRouter(
    prefix="/events",
    tags=["events"],
)


@lru_cache(maxsize=1)
def _city_keys() -> Set[str]:
    cfg = load_cities_config()
    cities = (cfg or {}).get("cities") or {}
    keys: Set[str] = set()
    for raw_key in cities.keys():
        normalized = str(raw_key or "").strip().lower().replace(" ", "_")
        if normalized:
            keys.add(normalized)
    return keys


@lru_cache(maxsize=1)
def _category_keys() -> Set[str]:
    return set(get_event_category_keys())


def _normalize_city(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    candidate = value.strip().lower().replace(" ", "_")
    if not candidate:
        return None
    if candidate not in _city_keys():
        raise HTTPException(status_code=400, detail=f"Unknown city '{value}'.")
    return candidate


def _normalize_categories(values: Optional[Sequence[str]]) -> List[str]:
    if not values:
        return []
    allowed = _category_keys()
    normalized: List[str] = []
    seen: Set[str] = set()
    for raw in values:
        if raw is None:
            continue
        for fragment in raw.split(","):
            candidate = fragment.strip().lower().replace(" ", "_")
            if not candidate:
                continue
            if candidate not in allowed:
                raise HTTPException(status_code=400, detail=f"Unknown category '{candidate}'.")
            if candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
    return normalized


@router.get("", response_model=EventsListResponse)
@router.get("/", response_model=EventsListResponse, include_in_schema=False)
async def get_events(
    city: Optional[str] = Query(
        default=None,
        description="Filter by city key (e.g., rotterdam).",
    ),
    date_from: Optional[date] = Query(
        default=None,
        description="Inclusive start date (YYYY-MM-DD).",
    ),
    date_to: Optional[date] = Query(
        default=None,
        description="Inclusive end date (YYYY-MM-DD).",
    ),
    categories: Optional[List[str]] = Query(
        default=None,
        description="Optional repeated category keys (community,culture,...).",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> EventsListResponse:
    if date_from and date_to and date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to must be on or after date_from.")

    normalized_city = _normalize_city(city)
    normalized_categories = _normalize_categories(categories)

    items, total = await list_public_events(
        city=normalized_city,
        date_from=date_from,
        date_to=date_to,
        categories=normalized_categories or None,
        limit=limit,
        offset=offset,
    )
    return EventsListResponse(items=items, total=total, limit=limit, offset=offset)

