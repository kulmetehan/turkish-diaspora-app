from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from app.core.logging import get_logger
from app.models.event_candidate import (
    EVENT_CANDIDATE_STATES,
    EventCandidate,
    EventCandidateCreate,
)
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

ALLOWED_STATE_TRANSITIONS = {
    "candidate": {"verified", "published", "rejected"},
    "verified": {"published", "rejected"},
    "published": {"rejected"},
    "rejected": set(),
}


@dataclass
class EventCandidateRecord:
    id: int
    event_source_id: int
    event_raw_id: int
    title: str
    description: Optional[str]
    duplicate_of_id: Optional[int]
    duplicate_score: Optional[float]
    start_time_utc: datetime
    end_time_utc: Optional[datetime]
    location_text: Optional[str]
    url: Optional[str]
    source_key: str
    ingest_hash: str
    state: str
    created_at: datetime
    updated_at: datetime
    event_category: Optional[str] = None
    source_name: Optional[str] = None
    has_duplicates: bool = False

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "EventCandidateRecord":
        return cls(
            id=int(row["id"]),
            event_source_id=int(row["event_source_id"]),
            event_raw_id=int(row["event_raw_id"]),
            title=str(row["title"]),
            description=row.get("description"),
            duplicate_of_id=row.get("duplicate_of_id"),
            duplicate_score=row.get("duplicate_score"),
            start_time_utc=row["start_time_utc"],
            end_time_utc=row.get("end_time_utc"),
            location_text=row.get("location_text"),
            url=row.get("url"),
            source_key=str(row["source_key"]),
            ingest_hash=str(row["ingest_hash"]),
            state=str(row["state"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            event_category=row.get("event_category"),
            source_name=row.get("source_name"),
            has_duplicates=bool(row.get("has_duplicates", False)),
        )

    def to_model(self) -> EventCandidate:
        return EventCandidate(
            id=self.id,
            event_source_id=self.event_source_id,
            event_raw_id=self.event_raw_id,
            title=self.title,
            description=self.description,
            duplicate_of_id=self.duplicate_of_id,
            duplicate_score=self.duplicate_score,
            start_time_utc=self.start_time_utc,
            end_time_utc=self.end_time_utc,
            location_text=self.location_text,
            url=self.url,
            source_key=self.source_key,
            ingest_hash=self.ingest_hash,
            state=self.state,
            event_category=self.event_category,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


async def insert_event_candidate(candidate: EventCandidateCreate) -> Optional[int]:
    """
    Insert a normalized event candidate. Returns new ID or None if deduped.
    """
    # Sanitize all string fields before inserting
    sanitized_title = _sanitize_null_bytes(candidate.title)
    sanitized_description = _sanitize_null_bytes(candidate.description)
    sanitized_location_text = _sanitize_null_bytes(candidate.location_text)
    sanitized_url = _sanitize_null_bytes(candidate.url)
    sanitized_source_key = _sanitize_null_bytes(candidate.source_key)
    
    row = await fetchrow(
        """
        INSERT INTO events_candidate (
            event_source_id,
            event_raw_id,
            title,
            description,
            start_time_utc,
            end_time_utc,
            location_text,
            url,
            source_key,
            ingest_hash,
            state
        )
        VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11
        )
        ON CONFLICT (event_source_id, ingest_hash) DO NOTHING
        RETURNING id
        """,
        candidate.event_source_id,
        candidate.event_raw_id,
        sanitized_title,
        sanitized_description,
        candidate.start_time_utc,
        candidate.end_time_utc,
        sanitized_location_text,
        sanitized_url,
        sanitized_source_key,
        candidate.ingest_hash,
        candidate.state,
    )

    if row:
        new_id = int(row["id"])
        logger.debug(
            "event_candidate_inserted",
            candidate_id=new_id,
            event_source_id=candidate.event_source_id,
            event_raw_id=candidate.event_raw_id,
        )
        return new_id

    logger.debug(
        "event_candidate_deduplicated",
        event_source_id=candidate.event_source_id,
        ingest_hash=candidate.ingest_hash,
    )
    return None


async def insert_many_event_candidates(
    candidates: Sequence[EventCandidateCreate],
) -> int:
    """
    Insert multiple normalized candidates sequentially. Returns count of inserts.
    """
    inserted = 0
    for candidate in candidates:
        new_id = await insert_event_candidate(candidate)
        if new_id is not None:
            inserted += 1
    return inserted


async def fetch_event_candidate_by_id(candidate_id: int) -> Optional[EventCandidate]:
    row = await fetchrow(
        """
        SELECT
            id,
            event_source_id,
            event_raw_id,
            title,
            description,
            duplicate_of_id,
            duplicate_score,
            start_time_utc,
            end_time_utc,
            location_text,
            url,
            source_key,
            ingest_hash,
            state,
            created_at,
            updated_at,
            EXISTS (
                SELECT 1 FROM events_candidate dup WHERE dup.duplicate_of_id = events_candidate.id
            ) AS has_duplicates
        FROM events_candidate
        WHERE id = $1
        """,
        candidate_id,
    )
    if not row:
        return None
    return EventCandidateRecord.from_row(dict(row)).to_model()


async def fetch_recent_event_candidates(limit: int = 50) -> Iterable[EventCandidate]:
    rows = await fetch(
        """
        SELECT
            id,
            event_source_id,
            event_raw_id,
            title,
            description,
            duplicate_of_id,
            duplicate_score,
            start_time_utc,
            end_time_utc,
            location_text,
            url,
            source_key,
            ingest_hash,
            state,
            event_category,
            created_at,
            updated_at,
            EXISTS (
                SELECT 1 FROM events_candidate dup WHERE dup.duplicate_of_id = events_candidate.id
            ) AS has_duplicates
        FROM events_candidate
        ORDER BY created_at DESC
        LIMIT $1
        """,
        max(0, int(limit)),
    )
    return [EventCandidateRecord.from_row(dict(row)).to_model() for row in rows or []]


async def list_event_candidates(
    *,
    state: Optional[str] = None,
    event_source_id: Optional[int] = None,
    source_key: Optional[str] = None,
    search: Optional[str] = None,
    duplicates_only: bool = False,
    canonical_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[list[EventCandidateRecord], int]:
    filters: list[str] = []
    params: list[Any] = []
    idx = 1

    if state:
        filters.append(f"ec.state = ${idx}")
        params.append(state)
        idx += 1

    if event_source_id:
        filters.append(f"ec.event_source_id = ${idx}")
        params.append(event_source_id)
        idx += 1

    if source_key:
        filters.append(f"ec.source_key = ${idx}")
        params.append(source_key.strip().lower())
        idx += 1

    if search:
        filters.append(f"(ec.title ILIKE ${idx} OR ec.description ILIKE ${idx})")
        params.append(f"%{search}%")
        idx += 1

    if duplicates_only and canonical_only:
        raise ValueError("duplicates_only and canonical_only cannot both be true")

    if duplicates_only:
        filters.append("ec.duplicate_of_id IS NOT NULL")
    elif canonical_only:
        filters.append("ec.duplicate_of_id IS NULL")

    where_clause = " AND ".join(filters) if filters else "1=1"

    data_sql = f"""
        SELECT
            ec.id,
            ec.event_source_id,
            ec.event_raw_id,
            ec.title,
            ec.description,
            ec.duplicate_of_id,
            ec.duplicate_score,
            ec.start_time_utc,
            ec.end_time_utc,
            ec.location_text,
            ec.url,
            ec.source_key,
            ec.ingest_hash,
            ec.state,
            ec.event_category,
            ec.created_at,
            ec.updated_at,
            es.name AS source_name,
            EXISTS (
                SELECT 1 FROM events_candidate dup WHERE dup.duplicate_of_id = ec.id
            ) AS has_duplicates
        FROM events_candidate ec
        LEFT JOIN event_sources es ON es.id = ec.event_source_id
        WHERE {where_clause}
        ORDER BY ec.updated_at DESC, ec.created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """

    count_sql = f"SELECT COUNT(*)::int AS total FROM events_candidate ec WHERE {where_clause}"

    rows = await fetch(data_sql, *(params + [limit, offset]))
    count_row = await fetchrow(count_sql, *params)
    records = [EventCandidateRecord.from_row(dict(row)) for row in rows or []]
    total = int(count_row["total"]) if count_row else 0
    return records, total


async def list_candidate_duplicates(
    candidate_id: int,
) -> Tuple[EventCandidateRecord, List[EventCandidateRecord]]:
    row = await fetchrow(
        """
        SELECT
            ec.id,
            ec.event_source_id,
            ec.event_raw_id,
            ec.title,
            ec.description,
            ec.duplicate_of_id,
            ec.duplicate_score,
            ec.start_time_utc,
            ec.end_time_utc,
            ec.location_text,
            ec.url,
            ec.source_key,
            ec.ingest_hash,
            ec.state,
            ec.event_category,
            ec.created_at,
            ec.updated_at,
            es.name AS source_name,
            EXISTS (
                SELECT 1 FROM events_candidate dup WHERE dup.duplicate_of_id = ec.id
            ) AS has_duplicates
        FROM events_candidate ec
        LEFT JOIN event_sources es ON es.id = ec.event_source_id
        WHERE ec.id = $1
        """,
        candidate_id,
    )
    if row is None:
        raise LookupError("event_candidate_not_found")

    current = EventCandidateRecord.from_row(dict(row))
    canonical_id = current.duplicate_of_id or current.id

    canonical_record = current
    if current.duplicate_of_id:
        canonical_row = await fetchrow(
            """
            SELECT
                ec.id,
                ec.event_source_id,
                ec.event_raw_id,
                ec.title,
                ec.description,
                ec.duplicate_of_id,
                ec.duplicate_score,
                ec.start_time_utc,
                ec.end_time_utc,
                ec.location_text,
                ec.url,
                ec.source_key,
                ec.ingest_hash,
                ec.state,
                ec.event_category,
                ec.created_at,
                ec.updated_at,
                es.name AS source_name,
                EXISTS (
                    SELECT 1 FROM events_candidate dup WHERE dup.duplicate_of_id = ec.id
                ) AS has_duplicates
            FROM events_candidate ec
            LEFT JOIN event_sources es ON es.id = ec.event_source_id
            WHERE ec.id = $1
            """,
            canonical_id,
        )
        if canonical_row is None:
            raise LookupError("canonical_event_not_found")
        canonical_record = EventCandidateRecord.from_row(dict(canonical_row))

    duplicate_rows = await fetch(
        """
        SELECT
            ec.id,
            ec.event_source_id,
            ec.event_raw_id,
            ec.title,
            ec.description,
            ec.duplicate_of_id,
            ec.duplicate_score,
            ec.start_time_utc,
            ec.end_time_utc,
            ec.location_text,
            ec.url,
            ec.source_key,
            ec.ingest_hash,
            ec.state,
            ec.event_category,
            ec.created_at,
            ec.updated_at,
            es.name AS source_name,
            EXISTS (
                SELECT 1 FROM events_candidate dup WHERE dup.duplicate_of_id = ec.id
            ) AS has_duplicates
        FROM events_candidate ec
        LEFT JOIN event_sources es ON es.id = ec.event_source_id
        WHERE ec.duplicate_of_id = $1
        ORDER BY ec.updated_at DESC, ec.id DESC
        """,
        canonical_record.id,
    )
    duplicates = [EventCandidateRecord.from_row(dict(r)) for r in duplicate_rows or []]
    return canonical_record, duplicates


async def update_event_candidate_state(
    *,
    candidate_id: int,
    new_state: str,
    actor_email: Optional[str] = None,
    event_category: Optional[str] = None,
) -> EventCandidateRecord:
    if new_state not in EVENT_CANDIDATE_STATES:
        raise ValueError(f"Invalid target state: {new_state}")

    row = await fetchrow(
        """
        SELECT
            ec.id,
            ec.event_source_id,
            ec.event_raw_id,
            ec.title,
            ec.description,
            ec.duplicate_of_id,
            ec.duplicate_score,
            ec.start_time_utc,
            ec.end_time_utc,
            ec.location_text,
            ec.url,
            ec.source_key,
            ec.ingest_hash,
            ec.state,
            ec.event_category,
            ec.created_at,
            ec.updated_at,
            es.name AS source_name,
            EXISTS (
                SELECT 1 FROM events_candidate dup WHERE dup.duplicate_of_id = ec.id
            ) AS has_duplicates
        FROM events_candidate ec
        LEFT JOIN event_sources es ON es.id = ec.event_source_id
        WHERE ec.id = $1
        """,
        candidate_id,
    )
    if row is None:
        raise LookupError("event_candidate_not_found")

    current = EventCandidateRecord.from_row(dict(row))
    if current.state == new_state:
        return current

    allowed = ALLOWED_STATE_TRANSITIONS.get(current.state, set())
    if new_state not in allowed:
        raise ValueError(
            f"Invalid transition: {current.state} -> {new_state}",
        )

    if event_category is not None:
        await execute(
            """
            UPDATE events_candidate
            SET state = $2,
                event_category = $3,
                updated_at = $4
            WHERE id = $1
            """,
            candidate_id,
            new_state,
            event_category,
            datetime.now(timezone.utc),
        )
        current.event_category = event_category
    else:
        await execute(
            """
            UPDATE events_candidate
            SET state = $2,
                updated_at = $3
            WHERE id = $1
            """,
            candidate_id,
            new_state,
            datetime.now(timezone.utc),
        )

    logger.info(
        "event_candidate_state_updated",
        candidate_id=candidate_id,
        old_state=current.state,
        new_state=new_state,
        admin=actor_email,
    )

    current.state = new_state
    current.updated_at = datetime.now(timezone.utc)
    return current


