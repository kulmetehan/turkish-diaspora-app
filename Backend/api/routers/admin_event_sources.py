from __future__ import annotations

from typing import List, Optional

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

from app.core.logging import get_logger
from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.event_sources import EventSource, EventSourceCreate, EventSourceUpdate
from services.db_service import execute, fetchrow
from services.event_sources_service import (
    create_event_source,
    get_event_source,
    list_event_sources as svc_list_event_sources,
    set_event_source_status,
    update_event_source as svc_update_event_source,
)

router = APIRouter(
    prefix="/admin/event-sources",
    tags=["admin-event-sources"],
)

logger = get_logger()


class EventSourcesResponse(BaseModel):
    items: List[EventSource]


class ToggleStatusResponse(BaseModel):
    id: int
    status: str


def _handle_db_error(exc: Exception) -> None:
    if isinstance(exc, asyncpg.UniqueViolationError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="key must be unique",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to process request",
    ) from exc


@router.get("", response_model=EventSourcesResponse)
async def list_event_sources(
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Optional status filter (active/disabled).",
    ),
    admin: AdminUser = Depends(verify_admin_user),
) -> EventSourcesResponse:
    try:
        items = await svc_list_event_sources(status=status_filter)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return EventSourcesResponse(items=items)


@router.post("", response_model=EventSource, status_code=status.HTTP_201_CREATED)
async def create_event_source_route(
    payload: EventSourceCreate,
    admin: AdminUser = Depends(verify_admin_user),
) -> EventSource:
    try:
        return await create_event_source(payload)
    except Exception as exc:  # pragma: no cover - fallback
        logger.warning("event_source_create_failed", error=str(exc))
        _handle_db_error(exc)


@router.put("/{source_id}", response_model=EventSource)
async def update_event_source_route(
    payload: EventSourceUpdate,
    source_id: int = Path(..., ge=1),
    admin: AdminUser = Depends(verify_admin_user),
) -> EventSource:
    try:
        updated = await svc_update_event_source(source_id, payload)
    except Exception as exc:  # pragma: no cover - fallback
        logger.warning("event_source_update_failed", id=source_id, error=str(exc))
        _handle_db_error(exc)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event source not found")
    return updated


@router.post("/{source_id}/toggle-status", response_model=ToggleStatusResponse)
async def toggle_event_source_status(
    source_id: int = Path(..., ge=1),
    admin: AdminUser = Depends(verify_admin_user),
) -> ToggleStatusResponse:
    existing = await get_event_source(source_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event source not found")
    new_status = "disabled" if existing.status == "active" else "active"
    updated = await set_event_source_status(source_id, new_status)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event source not found")
    logger.info(
        "event_source_status_toggled",
        id=source_id,
        previous=existing.status,
        current=updated.status,
        admin=admin.email,
    )
    return ToggleStatusResponse(id=updated.id, status=updated.status)


class DeleteEventSourceResponse(BaseModel):
    id: int
    key: str
    name: str
    deleted: bool
    cascade: bool
    related_records_deleted: int


@router.delete("/{source_id}", response_model=DeleteEventSourceResponse)
async def delete_event_source(
    source_id: int = Path(..., ge=1, description="Event source ID"),
    cascade: bool = Query(
        default=False,
        description="If true, delete related event_raw, events_candidate, and event_pages_raw records. If false, deletion will fail if there are related records.",
    ),
    admin: AdminUser = Depends(verify_admin_user),
) -> DeleteEventSourceResponse:
    """
    Delete an event source.
    
    By default, deletion will fail if there are related records (event_raw, events_candidate, event_pages_raw).
    Set cascade=true to delete the source and all related records.
    """
    try:
        # Check if source exists
        source_row = await fetchrow(
            "SELECT id, key, name FROM event_sources WHERE id = $1",
            source_id,
        )
        if not source_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event source not found")
        
        source_key = str(source_row["key"])
        source_name = str(source_row["name"])
        
        # Check for related records
        related_counts = await fetchrow(
            """
            SELECT 
                (SELECT COUNT(*) FROM event_pages_raw WHERE event_source_id = $1) AS pages_count,
                (SELECT COUNT(*) FROM event_raw WHERE event_source_id = $1) AS raw_count,
                (SELECT COUNT(*) FROM events_candidate WHERE event_source_id = $1) AS candidate_count
            """,
            source_id,
        )
        
        pages_count = int(related_counts["pages_count"]) if related_counts else 0
        raw_count = int(related_counts["raw_count"]) if related_counts else 0
        candidate_count = int(related_counts["candidate_count"]) if related_counts else 0
        total_related = pages_count + raw_count + candidate_count
        
        if total_related > 0 and not cascade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot delete source: {total_related} related records exist "
                    f"(pages: {pages_count}, raw: {raw_count}, candidates: {candidate_count}). "
                    "Set cascade=true to delete source and all related records."
                ),
            )
        
        # Delete related records if cascade
        if cascade and total_related > 0:
            # Delete in order: candidates -> raw -> pages (respecting foreign keys)
            await execute(
                "DELETE FROM events_candidate WHERE event_source_id = $1",
                source_id,
            )
            await execute(
                "DELETE FROM event_raw WHERE event_source_id = $1",
                source_id,
            )
            await execute(
                "DELETE FROM event_pages_raw WHERE event_source_id = $1",
                source_id,
            )
            logger.info(
                "event_source_cascade_deleted",
                source_id=source_id,
                source_key=source_key,
                pages_deleted=pages_count,
                raw_deleted=raw_count,
                candidates_deleted=candidate_count,
                admin=admin.email,
            )
        
        # Delete the source
        await execute(
            "DELETE FROM event_sources WHERE id = $1",
            source_id,
        )
        
        logger.info(
            "event_source_deleted",
            source_id=source_id,
            source_key=source_key,
            source_name=source_name,
            cascade=cascade,
            admin=admin.email,
        )
        
        return DeleteEventSourceResponse(
            id=source_id,
            key=source_key,
            name=source_name,
            deleted=True,
            cascade=cascade,
            related_records_deleted=total_related if cascade else 0,
        )
    except HTTPException:
        raise
    except asyncpg.ForeignKeyViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete source: foreign key constraint violation. Set cascade=true to delete related records.",
        ) from exc
    except (asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        logger.error(
            "event_source_delete_failed",
            source_id=source_id,
            error=str(exc),
            admin=admin.email,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event source: {str(exc)}",
        ) from exc


