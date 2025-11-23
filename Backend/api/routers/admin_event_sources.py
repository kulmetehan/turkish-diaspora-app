from __future__ import annotations

from typing import List, Optional

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

from app.core.logging import get_logger
from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.event_sources import EventSource, EventSourceCreate, EventSourceUpdate
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


