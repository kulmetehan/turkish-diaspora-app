from __future__ import annotations

from typing import Any, Dict, List, Optional

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Path, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.admin_events import (
    AdminEventCandidateItem,
    AdminEventCandidateListResponse,
    AdminEventCategoryUpdateRequest,
    AdminEventRawItem,
    AdminEventRawListResponse,
    AdminEventDuplicateCluster,
    EventStateMetrics,
    EventSourceDiagnostics,
)
from app.models.event_candidate import EVENT_CANDIDATE_STATES
from services.db_service import fetch, fetchrow, execute
from services.event_candidate_service import (
    EventCandidateRecord,
    fetch_event_candidate_by_id,
    list_event_candidates,
    list_candidate_duplicates,
    update_event_candidate_state,
    update_event_category,
)
from services.event_enrichment_service import EventEnrichmentService
from services.event_raw_service import (
    apply_event_enrichment,
    fetch_event_raw_by_id,
    update_event_raw_processing_state,
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
        event_category=record.event_category,
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


async def enrich_event_raw_background(event_raw_id: int) -> None:
    """
    Background task to enrich an event_raw record.
    This runs asynchronously after the API response is sent.
    """
    try:
        event_raw = await fetch_event_raw_by_id(event_raw_id)
        if not event_raw:
            logger.warning(
                "admin_enrichment_event_not_found",
                event_raw_id=event_raw_id,
            )
            return
        
        # Skip if already enriched
        if event_raw.processing_state == "enriched":
            logger.info(
                "admin_enrichment_already_enriched",
                event_raw_id=event_raw_id,
            )
            return
        
        # Enrich the event
        service = EventEnrichmentService()
        result, meta = service.enrich_event(event_raw)
        
        # Apply enrichment
        await apply_event_enrichment(
            event_id=event_raw_id,
            language_code=result.language_code,
            category_key=result.category_key,
            summary_ai=result.summary,
            confidence_score=result.confidence_score,
            extracted_location_text=result.extracted_location_text,
            enriched_by="admin_publish",
        )
        
        logger.info(
            "admin_enrichment_success",
            event_raw_id=event_raw_id,
            category=result.category_key,
            language=result.language_code,
            confidence=result.confidence_score,
        )
    except Exception as exc:
        logger.error(
            "admin_enrichment_failed",
            event_raw_id=event_raw_id,
            error=str(exc),
        )
        # Mark as error but don't fail the publish action
        await update_event_raw_processing_state(
            event_raw_id=event_raw_id,
            state="error_enrich",
            errors={"error": str(exc), "source": "admin_publish"},
        )


async def _apply_candidate_action(
    *,
    candidate_id: int,
    new_state: str,
    admin: AdminUser,
    background_tasks: Optional[BackgroundTasks] = None,
) -> AdminEventCandidateItem:
    try:
        # Fetch the event to get event_raw_id
        record = await fetch_event_candidate_by_id(candidate_id)
        if record is None:
            raise LookupError("event candidate not found")
        
        # If publishing, trigger enrichment in background
        if new_state == "published" and background_tasks is not None:
            # Check current processing_state
            raw_row = await fetchrow(
                """
                SELECT processing_state
                FROM event_raw
                WHERE id = $1
                """,
                record.event_raw_id,
            )
            
            # If not enriched, start enrichment in background
            if raw_row and raw_row.get("processing_state") != "enriched":
                background_tasks.add_task(
                    enrich_event_raw_background,
                    event_raw_id=record.event_raw_id,
                )
                logger.info(
                    "admin_event_enrichment_queued",
                    candidate_id=candidate_id,
                    event_raw_id=record.event_raw_id,
                    admin=admin.email,
                )
        
        # Update the candidate state (this happens immediately)
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
        background_tasks=None,
    )


@router.post(
    "/candidates/{candidate_id}/publish",
    response_model=AdminEventCandidateItem,
)
async def publish_event_candidate(
    candidate_id: int,
    background_tasks: BackgroundTasks,
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminEventCandidateItem:
    return await _apply_candidate_action(
        candidate_id=candidate_id,
        new_state="published",
        admin=admin,
        background_tasks=background_tasks,
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
        background_tasks=None,
    )


@router.post(
    "/candidates/bulk-publish",
    response_model=Dict[str, Any],
)
async def bulk_publish_event_candidates(
    background_tasks: BackgroundTasks,
    candidate_ids: List[int] = Body(..., embed=True),
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, Any]:
    """
    Publish multiple events at once. Each event will be enriched in the background.
    """
    published = []
    errors = []
    
    for candidate_id in candidate_ids:
        try:
            record = await _apply_candidate_action(
                candidate_id=candidate_id,
                new_state="published",
                admin=admin,
                background_tasks=background_tasks,
            )
            published.append(record.id)
        except HTTPException as exc:
            errors.append({"id": candidate_id, "error": exc.detail})
        except Exception as exc:
            errors.append({"id": candidate_id, "error": str(exc)})
    
    return {
        "published": published,
        "errors": errors,
        "total": len(candidate_ids),
        "success_count": len(published),
        "error_count": len(errors),
    }


@router.patch(
    "/candidates/{candidate_id}/category",
    response_model=AdminEventCandidateItem,
)
async def update_event_category_endpoint(
    candidate_id: int = Path(..., description="Event candidate ID"),
    request: AdminEventCategoryUpdateRequest = Body(...),
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminEventCandidateItem:
    """
    Update event category for a candidate event.
    Updates both events_candidate.event_category and event_raw.category_key.
    """
    try:
        record = await update_event_category(
            candidate_id=candidate_id,
            category_key=request.category,
            actor_email=admin.email,
        )
        
        logger.info(
            "admin_event_category_updated",
            candidate_id=candidate_id,
            category=request.category,
            admin=admin.email,
        )
        
        return _record_to_candidate_item(record)
    except LookupError:
        raise HTTPException(status_code=404, detail="event candidate not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "admin_event_category_update_failed",
            candidate_id=candidate_id,
            error=str(exc),
            admin=admin.email,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update event category: {str(exc)}",
        ) from exc


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


class EventFlushResponse(BaseModel):
    truncated_candidates: int
    truncated_raw: int
    sources_reset: int
    message: str


@router.post("/flush", response_model=EventFlushResponse)
async def flush_all_events(
    reset_sources: bool = Query(
        default=True,
        description="Reset event source timestamps so scraper can run immediately",
    ),
    admin: AdminUser = Depends(verify_admin_user),
) -> EventFlushResponse:
    """
    Flush all events from the database to allow re-scraping with updated flow.
    
    This endpoint:
    1. TRUNCATE events_candidate (leegt de genormaliseerde events)
    2. TRUNCATE event_raw (leegt de raw events)
    3. Optionally resets event_sources timestamps (last_run_at, last_success_at)
    
    Note: events_public is een VIEW, die wordt automatisch leeg als de onderliggende
    tabellen leeg zijn. We hoeven die niet expliciet te legen.
    
    Use this when you want to re-scrape all events with an updated scraper flow.
    """
    try:
        # Get counts before truncation
        candidates_count_row = await fetchrow(
            "SELECT COUNT(*)::int AS count FROM events_candidate"
        )
        raw_count_row = await fetchrow(
            "SELECT COUNT(*)::int AS count FROM event_raw"
        )
        
        candidates_count = int(candidates_count_row["count"]) if candidates_count_row else 0
        raw_count = int(raw_count_row["count"]) if raw_count_row else 0
        
        # TRUNCATE is sneller en netter dan DELETE
        # Volgorde: eerst events_candidate (afhankelijk), dan event_raw (parent)
        await execute("TRUNCATE TABLE events_candidate RESTART IDENTITY CASCADE")
        await execute("TRUNCATE TABLE event_raw RESTART IDENTITY CASCADE")
        
        # Optionally reset event source timestamps
        sources_reset = 0
        if reset_sources:
            await execute(
                """
                UPDATE event_sources
                SET last_run_at = NULL,
                    last_success_at = NULL,
                    last_error_at = NULL,
                    last_error = NULL
                WHERE status = 'active'
                """
            )
            # Get count of active sources
            sources_count_row = await fetchrow(
                "SELECT COUNT(*)::int AS count FROM event_sources WHERE status = 'active'"
            )
            sources_reset = int(sources_count_row["count"]) if sources_count_row else 0
        
        logger.info(
            "admin_events_flush_completed",
            truncated_candidates=candidates_count,
            truncated_raw=raw_count,
            sources_reset=sources_reset,
            admin=admin.email,
        )
        
        message = (
            f"Flushed {candidates_count} candidates and {raw_count} raw events. "
            f"{sources_reset} event sources reset." if reset_sources
            else f"Flushed {candidates_count} candidates and {raw_count} raw events."
        )
        
        return EventFlushResponse(
            truncated_candidates=candidates_count,
            truncated_raw=raw_count,
            sources_reset=sources_reset,
            message=message,
        )
    except (asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        logger.error(
            "admin_events_flush_failed",
            error=str(exc),
            admin=admin.email,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to flush events: {str(exc)}",
        ) from exc


@router.get("/metrics", response_model=EventStateMetrics)
async def get_event_state_metrics(
    admin: AdminUser = Depends(verify_admin_user),
) -> EventStateMetrics:
    """
    Return counts per state and visibility metrics for events.
    
    Provides:
    - Total candidates count
    - Counts per state (candidate, verified, published, rejected)
    - Count of events visible in frontend (events_public)
    - Count of published events not visible (filtered by country/location)
    - Count of duplicate events
    """
    try:
        # Total candidates count
        total_row = await fetchrow(
            "SELECT COUNT(*)::int AS count FROM events_candidate"
        )
        total_candidates = int(total_row["count"]) if total_row else 0

        # Counts per state
        state_rows = await fetch(
            """
            SELECT state, COUNT(*)::int AS count
            FROM events_candidate
            GROUP BY state
            """
        )
        by_state: dict[str, int] = {}
        for row in state_rows or []:
            state_name = str(row["state"])
            by_state[state_name] = int(row["count"])
        
        # Ensure all states are present (even if 0)
        for state in EVENT_CANDIDATE_STATES:
            if state not in by_state:
                by_state[state] = 0

        # Visible in frontend (events_public count)
        # Match frontend API filter: only future events (start_time_utc >= NOW())
        # This matches the default filter in list_public_events service
        visible_row = await fetchrow(
            """
            SELECT COUNT(*)::int AS count 
            FROM events_public 
            WHERE start_time_utc >= NOW()
            """
        )
        visible_in_frontend = int(visible_row["count"]) if visible_row else 0

        # Published events not visible (published but filtered out by country/location)
        published_not_visible_row = await fetchrow(
            """
            SELECT COUNT(*)::int AS count
            FROM events_candidate ec
            JOIN event_raw er ON er.id = ec.event_raw_id
            WHERE ec.state = 'published'
              AND er.processing_state = 'enriched'
              AND ec.duplicate_of_id IS NULL
              AND ec.id NOT IN (SELECT id FROM events_public)
            """
        )
        published_not_visible = int(published_not_visible_row["count"]) if published_not_visible_row else 0

        # Duplicate metrics
        # Count events marked as duplicates (have duplicate_of_id)
        duplicate_row = await fetchrow(
            "SELECT COUNT(*)::int AS count FROM events_candidate WHERE duplicate_of_id IS NOT NULL"
        )
        duplicate_count = int(duplicate_row["count"]) if duplicate_row else 0
        
        # Count canonical events that have duplicates pointing to them
        canonical_with_duplicates_row = await fetchrow(
            """
            SELECT COUNT(DISTINCT ec.id)::int AS count
            FROM events_candidate ec
            WHERE ec.duplicate_of_id IS NULL
              AND EXISTS (
                  SELECT 1 FROM events_candidate dup 
                  WHERE dup.duplicate_of_id = ec.id
              )
            """
        )
        canonical_with_duplicates = int(canonical_with_duplicates_row["count"]) if canonical_with_duplicates_row else 0

        return EventStateMetrics(
            total_candidates=total_candidates,
            by_state=by_state,
            visible_in_frontend=visible_in_frontend,
            published_not_visible=published_not_visible,
            duplicate_count=duplicate_count,
            canonical_with_duplicates=canonical_with_duplicates,
        )
    except (asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        logger.error(
            "admin_events_metrics_failed",
            error=str(exc),
            admin=admin.email,
        )
        raise HTTPException(
            status_code=503,
            detail="event metrics unavailable",
        ) from exc


@router.get("/sources/{source_id}/diagnostics", response_model=EventSourceDiagnostics)
async def get_event_source_diagnostics(
    source_id: int = Path(..., ge=1, description="Event source ID"),
    admin: AdminUser = Depends(verify_admin_user),
) -> EventSourceDiagnostics:
    """
    Diagnostic information for a specific event source.
    Shows where events are in the pipeline and why they might not be appearing.
    """
    try:
        # Get source info
        source_row = await fetchrow(
            """
            SELECT id, key, name, status, last_run_at, last_success_at, last_error
            FROM event_sources
            WHERE id = $1
            """,
            source_id,
        )
        if not source_row:
            raise HTTPException(status_code=404, detail="event source not found")
        
        source_key = str(source_row["key"])
        
        # Pages raw counts
        pages_counts = await fetchrow(
            """
            SELECT 
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE processing_state = 'pending')::int AS pending,
                COUNT(*) FILTER (WHERE processing_state = 'extracted')::int AS extracted,
                COUNT(*) FILTER (WHERE processing_state IN ('error_fetch', 'error_extract'))::int AS error
            FROM event_pages_raw
            WHERE event_source_id = $1
            """,
            source_id,
        )
        
        # Events raw counts
        events_raw_counts = await fetchrow(
            """
            SELECT 
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE processing_state = 'pending')::int AS pending,
                COUNT(*) FILTER (WHERE processing_state = 'enriched')::int AS enriched,
                COUNT(*) FILTER (WHERE processing_state IN ('error_norm', 'error_enrich'))::int AS error
            FROM event_raw
            WHERE event_source_id = $1
            """,
            source_id,
        )
        
        # Events candidate counts by state
        candidate_state_counts = await fetch(
            """
            SELECT state, COUNT(*)::int AS count
            FROM events_candidate
            WHERE event_source_id = $1
            GROUP BY state
            """,
            source_id,
        )
        candidate_by_state: Dict[str, int] = {}
        total_candidates = 0
        for row in candidate_state_counts or []:
            state = str(row["state"])
            count = int(row["count"])
            candidate_by_state[state] = count
            total_candidates += count
        
        # Published count
        published_row = await fetchrow(
            """
            SELECT COUNT(*)::int AS count
            FROM events_candidate
            WHERE event_source_id = $1
              AND state = 'published'
              AND duplicate_of_id IS NULL
            """,
            source_id,
        )
        published_count = int(published_row["count"]) if published_row else 0
        
        # Visible in frontend (published + future + passing filters)
        visible_row = await fetchrow(
            """
            SELECT COUNT(*)::int AS count
            FROM events_public
            WHERE event_source_id = $1
              AND start_time_utc >= NOW()
            """,
            source_id,
        )
        visible_count = int(visible_row["count"]) if visible_row else 0
        
        # Convert datetime to ISO string, handling None values
        last_run_at = source_row["last_run_at"]
        last_success_at = source_row["last_success_at"]
        
        return EventSourceDiagnostics(
            source_id=source_id,
            source_key=source_key,
            source_name=str(source_row["name"]),
            status=str(source_row["status"]),
            last_run_at=last_run_at.isoformat() if last_run_at else None,
            last_success_at=last_success_at.isoformat() if last_success_at else None,
            last_error=source_row["last_error"],
            pages_raw_count=int(pages_counts["total"]) if pages_counts else 0,
            pages_pending=int(pages_counts["pending"]) if pages_counts else 0,
            pages_extracted=int(pages_counts["extracted"]) if pages_counts else 0,
            pages_error=int(pages_counts["error"]) if pages_counts else 0,
            events_raw_count=int(events_raw_counts["total"]) if events_raw_counts else 0,
            events_raw_pending=int(events_raw_counts["pending"]) if events_raw_counts else 0,
            events_raw_enriched=int(events_raw_counts["enriched"]) if events_raw_counts else 0,
            events_raw_error=int(events_raw_counts["error"]) if events_raw_counts else 0,
            events_candidate_count=total_candidates,
            events_candidate_by_state=candidate_by_state,
            events_published_count=published_count,
            events_visible_in_frontend=visible_count,
        )
    except HTTPException:
        raise
    except (asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        logger.error(
            "event_source_diagnostics_failed",
            source_id=source_id,
            error=str(exc),
            admin=admin.email,
        )
        raise HTTPException(
            status_code=503,
            detail="event source diagnostics unavailable",
        ) from exc


