from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.logging import get_logger
from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.admin_events import (
    AdminEventCandidateItem,
    AdminEventCandidateListResponse,
    AdminEventRawItem,
    AdminEventRawListResponse,
    AdminEventDuplicateCluster,
)
from app.models.event_candidate import EVENT_CANDIDATE_STATES
from services.db_service import fetch, fetchrow
from services.event_candidate_service import (
    EventCandidateRecord,
    list_event_candidates,
    list_candidate_duplicates,
    update_event_candidate_state,
)

router = APIRouter(
    prefix="/admin/events",
    tags=["admin-events"],
)

logger = get_logger()


@router.get("/raw", response_model=AdminEventRawListResponse)
async def list_event_raw(
    processing_state: str | None = Query(
        default=None,
        description="Filter by processing_state (pending/enriched/error).",
    ),
    source_id: int | None = Query(default=None, ge=1),
    category_key: str | None = Query(default=None, description="Filter by normalized category key."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminEventRawListResponse:
    filters: list[str] = []
    params: list[object] = []
    idx = 1

    if processing_state:
        filters.append(f"er.processing_state = ${idx}")
        params.append(processing_state)
        idx += 1

    if source_id:
        filters.append(f"er.event_source_id = ${idx}")
        params.append(source_id)
        idx += 1

    if category_key:
        filters.append(f"er.category_key = ${idx}")
        params.append(category_key.strip().lower())
        idx += 1

    where_clause = " AND ".join(filters) if filters else "1=1"

    data_sql = f"""
        SELECT
            er.id,
            er.event_source_id,
            es.key AS source_key,
            er.title,
            er.description,
            er.location_text,
            er.venue,
            er.event_url,
            er.start_at,
            er.end_at,
            er.processing_state,
            er.language_code,
            er.category_key,
            er.summary_ai,
            er.confidence_score,
            er.enriched_at,
            er.enriched_by,
            er.processing_errors,
            er.fetched_at
        FROM event_raw er
        LEFT JOIN event_sources es ON es.id = er.event_source_id
        WHERE {where_clause}
        ORDER BY er.fetched_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """

    count_sql = f"SELECT COUNT(*)::int AS total FROM event_raw er WHERE {where_clause}"

    try:
        rows = await fetch(data_sql, *(params + [limit, offset]))
        count_row = await fetchrow(count_sql, *params)
    except (asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        raise HTTPException(status_code=503, detail="event data unavailable") from exc

    items = [
        AdminEventRawItem(
            id=row["id"],
            event_source_id=row["event_source_id"],
            source_key=row.get("source_key"),
            title=row.get("title"),
            description=row.get("description"),
            location_text=row.get("location_text"),
            venue=row.get("venue"),
            event_url=row.get("event_url"),
            start_at=row.get("start_at"),
            end_at=row.get("end_at"),
            processing_state=row.get("processing_state"),
            language_code=row.get("language_code"),
            category_key=row.get("category_key"),
            summary_ai=row.get("summary_ai"),
            confidence_score=row.get("confidence_score"),
            enriched_at=row.get("enriched_at"),
            enriched_by=row.get("enriched_by"),
            processing_errors=row.get("processing_errors"),
            fetched_at=row.get("fetched_at"),
        )
        for row in rows or []
    ]

    total = int(count_row["total"]) if count_row else 0

    return AdminEventRawListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


def _record_to_candidate_item(record: EventCandidateRecord) -> AdminEventCandidateItem:
    return AdminEventCandidateItem(
        id=record.id,
        event_source_id=record.event_source_id,
        source_key=record.source_key,
        source_name=record.source_name,
        title=record.title,
        description=record.description,
        location_text=record.location_text,
        url=record.url,
        start_time_utc=record.start_time_utc,
        end_time_utc=record.end_time_utc,
        duplicate_of_id=record.duplicate_of_id,
        duplicate_score=record.duplicate_score,
        has_duplicates=record.has_duplicates,
        state=record.state,  # type: ignore[arg-type]
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/candidates", response_model=AdminEventCandidateListResponse)
async def list_event_candidates_endpoint(
    state: str | None = Query(default=None, description="Filter by candidate state."),
    source_id: int | None = Query(default=None, ge=1, description="Filter by event_source_id."),
    source_key: str | None = Query(default=None, description="Filter by source key slug."),
    search: str | None = Query(default=None, description="Search title/description."),
    duplicates_only: bool = Query(default=False, description="Return only rows flagged as duplicates."),
    canonical_only: bool = Query(default=False, description="Return only canonical (non-duplicate) rows."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminEventCandidateListResponse:
    _ = admin  # unused but enforces auth
    normalized_state = None
    if state:
        state_clean = state.strip().lower()
        if state_clean not in EVENT_CANDIDATE_STATES:
            raise HTTPException(
                status_code=400,
                detail=f"state must be one of: {', '.join(EVENT_CANDIDATE_STATES)}",
            )
        normalized_state = state_clean

    normalized_source_key = source_key.strip().lower() if source_key else None

    if duplicates_only and canonical_only:
        raise HTTPException(
            status_code=400,
            detail="duplicates_only and canonical_only cannot both be true.",
        )

    records, total = await list_event_candidates(
        state=normalized_state,
        event_source_id=source_id,
        source_key=normalized_source_key,
        search=search.strip() if search else None,
        duplicates_only=duplicates_only,
        canonical_only=canonical_only,
        limit=limit,
        offset=offset,
    )
    items = [_record_to_candidate_item(record) for record in records]
    return AdminEventCandidateListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


async def _apply_candidate_action(
    *,
    candidate_id: int,
    new_state: str,
    admin: AdminUser,
) -> AdminEventCandidateItem:
    try:
        record = await update_event_candidate_state(
            candidate_id=candidate_id,
            new_state=new_state,
            actor_email=admin.email,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="event candidate not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "admin_event_candidate_action",
        candidate_id=candidate_id,
        action=new_state,
        admin=admin.email,
    )
    return _record_to_candidate_item(record)


@router.post(
    "/candidates/{candidate_id}/verify",
    response_model=AdminEventCandidateItem,
)
async def verify_event_candidate(
    candidate_id: int,
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminEventCandidateItem:
    return await _apply_candidate_action(
        candidate_id=candidate_id,
        new_state="verified",
        admin=admin,
    )


@router.post(
    "/candidates/{candidate_id}/publish",
    response_model=AdminEventCandidateItem,
)
async def publish_event_candidate(
    candidate_id: int,
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminEventCandidateItem:
    return await _apply_candidate_action(
        candidate_id=candidate_id,
        new_state="published",
        admin=admin,
    )


@router.post(
    "/candidates/{candidate_id}/reject",
    response_model=AdminEventCandidateItem,
)
async def reject_event_candidate(
    candidate_id: int,
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminEventCandidateItem:
    return await _apply_candidate_action(
        candidate_id=candidate_id,
        new_state="rejected",
        admin=admin,
    )


@router.get(
    "/candidates/{candidate_id}/duplicates",
    response_model=AdminEventDuplicateCluster,
)
async def get_event_candidate_duplicates(
    candidate_id: int,
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminEventDuplicateCluster:
    _ = admin
    try:
        canonical, duplicates = await list_candidate_duplicates(candidate_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="event candidate not found") from None
    return AdminEventDuplicateCluster(
        canonical=_record_to_candidate_item(canonical),
        duplicates=[_record_to_candidate_item(record) for record in duplicates],
    )


