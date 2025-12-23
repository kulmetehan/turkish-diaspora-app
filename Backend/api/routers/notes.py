# Backend/api/routers/notes.py
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from starlette.requests import Request
from typing import List, Optional, Dict, Any
import json
from pydantic import BaseModel
from datetime import datetime

from app.core.client_id import require_client_id, get_client_id
from app.core.feature_flags import require_feature
from app.deps.auth import get_current_user_optional, User
from app.deps.rate_limiting import require_rate_limit_factory
from services.db_service import fetch, execute
from services.xp_service import award_xp
from services.activity_summary_service import update_user_activity_summary

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
    reaction_count: int = 0
    labels: List[str] = []
    # TODO: user info if available


@router.post("/{location_id}/notes", response_model=NoteResponse)
async def create_note(
    request: Request,
    location_id: int = Path(..., description="Location ID"),
    note: NoteCreate = ...,
    client_id: str = Depends(require_client_id),
    _rate_limit: None = Depends(require_rate_limit_factory("note")),
    user: Optional[User] = Depends(get_current_user_optional),
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
    
    user_id = user.user_id if user else None
    
    try:
        # Insert note with user_id if authenticated, otherwise just client_id
        if user_id:
            sql = """
                INSERT INTO location_notes (location_id, user_id, client_id, content, created_at, updated_at)
                VALUES ($1, $2, $3, $4, now(), now())
                RETURNING id, location_id, content, is_edited, created_at, updated_at
            """
            row = await fetch(sql, location_id, user_id, client_id, note.content)
        else:
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
        if user_id:
            await award_xp(user_id=user_id, client_id=client_id, source="note", source_id=result["id"])
            # Update activity summary (fire-and-forget async task)
            asyncio.create_task(update_user_activity_summary(user_id=user_id))
        
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


def _calculate_labels(reaction_count: int) -> List[str]:
    """Calculate labels for notes based on reaction count."""
    labels = []
    # Sözü Dinlenir: >= 5 reactions
    if reaction_count >= 5:
        labels.append("sözü_dinlenir")
    # Yerinde Tespit: Future implementation requires "nuttig" markers
    return labels


def _parse_reactions(reactions: Any) -> Optional[Dict[str, int]]:
    """Parse reactions JSON from database."""
    if reactions is None:
        return None
    if isinstance(reactions, dict):
        return reactions
    if isinstance(reactions, str):
        try:
            parsed = json.loads(reactions)
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


@router.get("/{location_id}/notes", response_model=List[NoteResponse])
async def get_notes(
    location_id: int = Path(..., description="Location ID"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("reactions_desc", description="Sort by: reactions_desc, created_at_desc"),
):
    """Get notes for a location."""
    require_feature("notes_enabled")
    
    # Validate sort_by
    valid_sorts = ["reactions_desc", "created_at_desc"]
    if sort_by not in valid_sorts:
        sort_by = "reactions_desc"
    
    # Query notes with reaction counts from activity_stream and activity_reactions
    # Match activity_stream entries by location_id, activity_type='note', and timestamp proximity
    sql = """
        SELECT 
            ln.id,
            ln.location_id,
            ln.content,
            ln.is_edited,
            ln.created_at,
            ln.updated_at,
            COALESCE(
                (
                    SELECT COUNT(*)::int
                    FROM activity_reactions ar
                    INNER JOIN activity_stream ast ON ar.activity_id = ast.id
                    WHERE ast.activity_type = 'note'
                      AND ast.location_id = ln.location_id
                      AND ABS(EXTRACT(EPOCH FROM (ast.created_at - ln.created_at))) < 10
                      AND ast.payload::text LIKE '%' || LEFT(ln.content, 30) || '%'
                ),
                0
            ) as reaction_count
        FROM location_notes ln
        WHERE ln.location_id = $1
    """
    
    # Add sorting
    if sort_by == "reactions_desc":
        sql += """
            ORDER BY reaction_count DESC, ln.created_at DESC
        """
    else:
        sql += """
            ORDER BY ln.created_at DESC
        """
    
    sql += """
        LIMIT $2 OFFSET $3
    """
    
    rows = await fetch(sql, location_id, limit, offset)
    
    result = []
    for row in rows:
        reaction_count = row.get("reaction_count", 0) or 0
        labels = _calculate_labels(reaction_count)
        
        result.append(
            NoteResponse(
                id=row["id"],
                location_id=row["location_id"],
                content=row["content"],
                is_edited=row.get("is_edited", False),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                reaction_count=reaction_count,
                labels=labels,
            )
        )
    
    return result


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



