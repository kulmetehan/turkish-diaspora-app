# Backend/api/routers/favorites.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.core.client_id import require_client_id, get_client_id
from app.core.feature_flags import require_feature
from services.db_service import fetch
from services.xp_service import award_xp

# Router for location-specific favorites endpoints
location_favorites_router = APIRouter(prefix="/locations", tags=["favorites"])

# Router for general favorites endpoints
favorites_router = APIRouter(prefix="/favorites", tags=["favorites"])


class FavoriteItem(BaseModel):
    id: int
    location_id: int
    location_name: str | None
    location_lat: float | None
    location_lng: float | None
    created_at: datetime


@location_favorites_router.post("/{location_id}/favorites")
async def create_favorite(
    location_id: int = Path(..., description="Location ID"),
    client_id: str = Depends(require_client_id),
    # TODO: user_id: Optional[UUID] = Depends(get_current_user_optional),
):
    """Add a location to favorites."""
    require_feature("check_ins_enabled")  # Or create separate flag
    
    # TODO: Verify location exists
    
    try:
        # Check if favorite already exists
        check_sql = """
            SELECT id FROM favorites
            WHERE location_id = $1 
              AND client_id = $2
            LIMIT 1
        """
        existing = await fetch(check_sql, location_id, client_id)
        if existing:
            raise HTTPException(status_code=409, detail="Location already in favorites")
        
        # Insert favorite
        sql = """
            INSERT INTO favorites (location_id, client_id, created_at)
            VALUES ($1, $2, now())
            RETURNING id
        """
        row = await fetch(sql, location_id, client_id)
        
        favorite_id = row[0]["id"] if row else None
        
        # Award XP (only works for authenticated users after Story 9)
        user_id = None  # TODO: Extract from auth session when available
        if user_id:
            await award_xp(user_id=user_id, client_id=client_id, source="favorite", source_id=favorite_id)
        
        return {"ok": True, "favorite_id": favorite_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create favorite: {str(e)}")


@location_favorites_router.delete("/{location_id}/favorites")
async def delete_favorite(
    location_id: int = Path(..., description="Location ID"),
    client_id: str = Depends(require_client_id),
    # TODO: user_id: Optional[UUID] = Depends(get_current_user_optional),
):
    """Remove a location from favorites."""
    require_feature("check_ins_enabled")
    
    sql = """
        DELETE FROM favorites
        WHERE location_id = $1 
          AND client_id = $2
        RETURNING id
    """
    
    row = await fetch(sql, location_id, client_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    return {"ok": True}


@favorites_router.get("", response_model=List[FavoriteItem])
async def get_favorites(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    client_id: str | None = Depends(get_client_id),
    # TODO: user_id: Optional[UUID] = Depends(get_current_user_optional),
):
    """Get all favorites for current user/client."""
    require_feature("check_ins_enabled")
    
    if not client_id:
        return []
    
    sql = """
        SELECT 
            f.id,
            f.location_id,
            l.name as location_name,
            l.lat as location_lat,
            l.lng as location_lng,
            f.created_at
        FROM favorites f
        LEFT JOIN locations l ON f.location_id = l.id
        WHERE f.client_id = $1
        ORDER BY f.created_at DESC
        LIMIT $2 OFFSET $3
    """
    
    rows = await fetch(sql, client_id, limit, offset)
    
    return [
        FavoriteItem(
            id=row["id"],
            location_id=row["location_id"],
            location_name=row.get("location_name"),
            location_lat=row.get("location_lat"),
            location_lng=row.get("location_lng"),
            created_at=row["created_at"],
        )
        for row in rows
    ]
