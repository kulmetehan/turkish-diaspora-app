from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from app.core.logging import get_logger
from app.models.event_raw import EventRaw, EventRawCreate
from services.db_service import execute, fetch, fetchrow

logger = get_logger()


def _sanitize_null_bytes(text: Optional[str]) -> Optional[str]:
    """
    Remove null bytes (\x00 and \u0000) from a string.
    PostgreSQL TEXT type cannot handle null bytes.
    """
    if text is None:
        return None
    if not isinstance(text, str):
        return text
    return text.replace("\x00", "").replace("\u0000", "")


def _sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize all string values in a dictionary/list structure
    by removing null bytes. This ensures data is safe for PostgreSQL JSONB storage.
    """
    if obj is None:
        return None
    if isinstance(obj, str):
        return _sanitize_null_bytes(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(item) for item in obj]
    return obj


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
    # Sanitize all string fields before inserting
    sanitized_title = _sanitize_null_bytes(event.title)
    sanitized_description = _sanitize_null_bytes(event.description)
    sanitized_location_text = _sanitize_null_bytes(event.location_text)
    sanitized_venue = _sanitize_null_bytes(event.venue)
    sanitized_event_url = _sanitize_null_bytes(event.event_url)
    sanitized_image_url = _sanitize_null_bytes(event.image_url)
    sanitized_detected_format = _sanitize_null_bytes(event.detected_format)
    
    # Sanitize JSON payloads
    sanitized_raw_payload = _sanitize_for_json(event.raw_payload) if event.raw_payload else {}
    sanitized_processing_errors = _sanitize_for_json(event.processing_errors) if event.processing_errors else None
    
    raw_payload_json = json.dumps(sanitized_raw_payload, ensure_ascii=False)
    processing_errors_json = (
        json.dumps(sanitized_processing_errors, ensure_ascii=False)
        if sanitized_processing_errors is not None
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
        sanitized_title,
        sanitized_description,
        sanitized_location_text,
        sanitized_venue,
        sanitized_event_url,
        sanitized_image_url,
        event.start_at,
        event.end_at,
        sanitized_detected_format,
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
    # Sanitize errors dict before serializing
    sanitized_errors = _sanitize_for_json(errors) if errors is not None else None
    errors_json = json.dumps(sanitized_errors, ensure_ascii=False) if sanitized_errors is not None else None
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
    extracted_location_text: Optional[str] = None,
    enriched_by: str = "event_enrichment_bot",
) -> None:
    """
    Persist AI enrichment output and mark the row as enriched.
    If location_text is missing but extracted_location_text exists, update both event_raw and events_candidate.
    """
    # Sanitize all string fields
    sanitized_language_code = _sanitize_null_bytes(language_code)
    sanitized_category_key = _sanitize_null_bytes(category_key)
    sanitized_summary_ai = _sanitize_null_bytes(summary_ai)
    sanitized_extracted_location_text = _sanitize_null_bytes(extracted_location_text)
    
    # Check if we need to update location_text
    if sanitized_extracted_location_text and sanitized_extracted_location_text.strip():
        # Check current location_text
        from services.db_service import fetchrow as db_fetchrow
        current = await db_fetchrow(
            "SELECT location_text FROM event_raw WHERE id = $1",
            event_id,
        )
        if not current or not current.get("location_text"):
            # Update location_text in event_raw
            location_value = sanitized_extracted_location_text.strip()
            await execute(
                """
                UPDATE event_raw
                SET location_text = $2
                WHERE id = $1
                """,
                event_id,
                location_value,
            )
            # Also update in events_candidate if it exists
            await execute(
                """
                UPDATE events_candidate
                SET location_text = $2
                WHERE event_raw_id = $1 AND (location_text IS NULL OR location_text = '')
                """,
                event_id,
                location_value,
            )

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
        sanitized_language_code,
        sanitized_category_key,
        sanitized_summary_ai,
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
    # Sanitize error dict before serializing
    sanitized_error = _sanitize_for_json(error) if error else {}
    error_json = json.dumps(sanitized_error, ensure_ascii=False)
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


async def update_event_raw_from_detail_page(
    event_raw_id: int,
    *,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    description: Optional[str] = None,
    location_text: Optional[str] = None,
    venue: Optional[str] = None,
    image_url: Optional[str] = None,
    raw_payload_updates: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Update event_raw record with data extracted from detail page.
    Only updates fields that are provided (not None).
    Updates raw_payload by merging raw_payload_updates if provided.
    """
    # Sanitize all string fields before updating
    sanitized_description = _sanitize_null_bytes(description)
    sanitized_location_text = _sanitize_null_bytes(location_text)
    sanitized_venue = _sanitize_null_bytes(venue)
    sanitized_image_url = _sanitize_null_bytes(image_url)
    
    updates: List[str] = []
    params: List[Any] = [event_raw_id]
    param_num = 2

    if start_at is not None:
        updates.append(f"start_at = ${param_num}")
        params.append(start_at)
        param_num += 1

    if end_at is not None:
        updates.append(f"end_at = ${param_num}")
        params.append(end_at)
        param_num += 1

    if sanitized_description is not None:
        updates.append(f"description = ${param_num}")
        params.append(sanitized_description)
        param_num += 1

    if sanitized_location_text is not None:
        updates.append(f"location_text = ${param_num}")
        params.append(sanitized_location_text)
        param_num += 1

    if sanitized_venue is not None:
        updates.append(f"venue = ${param_num}")
        params.append(sanitized_venue)
        param_num += 1

    if sanitized_image_url is not None:
        updates.append(f"image_url = ${param_num}")
        params.append(sanitized_image_url)
        param_num += 1

    if raw_payload_updates:
        # Sanitize raw_payload_updates before merging
        sanitized_raw_payload_updates = _sanitize_for_json(raw_payload_updates)
        
        # Fetch current raw_payload, merge updates, then update
        current = await fetchrow(
            "SELECT raw_payload FROM event_raw WHERE id = $1",
            event_raw_id,
        )
        if current:
            current_payload = current.get("raw_payload") or {}
            if isinstance(current_payload, str):
                try:
                    current_payload = json.loads(current_payload)
                except ValueError:
                    current_payload = {}
            if not isinstance(current_payload, dict):
                current_payload = {}

            merged_payload = {**current_payload, **sanitized_raw_payload_updates}
            updates.append(f"raw_payload = CAST(${param_num}::text AS JSONB)")
            params.append(json.dumps(merged_payload, ensure_ascii=False))
            param_num += 1

    if not updates:
        return  # Nothing to update

    # Track if location_text was updated
    location_text_updated = sanitized_location_text is not None

    # Reset processing_state to 'pending' so normalization bot will reprocess this event
    updates.append("processing_state = 'pending'")
    
    sql = f"""
        UPDATE event_raw
        SET {', '.join(updates)}
        WHERE id = $1
    """
    await execute(sql, *params)

    # Also update events_candidate.location_text if location_text was updated
    if location_text_updated and sanitized_location_text:
        await execute(
            """
            UPDATE events_candidate
            SET location_text = $2
            WHERE event_raw_id = $1 AND (location_text IS NULL OR location_text = '')
            """,
            event_raw_id,
            sanitized_location_text,
        )

    logger.info(
        "event_raw_updated_from_detail_page",
        event_raw_id=event_raw_id,
        fields_updated=len(updates),
        location_text_updated=location_text_updated,
    )


