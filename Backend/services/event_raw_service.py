from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from app.core.logging import get_logger
from app.models.event_raw import EventRaw, EventRawCreate
from services.db_service import execute, fetch, fetchrow

logger = get_logger()


@dataclass
class EventRawRecord:
    id: int
    event_source_id: int
    title: Optional[str]
    description: Optional[str]
    location_text: Optional[str]
    venue: Optional[str]
    event_url: Optional[str]
    image_url: Optional[str]
    start_at: Optional[datetime]
    end_at: Optional[datetime]
    detected_format: str
    ingest_hash: str
    raw_payload: Dict[str, Any]
    processing_state: str
    processing_errors: Optional[Dict[str, Any]]
    fetched_at: datetime
    created_at: datetime
    language_code: Optional[str]
    category_key: Optional[str]
    summary_ai: Optional[str]
    confidence_score: Optional[float]
    enriched_at: Optional[datetime]
    enriched_by: Optional[str]

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "EventRawRecord":
        payload = row.get("raw_payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except ValueError:
                payload = {}
        errors = row.get("processing_errors") or None
        if isinstance(errors, str):
            try:
                errors = json.loads(errors)
            except ValueError:
                errors = None
        return cls(
            id=int(row["id"]),
            event_source_id=int(row["event_source_id"]),
            title=row.get("title"),
            description=row.get("description"),
            location_text=row.get("location_text"),
            venue=row.get("venue"),
            event_url=row.get("event_url"),
            image_url=row.get("image_url"),
            start_at=row.get("start_at"),
            end_at=row.get("end_at"),
            detected_format=str(row.get("detected_format")),
            ingest_hash=str(row.get("ingest_hash")),
            raw_payload=payload if isinstance(payload, dict) else {},
            processing_state=str(row.get("processing_state")),
            processing_errors=errors if isinstance(errors, dict) else None,
            fetched_at=row.get("fetched_at"),
            created_at=row.get("created_at"),
            language_code=row.get("language_code"),
            category_key=row.get("category_key"),
            summary_ai=row.get("summary_ai"),
            confidence_score=row.get("confidence_score"),
            enriched_at=row.get("enriched_at"),
            enriched_by=row.get("enriched_by"),
        )

    def to_model(self) -> EventRaw:
        return EventRaw(
            id=self.id,
            event_source_id=self.event_source_id,
            title=self.title,
            description=self.description,
            location_text=self.location_text,
            venue=self.venue,
            event_url=self.event_url,
            image_url=self.image_url,
            start_at=self.start_at,
            end_at=self.end_at,
            detected_format=self.detected_format,  # type: ignore[arg-type]
            ingest_hash=self.ingest_hash,
            raw_payload=self.raw_payload,
            processing_state=self.processing_state,
            processing_errors=self.processing_errors,
            fetched_at=self.fetched_at,
            created_at=self.created_at,
            language_code=self.language_code,
            category_key=self.category_key,
            summary_ai=self.summary_ai,
            confidence_score=self.confidence_score,
            enriched_at=self.enriched_at,
            enriched_by=self.enriched_by,
        )


async def insert_event_raw(event: EventRawCreate) -> Optional[int]:
    """
    Insert a raw event row. Returns the inserted ID or None when deduped.
    """
    raw_payload_json = json.dumps(event.raw_payload, ensure_ascii=False)
    processing_errors_json = (
        json.dumps(event.processing_errors, ensure_ascii=False)
        if event.processing_errors is not None
        else None
    )
    row = await fetchrow(
        """
        INSERT INTO event_raw (
            event_source_id,
            title,
            description,
            location_text,
            venue,
            event_url,
            image_url,
            start_at,
            end_at,
            detected_format,
            ingest_hash,
            raw_payload,
            processing_state,
            processing_errors
        )
        VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,
            CAST($12::text AS JSONB),$13,CAST($14::text AS JSONB)
        )
        ON CONFLICT (event_source_id, ingest_hash) DO NOTHING
        RETURNING id
        """,
        event.event_source_id,
        event.title,
        event.description,
        event.location_text,
        event.venue,
        event.event_url,
        event.image_url,
        event.start_at,
        event.end_at,
        event.detected_format,
        event.ingest_hash,
        raw_payload_json,
        event.processing_state,
        processing_errors_json,
    )
    if row:
        inserted_id = int(row["id"])
        logger.debug(
            "event_raw_inserted",
            event_source_id=event.event_source_id,
            id=inserted_id,
        )
        return inserted_id
    logger.debug(
        "event_raw_deduplicated",
        event_source_id=event.event_source_id,
        ingest_hash=event.ingest_hash,
    )
    return None


async def insert_many_event_raw(events: Sequence[EventRawCreate]) -> int:
    """
    Insert a batch of events, returning the number of newly inserted rows.
    """
    if not events:
        return 0

    inserted = 0
    for event in events:
        new_id = await insert_event_raw(event)
        if new_id is not None:
            inserted += 1
    return inserted


async def fetch_recent_event_raw(
    *,
    limit: int = 50,
    event_source_id: Optional[int] = None,
) -> Iterable[EventRaw]:
    """
    Fetch recent raw events, optionally scoped to a single source.
    """
    params: list[Any] = [limit]
    where_clause = ""
    if event_source_id:
        where_clause = "WHERE event_source_id = $2"
        params.insert(0, event_source_id)

    rows = await fetch(
        f"""
        SELECT
            id,
            event_source_id,
            title,
            description,
            location_text,
            venue,
            event_url,
            image_url,
            start_at,
            end_at,
            detected_format,
            ingest_hash,
            raw_payload,
            processing_state,
            processing_errors,
            fetched_at,
            created_at
        FROM event_raw
        {where_clause}
        ORDER BY fetched_at DESC
        LIMIT ${len(params)}
        """,
        *params,
    )
    return [EventRawRecord.from_row(dict(row)).to_model() for row in rows or []]


async def fetch_pending_event_raw(
    *,
    limit: int = 50,
) -> List[EventRaw]:
    """
    Fetch rows waiting for AI enrichment.
    """
    rows = await fetch(
        """
        SELECT
            id,
            event_source_id,
            title,
            description,
            location_text,
            venue,
            event_url,
            image_url,
            start_at,
            end_at,
            detected_format,
            ingest_hash,
            raw_payload,
            processing_state,
            processing_errors,
            fetched_at,
            created_at,
            language_code,
            category_key,
            summary_ai,
            confidence_score,
            enriched_at,
            enriched_by
        FROM event_raw
        WHERE processing_state = 'pending'
        ORDER BY fetched_at ASC
        LIMIT $1
        """,
        max(0, int(limit)),
    )
    return [EventRawRecord.from_row(dict(row)).to_model() for row in rows or []]


async def fetch_pending_event_raw(*, limit: int = 50) -> Iterable[EventRaw]:
    """
    Fetch pending raw events in FIFO order for normalization.
    """
    rows = await fetch(
        """
        SELECT
            id,
            event_source_id,
            title,
            description,
            location_text,
            venue,
            event_url,
            image_url,
            start_at,
            end_at,
            detected_format,
            ingest_hash,
            raw_payload,
            processing_state,
            processing_errors,
            fetched_at,
            created_at
        FROM event_raw
        WHERE processing_state = 'pending'
        ORDER BY fetched_at ASC
        LIMIT $1
        """,
        max(0, int(limit)),
    )
    return [EventRawRecord.from_row(dict(row)).to_model() for row in rows or []]


async def fetch_normalized_event_raw(*, limit: int = 50) -> List[EventRaw]:
    """
    Fetch rows that completed normalization and are waiting for enrichment.
    """
    rows = await fetch(
        """
        SELECT
            id,
            event_source_id,
            title,
            description,
            location_text,
            venue,
            event_url,
            image_url,
            start_at,
            end_at,
            detected_format,
            ingest_hash,
            raw_payload,
            processing_state,
            processing_errors,
            fetched_at,
            created_at,
            language_code,
            category_key,
            summary_ai,
            confidence_score,
            enriched_at,
            enriched_by
        FROM event_raw
        WHERE processing_state = 'normalized'
        ORDER BY fetched_at ASC
        LIMIT $1
        """,
        max(0, int(limit)),
    )
    return [EventRawRecord.from_row(dict(row)).to_model() for row in rows or []]


async def update_event_raw_processing_state(
    event_raw_id: int,
    *,
    state: str,
    errors: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Update processing_state + optional processing_errors payload for a row.
    """
    errors_json = json.dumps(errors, ensure_ascii=False) if errors is not None else None
    await execute(
        """
        UPDATE event_raw
        SET
            processing_state = $2,
            processing_errors = CAST($3::text AS JSONB)
        WHERE id = $1
        """,
        event_raw_id,
        state,
        errors_json,
    )


async def apply_event_enrichment(
    *,
    event_id: int,
    language_code: Optional[str],
    category_key: Optional[str],
    summary_ai: Optional[str],
    confidence_score: Optional[float],
    enriched_by: str = "event_enrichment_bot",
) -> None:
    """
    Persist AI enrichment output and mark the row as enriched.
    """
    await execute(
        """
        UPDATE event_raw
        SET language_code = $2,
            category_key = $3,
            summary_ai = $4,
            confidence_score = $5,
            enriched_at = NOW(),
            enriched_by = $6,
            processing_state = 'enriched',
            processing_errors = NULL
        WHERE id = $1
        """,
        int(event_id),
        language_code,
        category_key,
        summary_ai,
        confidence_score,
        enriched_by,
    )


async def mark_event_enrichment_error(
    *,
    event_id: int,
    error: Dict[str, Any],
    enriched_by: str = "event_enrichment_bot",
) -> None:
    """
    Record enrichment failure metadata and mark the row for review/retry.
    """
    error_json = json.dumps(error or {}, ensure_ascii=False)
    await execute(
        """
        UPDATE event_raw
        SET processing_state = 'error',
            processing_errors = CAST($2 AS JSONB),
            enriched_at = NOW(),
            enriched_by = $3
        WHERE id = $1
        """,
        int(event_id),
        error_json,
        enriched_by,
    )


