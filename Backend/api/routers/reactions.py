# Backend/api/routers/reactions.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from starlette.requests import Request
from typing import Dict
from pydantic import BaseModel

from app.core.client_id import require_client_id
from app.core.feature_flags import require_feature
from app.deps.rate_limiting import require_rate_limit_factory
from services.db_service import fetch, execute
from services.xp_service import award_xp

router = APIRouter(prefix="/locations", tags=["reactions"])


VALID_REACTION_TYPES = {'fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag'}


class ReactionCreate(BaseModel):
    reaction_type: str  # 'fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag'


class ReactionStats(BaseModel):
    location_id: int
    reactions: Dict[str, int]  # {reaction_type: count}


@router.post("/{location_id}/reactions")
async def create_reaction(
    request: Request,
    location_id: int = Path(..., description="Location ID"),
    reaction: ReactionCreate = ...,
    client_id: str = Depends(require_client_id),
    _rate_limit: None = Depends(require_rate_limit_factory("reaction")),
):
    """Add a reaction to a location."""
    require_feature("reactions_enabled")
    
    if reaction.reaction_type not in VALID_REACTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reaction_type. Must be one of: {', '.join(VALID_REACTION_TYPES)}"
        )
    
    # TODO: Verify location exists
    
    try:
        # Check if reaction already exists
        check_sql = """
            SELECT id FROM location_reactions
            WHERE location_id = $1 
              AND client_id = $2
              AND reaction_type = $3
            LIMIT 1
        """
        existing = await fetch(check_sql, location_id, client_id, reaction.reaction_type)
        if existing:
            raise HTTPException(status_code=409, detail="Reaction already exists")
        
        sql = """
            INSERT INTO location_reactions (location_id, client_id, reaction_type, created_at)
            VALUES ($1, $2, $3, now())
            RETURNING id
        """
        row = await fetch(sql, location_id, client_id, reaction.reaction_type)
        
        reaction_id = row[0]["id"] if row else None
        
        # Award XP (only works for authenticated users after Story 9)
        user_id = None  # TODO: Extract from auth session when available
        if user_id:
            await award_xp(user_id=user_id, client_id=client_id, source="reaction", source_id=reaction_id)
        
        return {"ok": True, "reaction_id": reaction_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create reaction: {str(e)}")


@router.delete("/{location_id}/reactions/{reaction_type}")
async def remove_reaction(
    request: Request,
    location_id: int = Path(..., description="Location ID"),
    reaction_type: str = Path(..., description="Reaction type"),
    client_id: str = Depends(require_client_id),
    _rate_limit: None = Depends(require_rate_limit_factory("reaction")),
):
    """Remove a reaction from a location."""
    require_feature("reactions_enabled")
    
    if reaction_type not in VALID_REACTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reaction_type. Must be one of: {', '.join(VALID_REACTION_TYPES)}"
        )
    
    try:
        sql = """
            DELETE FROM location_reactions
            WHERE location_id = $1 
              AND client_id = $2
              AND reaction_type = $3
            RETURNING id
        """
        row = await fetch(sql, location_id, client_id, reaction_type)
        
        if not row:
            raise HTTPException(status_code=404, detail="Reaction not found")
        
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete reaction: {str(e)}")


@router.get("/{location_id}/reactions", response_model=ReactionStats)
async def get_reactions(
    location_id: int = Path(..., description="Location ID"),
):
    """Get aggregated reaction counts for a location."""
    require_feature("reactions_enabled")
    
    sql = """
        SELECT 
            reaction_type,
            COUNT(*) as count
        FROM location_reactions
        WHERE location_id = $1
        GROUP BY reaction_type
    """
    
    rows = await fetch(sql, location_id)
    
    reactions = {}
    for row in rows:
        reactions[row["reaction_type"]] = row.get("count", 0) or 0
    
    return ReactionStats(
        location_id=location_id,
        reactions=reactions,
    )

