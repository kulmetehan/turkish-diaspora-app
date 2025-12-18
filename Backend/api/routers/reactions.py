# Backend/api/routers/reactions.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from starlette.requests import Request
from typing import Dict, Optional
from pydantic import BaseModel

from app.core.client_id import get_client_id, require_client_id
from app.core.feature_flags import require_feature
from app.deps.rate_limiting import require_rate_limit_factory
from services.db_service import fetch, execute
from services.xp_service import award_xp

router = APIRouter(prefix="/locations", tags=["reactions"])


VALID_REACTION_TYPES = {'fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag'}


class ReactionToggleRequest(BaseModel):
    reaction_type: str  # 'fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag'


class ReactionStats(BaseModel):
    location_id: int
    reactions: Dict[str, int]  # {reaction_type: count}
    user_reaction: Optional[str] = None  # Current user's reaction type, if any


@router.post("/{location_id}/reactions", response_model=dict)
async def toggle_location_reaction(
    location_id: int = Path(..., description="Location ID"),
    request: ReactionToggleRequest = ...,
    client_id: Optional[str] = Depends(get_client_id),
    _rate_limit: None = Depends(require_rate_limit_factory("reaction")),
):
    """Toggle emoji reaction on location."""
    require_feature("reactions_enabled")
    
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id required")
    
    # Validate reaction type
    if request.reaction_type not in VALID_REACTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reaction_type. Must be one of: {', '.join(VALID_REACTION_TYPES)}"
        )
    
    user_id = None  # TODO: Extract from auth session
    
    # Check if location exists
    check_sql = "SELECT id FROM locations WHERE id = $1"
    check_rows = await fetch(check_sql, location_id)
    if not check_rows:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Check if already reacted with this type
    if user_id:
        check_reaction_sql = """
            SELECT id FROM location_reactions 
            WHERE location_id = $1 AND user_id = $2 AND reaction_type = $3
        """
        existing = await fetch(check_reaction_sql, location_id, user_id, request.reaction_type)
    else:
        check_reaction_sql = """
            SELECT id FROM location_reactions 
            WHERE location_id = $1 AND client_id = $2 AND reaction_type = $3
        """
        existing = await fetch(check_reaction_sql, location_id, client_id, request.reaction_type)
    
    if existing:
        # Remove reaction
        if user_id:
            delete_sql = """
                DELETE FROM location_reactions 
                WHERE location_id = $1 AND user_id = $2 AND reaction_type = $3
            """
            await execute(delete_sql, location_id, user_id, request.reaction_type)
        else:
            delete_sql = """
                DELETE FROM location_reactions 
                WHERE location_id = $1 AND client_id = $2 AND reaction_type = $3
            """
            await execute(delete_sql, location_id, client_id, request.reaction_type)
        is_active = False
    else:
        # Add reaction
        if user_id:
            insert_sql = """
                INSERT INTO location_reactions (location_id, user_id, reaction_type, created_at) 
                VALUES ($1, $2, $3, now()) ON CONFLICT DO NOTHING
            """
            await execute(insert_sql, location_id, user_id, request.reaction_type)
        else:
            insert_sql = """
                INSERT INTO location_reactions (location_id, client_id, reaction_type, created_at) 
                VALUES ($1, $2::uuid, $3, now()) ON CONFLICT DO NOTHING
            """
            await execute(insert_sql, location_id, client_id, request.reaction_type)
        is_active = True
    
    # Get updated count
    count_sql = """
        SELECT COUNT(*) as count 
        FROM location_reactions 
        WHERE location_id = $1 AND reaction_type = $2
    """
    count_rows = await fetch(count_sql, location_id, request.reaction_type)
    count = count_rows[0]["count"] if count_rows else 0
    
    return {
        "reaction_type": request.reaction_type,
        "is_active": is_active,
        "count": count
    }


@router.get("/{location_id}/reactions", response_model=ReactionStats)
async def get_reactions(
    location_id: int = Path(..., description="Location ID"),
    client_id: Optional[str] = Depends(get_client_id),
):
    """Get aggregated reaction counts and user reaction for a location."""
    require_feature("reactions_enabled")
    
    # Check if location exists
    check_sql = "SELECT id FROM locations WHERE id = $1"
    check_rows = await fetch(check_sql, location_id)
    if not check_rows:
        raise HTTPException(status_code=404, detail="Location not found")
    
    user_id = None  # TODO: Extract from auth session
    
    # Get reaction counts grouped by type
    counts_sql = """
        SELECT 
            reaction_type,
            COUNT(*) as count
        FROM location_reactions
        WHERE location_id = $1
        GROUP BY reaction_type
    """
    count_rows = await fetch(counts_sql, location_id)
    
    # Build reactions dict with all types initialized to 0
    reactions = {
        "fire": 0,
        "heart": 0,
        "thumbs_up": 0,
        "smile": 0,
        "star": 0,
        "flag": 0,
    }
    
    for row in count_rows:
        reaction_type = row["reaction_type"]
        if reaction_type in reactions:
            reactions[reaction_type] = row.get("count", 0) or 0
    
    # Get user's reaction if any
    user_reaction = None
    if user_id:
        user_reaction_sql = """
            SELECT reaction_type FROM location_reactions
            WHERE location_id = $1 AND user_id = $2
            LIMIT 1
        """
        user_reaction_rows = await fetch(user_reaction_sql, location_id, user_id)
        if user_reaction_rows:
            user_reaction = user_reaction_rows[0]["reaction_type"]
    elif client_id:
        user_reaction_sql = """
            SELECT reaction_type FROM location_reactions
            WHERE location_id = $1 AND client_id = $2
            LIMIT 1
        """
        user_reaction_rows = await fetch(user_reaction_sql, location_id, client_id)
        if user_reaction_rows:
            user_reaction = user_reaction_rows[0]["reaction_type"]
    
    return ReactionStats(
        location_id=location_id,
        reactions=reactions,
        user_reaction=user_reaction,
    )

