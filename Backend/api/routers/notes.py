# Backend/api/routers/notes.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from starlette.requests import Request
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.core.client_id import require_client_id, get_client_id
from app.core.feature_flags import require_feature
from app.deps.rate_limiting import require_rate_limit_factory
from services.db_service import fetch, execute
from services.xp_service import award_xp

router = APIRouter(prefix="/locations", tags=["notes"])


class NoteCreate(BaseModel):
    content: str  # 3-1000 chars


class NoteResponse(BaseModel):
    id: int
    location_id: int
    content: str
    is_edited: bool
    created_at: datetime
    updated_at: datetime
    # TODO: user info if available


@router.post("/{location_id}/notes", response_model=NoteResponse)
async def create_note(
    request: Request,
    location_id: int = Path(..., description="Location ID"),
    note: NoteCreate = ...,
    client_id: str = Depends(require_client_id),
    _rate_limit: None = Depends(require_rate_limit_factory("note")),
):
    """Create a note for a location."""
    require_feature("notes_enabled")
    
    # Validate content length
    if len(note.content) < 3 or len(note.content) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Note content must be between 3 and 1000 characters"
        )
    
    # TODO: Verify location exists
    
    try:
        sql = """
            INSERT INTO location_notes (location_id, client_id, content, created_at, updated_at)
            VALUES ($1, $2, $3, now(), now())
            RETURNING id, location_id, content, is_edited, created_at, updated_at
        """
        row = await fetch(sql, location_id, client_id, note.content)
        
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create note")
        
        result = row[0]
        
        # Award XP (only works for authenticated users after Story 9)
        user_id = None  # TODO: Extract from auth session when available
        if user_id:
            await award_xp(user_id=user_id, client_id=client_id, source="note", source_id=result["id"])
        
        return NoteResponse(
            id=result["id"],
            location_id=result["location_id"],
            content=result["content"],
            is_edited=result.get("is_edited", False),
            created_at=result["created_at"],
            updated_at=result["updated_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create note: {str(e)}")


@router.get("/{location_id}/notes", response_model=List[NoteResponse])
async def get_notes(
    location_id: int = Path(..., description="Location ID"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
):
    """Get notes for a location."""
    require_feature("notes_enabled")
    
    sql = """
        SELECT id, location_id, content, is_edited, created_at, updated_at
        FROM location_notes
        WHERE location_id = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
    """
    
    rows = await fetch(sql, location_id, limit, offset)
    
    return [
        NoteResponse(
            id=row["id"],
            location_id=row["location_id"],
            content=row["content"],
            is_edited=row.get("is_edited", False),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.put("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    request: Request,
    note_id: int = Path(..., description="Note ID"),
    note: NoteCreate = ...,
    client_id: str = Depends(require_client_id),
    _rate_limit: None = Depends(require_rate_limit_factory("note")),
):
    """Update own note."""
    require_feature("notes_enabled")
    
    if len(note.content) < 3 or len(note.content) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Note content must be between 3 and 1000 characters"
        )
    
    # Verify ownership
    sql = """
        UPDATE location_notes
        SET content = $1, is_edited = true, updated_at = now()
        WHERE id = $2 AND client_id = $3
        RETURNING id, location_id, content, is_edited, created_at, updated_at
    """
    
    row = await fetch(sql, note.content, note_id, client_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Note not found or not owned by client")
    
    result = row[0]
    return NoteResponse(
        id=result["id"],
        location_id=result["location_id"],
        content=result["content"],
        is_edited=result.get("is_edited", False),
        created_at=result["created_at"],
        updated_at=result["updated_at"],
    )


@router.delete("/notes/{note_id}")
async def delete_note(
    request: Request,
    note_id: int = Path(..., description="Note ID"),
    client_id: str = Depends(require_client_id),
    _rate_limit: None = Depends(require_rate_limit_factory("note")),
):
    """Delete own note."""
    require_feature("notes_enabled")
    
    sql = """
        DELETE FROM location_notes
        WHERE id = $1 AND client_id = $2
        RETURNING id
    """
    
    row = await fetch(sql, note_id, client_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Note not found or not owned by client")
    
    return {"ok": True}



