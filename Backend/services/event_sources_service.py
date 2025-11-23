"""
Event Sources Service - CRUD helpers for admin-managed event scraping sources.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.models.event_sources import (
    EVENT_SOURCE_STATUSES,
    EventSource,
    EventSourceCreate,
    EventSourceUpdate,
    sanitize_event_selectors,
)
from services.db_service import execute, fetch, fetchrow, init_db_pool

logger = get_logger()


@dataclass
class EventSourceRecord:
    id: int
    key: str
    name: str
    base_url: str
    list_url: Optional[str]
    city_key: Optional[str]
    selectors: Dict[str, Any]
    interval_minutes: int
    status: str
    last_run_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_error_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "EventSourceRecord":
        selectors = row.get("selectors") or {}
        if isinstance(selectors, str):
            try:
                selectors = json.loads(selectors)
            except Exception:
                selectors = {}
        if not isinstance(selectors, dict):
            selectors = {}
        selectors = sanitize_event_selectors(selectors)
        return cls(
            id=int(row["id"]),
            key=str(row["key"]),
            name=str(row["name"]),
            base_url=str(row["base_url"]),
            list_url=row.get("list_url"),
            city_key=row.get("city_key"),
            selectors=selectors,
            interval_minutes=int(row["interval_minutes"]),
            status=str(row["status"]),
            last_run_at=row.get("last_run_at"),
            last_success_at=row.get("last_success_at"),
            last_error_at=row.get("last_error_at"),
            last_error=row.get("last_error"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def to_model(self) -> EventSource:
        return EventSource(
            id=self.id,
            key=self.key,
            name=self.name,
            base_url=self.base_url,
            list_url=self.list_url,
            city_key=self.city_key,
            selectors=self.selectors,
            interval_minutes=self.interval_minutes,
            status=self.status,
            last_run_at=self.last_run_at,
            last_success_at=self.last_success_at,
            last_error_at=self.last_error_at,
            last_error=self.last_error,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def to_worker_payload(self) -> Dict[str, Any]:
        """
        Minimal dict consumed by scraper workers.
        """
        return {
            "id": self.id,
            "key": self.key,
            "base_url": self.base_url,
            "list_url": self.list_url,
            "city_key": self.city_key,
            "selectors": self.selectors,
            "interval_minutes": self.interval_minutes,
            "status": self.status,
        }


def _dump_selectors(selectors: Optional[Dict[str, Any]]) -> str:
    payload = selectors or {}
    try:
        return json.dumps(payload, ensure_ascii=False)
    except TypeError:
        logger.warning("event_source_invalid_selectors_serialization", selectors=str(selectors))
        return "{}"


async def list_event_sources(status: Optional[str] = None) -> List[EventSource]:
    """
    Return all event sources, optionally filtered by status.
    """
    await init_db_pool()
    params: List[Any] = []
    status_filter = ""
    if status:
        lowered = status.strip().lower()
        if lowered not in EVENT_SOURCE_STATUSES:
            raise ValueError(f"Invalid status filter: {status}")
        status_filter = "WHERE status = $1"
        params.append(lowered)

    sql = f"""
        SELECT id, key, name, base_url, list_url, selectors, interval_minutes,
               city_key, status, last_run_at, last_success_at, last_error_at, last_error,
               created_at, updated_at
        FROM event_sources
        {status_filter}
        ORDER BY name ASC
    """
    rows = await fetch(sql, *params)
    return [EventSourceRecord.from_row(dict(row)).to_model() for row in rows or []]


async def list_active_event_sources() -> List[Dict[str, Any]]:
    """
    Helper for workers: returns sanitized dicts for sources that are currently active.
    """
    sources = await list_event_sources(status="active")
    return [
        {
            "id": source.id,
            "key": source.key,
            "base_url": source.base_url,
            "list_url": source.list_url,
            "selectors": source.selectors,
            "interval_minutes": source.interval_minutes,
            "status": source.status,
        }
        for source in sources
    ]


async def get_event_source(source_id: int) -> Optional[EventSource]:
    """
    Fetch a single event source by ID.
    """
    await init_db_pool()
    row = await fetchrow(
        """
        SELECT id, key, name, base_url, list_url, selectors, interval_minutes,
               city_key, status, last_run_at, last_success_at, last_error_at, last_error,
               created_at, updated_at
        FROM event_sources
        WHERE id = $1
        """,
        source_id,
    )
    if not row:
        return None
    return EventSourceRecord.from_row(dict(row)).to_model()


async def create_event_source(payload: EventSourceCreate) -> EventSource:
    """
    Create a new event source entry.
    """
    await init_db_pool()
    selectors_json = _dump_selectors(payload.selectors)
    status_value = payload.status or "active"

    row = await fetchrow(
        """
        INSERT INTO event_sources
            (key, name, base_url, list_url, city_key, selectors, interval_minutes, status)
        VALUES
            ($1, $2, $3, $4, $5, CAST($6::text AS JSONB), $7, $8)
        RETURNING id, key, name, base_url, list_url, selectors, interval_minutes,
                  city_key, status, last_run_at, last_success_at, last_error_at, last_error,
                  created_at, updated_at
        """,
        payload.key,
        payload.name,
        payload.base_url,
        payload.list_url,
        payload.city_key,
        selectors_json,
        payload.interval_minutes,
        status_value,
    )
    if not row:
        raise RuntimeError("Failed to insert event source")
    logger.info("event_source_created", key=payload.key, name=payload.name)
    return EventSourceRecord.from_row(dict(row)).to_model()


async def update_event_source(source_id: int, payload: EventSourceUpdate) -> Optional[EventSource]:
    """
    Update mutable fields for the event source.
    """
    await init_db_pool()
    data = payload.dict(exclude_unset=True)
    if not data:
        return await get_event_source(source_id)

    setters = []
    values: List[Any] = []
    idx = 1

    def push(fragment: str, value: Any) -> None:
        nonlocal idx
        setters.append(fragment.format(idx=idx))
        values.append(value)
        idx += 1

    if "key" in data:
        push("key = ${idx}", data["key"])
    if "name" in data:
        push("name = ${idx}", data["name"])
    if "base_url" in data:
        push("base_url = ${idx}", data["base_url"])
    if "list_url" in data:
        push("list_url = ${idx}", data["list_url"])
    if "city_key" in data:
        push("city_key = ${idx}", data["city_key"])
    if "selectors" in data:
        selectors_json = _dump_selectors(data["selectors"])
        push("selectors = CAST(${idx}::text AS JSONB)", selectors_json)
    if "interval_minutes" in data:
        push("interval_minutes = ${idx}", data["interval_minutes"])
    if "status" in data:
        push("status = ${idx}", data["status"])

    setters.append("updated_at = NOW()")

    sql = f"""
        UPDATE event_sources
        SET {', '.join(setters)}
        WHERE id = ${idx}
        RETURNING id, key, name, base_url, list_url, selectors, interval_minutes,
                  city_key, status, last_run_at, last_success_at, last_error_at, last_error,
                  created_at, updated_at
    """
    values.append(source_id)

    row = await fetchrow(sql, *values)
    if not row:
        return None
    logger.info("event_source_updated", id=source_id, fields=list(data.keys()))
    return EventSourceRecord.from_row(dict(row)).to_model()


async def set_event_source_status(source_id: int, status: str) -> Optional[EventSource]:
    """
    Toggle status between active/disabled.
    """
    lowered = status.strip().lower()
    if lowered not in EVENT_SOURCE_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(EVENT_SOURCE_STATUSES)}")

    return await update_event_source(
        source_id,
        EventSourceUpdate(status=lowered),
    )


async def mark_event_source_run(
    source_id: int,
    *,
    success: bool,
    error_message: Optional[str] = None,
) -> None:
    """
    Update bookkeeping columns after a scraper run.
    """
    await init_db_pool()
    if success:
        await execute(
            """
            UPDATE event_sources
            SET
                last_run_at = NOW(),
                last_success_at = NOW(),
                last_error = NULL,
                updated_at = NOW()
            WHERE id = $1
            """,
            source_id,
        )
    else:
        await execute(
            """
            UPDATE event_sources
            SET
                last_run_at = NOW(),
                last_error_at = NOW(),
                last_error = $2,
                updated_at = NOW()
            WHERE id = $1
            """,
            source_id,
            (error_message or "")[:500] or None,
        )

