# Backend/api/routers/check_ins.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from starlette.requests import Request
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.core.client_id import require_client_id, get_client_id
from app.core.feature_flags import require_feature
from app.deps.rate_limiting import require_rate_limit_factory
from services.db_service import fetch, execute
from services.xp_service import award_xp

router = APIRouter(prefix="/locations", tags=["check-ins"])


class CheckInStats(BaseModel):
    location_id: int
    total_check_ins: int
    check_ins_today: int
    unique_users_today: int


@router.post("/{location_id}/check-ins")
async def create_check_in(
    request: Request,
    location_id: int = Path(..., description="Location ID"),
    client_id: str = Depends(require_client_id),
    _rate_limit: None = Depends(require_rate_limit_factory("check_in")),
    # TODO: current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Create a check-in for a location."""
    require_feature("check_ins_enabled")
    
    # TODO: Verify location exists
    # TODO: Check duplicate (max 3 per day per location per user/client)
    
    # Insert check-in
    try:
        # Check if check-in already exists for today
        check_sql = """
            SELECT id FROM check_ins
            WHERE location_id = $1 
              AND client_id = $2
              AND DATE(created_at) = CURRENT_DATE
            LIMIT 1
        """
        existing = await fetch(check_sql, location_id, client_id)
        if existing:
            raise HTTPException(status_code=409, detail="Check-in already exists for today")
        
        sql = """
            INSERT INTO check_ins (location_id, client_id, created_at)
            VALUES ($1, $2, now())
            RETURNING id
        """
        row = await fetch(sql, location_id, client_id)
        
        check_in_id = row[0]["id"] if row else None
        
        # Award XP (only works for authenticated users after Story 9)
        user_id = None  # TODO: Extract from auth session when available
        if user_id:
            await award_xp(user_id=user_id, client_id=client_id, source="check_in", source_id=check_in_id)
        
        return {"ok": True, "check_in_id": check_in_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create check-in: {str(e)}")


@router.get("/{location_id}/check-ins", response_model=CheckInStats)
async def get_check_in_stats(
    location_id: int = Path(..., description="Location ID"),
):
    """Get check-in statistics for a location."""
    require_feature("check_ins_enabled")
    
    sql = """
        SELECT 
            COUNT(*) as total_check_ins,
            COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE) as check_ins_today,
            COUNT(DISTINCT COALESCE(user_id::text, client_id::text)) FILTER (WHERE DATE(created_at) = CURRENT_DATE) as unique_users_today
        FROM check_ins
        WHERE location_id = $1
    """
    
    rows = await fetch(sql, location_id)
    if not rows:
        return CheckInStats(
            location_id=location_id,
            total_check_ins=0,
            check_ins_today=0,
            unique_users_today=0,
        )
    
    row = rows[0]
    return CheckInStats(
        location_id=location_id,
        total_check_ins=row.get("total_check_ins", 0) or 0,
        check_ins_today=row.get("check_ins_today", 0) or 0,
        unique_users_today=row.get("unique_users_today", 0) or 0,
    )


@router.get("/check-ins/nearby")
async def get_nearby_check_ins(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius_m: int = Query(1000, description="Radius in meters"),
    limit: int = Query(50, le=100),
):
    """Get recent check-ins near a location."""
    require_feature("check_ins_enabled")
    
    # TODO: Geospatial query for nearby check-ins
    # For now, return empty list
    return {"items": [], "total": 0}

