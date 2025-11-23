from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, List, Optional, Sequence, Tuple

from app.models.events_public import EventItem
from services.db_service import fetch, fetchrow


def _date_start(dt: date) -> datetime:
    return datetime.combine(dt, time.min, tzinfo=timezone.utc)


def _date_end(dt: date) -> datetime:
    return datetime.combine(dt, time.max, tzinfo=timezone.utc)


def _row_to_event_item(row: Any) -> EventItem:
    return EventItem(
        id=int(row["id"]),
        title=str(row["title"]),
        description=row.get("description"),
        start_time_utc=row["start_time_utc"],
        end_time_utc=row.get("end_time_utc"),
        city_key=row.get("city_key"),
        category_key=row.get("category_key"),
        location_text=row.get("location_text"),
        url=row.get("url"),
        source_key=str(row["source_key"]),
        summary_ai=row.get("summary_ai"),
        updated_at=row["updated_at"],
    )


async def list_public_events(
    *,
    city: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
    categories: Optional[Sequence[str]],
    limit: int,
    offset: int,
) -> Tuple[List[EventItem], int]:
    """
    Fetch paginated public events with optional filters.
    """

    params: List[Any] = []
    filters: List[str] = []

    if city:
        filters.append(f"ep.city_key = ${len(params) + 1}")
        params.append(city)

    if categories:
        filters.append(f"ep.category_key = ANY(${len(params) + 1}::text[])")
        params.append(list(categories))

    if date_from:
        filters.append(f"ep.start_time_utc >= ${len(params) + 1}")
        params.append(_date_start(date_from))

    if date_to:
        filters.append(f"ep.start_time_utc <= ${len(params) + 1}")
        params.append(_date_end(date_to))

    if not date_from and not date_to:
        filters.append(f"ep.start_time_utc >= ${len(params) + 1}")
        params.append(datetime.now(timezone.utc))

    where_clause = " AND ".join(filters) if filters else "TRUE"
    limit_idx = len(params) + 1
    offset_idx = len(params) + 2

    data_sql = f"""
        SELECT
            id,
            title,
            description,
            start_time_utc,
            end_time_utc,
            city_key,
            category_key,
            location_text,
            url,
            source_key,
            summary_ai,
            updated_at
        FROM events_public ep
        WHERE {where_clause}
        ORDER BY start_time_utc ASC, id ASC
        LIMIT ${limit_idx} OFFSET ${offset_idx}
    """

    rows = await fetch(data_sql, *(params + [limit, offset]))
    items = [_row_to_event_item(dict(row)) for row in rows or []]

    count_sql = f"SELECT COUNT(*)::int AS total FROM events_public ep WHERE {where_clause}"
    count_row = await fetchrow(count_sql, *params)
    total = int(count_row["total"]) if count_row else 0
    return items, total

