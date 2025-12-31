# Backend/api/routers/check_ins.py
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from starlette.requests import Request
from typing import Optional, List, Dict, Literal, Any
from pydantic import BaseModel
from datetime import datetime

from app.core.client_id import require_client_id, get_client_id
from app.core.feature_flags import require_feature
from app.deps.auth import get_current_user_optional, User
from app.deps.rate_limiting import require_rate_limit_factory
from services.db_service import fetch, execute
from services.xp_service import award_xp
from services.activity_summary_service import update_user_activity_summary

router = APIRouter(prefix="/locations", tags=["check-ins"])


class CheckInStats(BaseModel):
    location_id: int
    total_check_ins: int
    check_ins_today: int
    unique_users_today: int
    check_ins_this_week: Optional[int] = 0
    status_text: Optional[str] = None


@router.post("/{location_id}/check-ins")
async def create_check_in(
    request: Request,
    location_id: int = Path(..., description="Location ID"),
    client_id: str = Depends(require_client_id),
    _rate_limit: None = Depends(require_rate_limit_factory("check_in")),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Create a check-in for a location."""
    require_feature("check_ins_enabled")
    
    user_id = user.user_id if user else None
    
    # TODO: Verify location exists
    # TODO: Check duplicate (max 3 per day per location per user/client)
    
    # Insert check-in
    try:
        # Check if check-in already exists for today
        if user_id:
            check_sql = """
                SELECT id FROM check_ins
                WHERE location_id = $1 
                  AND user_id = $2
                  AND DATE(created_at) = CURRENT_DATE
                LIMIT 1
            """
            existing = await fetch(check_sql, location_id, user_id)
        else:
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
        
        if user_id:
            sql = """
                INSERT INTO check_ins (location_id, user_id, client_id, created_at)
                VALUES ($1, $2, $3, now())
                RETURNING id
            """
            row = await fetch(sql, location_id, user_id, client_id)
        else:
            sql = """
                INSERT INTO check_ins (location_id, client_id, created_at)
                VALUES ($1, $2, now())
                RETURNING id
            """
            row = await fetch(sql, location_id, client_id)
        
        check_in_id = row[0]["id"] if row else None
        
        # Award XP (only works for authenticated users after Story 9)
        if user_id:
            await award_xp(user_id=user_id, client_id=client_id, source="check_in", source_id=check_in_id)
            # Update activity summary (fire-and-forget async task)
            asyncio.create_task(update_user_activity_summary(user_id=user_id))
        
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
            COUNT(DISTINCT COALESCE(user_id::text, client_id::text)) FILTER (WHERE DATE(created_at) = CURRENT_DATE) as unique_users_today,
            COUNT(*) FILTER (WHERE DATE_TRUNC('week', created_at) = DATE_TRUNC('week', CURRENT_DATE)) as check_ins_this_week
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
            check_ins_this_week=0,
            status_text=None,
        )
    
    row = rows[0]
    check_ins_today = row.get("check_ins_today", 0) or 0
    check_ins_this_week = row.get("check_ins_this_week", 0) or 0
    
    # Calculate status text
    status_text = None
    if check_ins_today > 0:
        status_text = "Bugün canlı"
    elif check_ins_this_week <= 2:
        status_text = "Bu hafta sakin"
    
    return CheckInStats(
        location_id=location_id,
        total_check_ins=row.get("total_check_ins", 0) or 0,
        check_ins_today=check_ins_today,
        unique_users_today=row.get("unique_users_today", 0) or 0,
        check_ins_this_week=check_ins_this_week,
        status_text=status_text,
    )


class MahallelisiResponse(BaseModel):
    user_id: str
    name: str
    check_in_count: int
    primary_role: Optional[str] = None
    secondary_role: Optional[str] = None


@router.get("/{location_id}/mahallelisi", response_model=Optional[MahallelisiResponse])
async def get_location_mahallelisi(
    location_id: int = Path(..., description="Location ID"),
):
    """Get the most active user (Mahallelisi) for this location this week."""
    require_feature("check_ins_enabled")
    
    # Query for user with most check-ins this week
    # Note: We filter for authenticated users only (user_id IS NOT NULL)
    sql = """
        SELECT 
            ci.user_id,
            COUNT(*) as check_in_count,
            up.display_name,
            ur.primary_role,
            ur.secondary_role
        FROM check_ins ci
        INNER JOIN user_profiles up ON ci.user_id = up.id
        LEFT JOIN user_roles ur ON ur.user_id = ci.user_id AND ur.city_key = up.city_key
        WHERE ci.location_id = $1
          AND ci.user_id IS NOT NULL
          AND DATE_TRUNC('week', ci.created_at) = DATE_TRUNC('week', CURRENT_DATE)
        GROUP BY ci.user_id, up.display_name, ur.primary_role, ur.secondary_role
        ORDER BY check_in_count DESC
        LIMIT 1
    """
    
    rows = await fetch(sql, location_id)
    
    if not rows or len(rows) == 0:
        return None
    
    row = rows[0]
    display_name = row.get("display_name") or "Anonim"
    
    return MahallelisiResponse(
        user_id=str(row["user_id"]),
        name=display_name,
        check_in_count=row.get("check_in_count", 0) or 0,
        primary_role=row.get("primary_role"),
        secondary_role=row.get("secondary_role"),
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


class UserCheckIn(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    checked_in_at: str


class CheckInItem(BaseModel):
    location_id: int
    type: Literal["single", "cluster"]
    lat: float
    lng: float
    count: Optional[int] = None
    users: List[UserCheckIn]


class ActiveCheckInsResponse(BaseModel):
    items: List[CheckInItem]


@router.get("/check-ins/active-users", response_model=ActiveCheckInsResponse)
async def get_active_check_ins(
    bbox: Optional[str] = Query(None, description="Bounding box: min_lng,min_lat,max_lng,max_lat"),
    limit: int = Query(200, le=500, description="Maximum number of check-ins to return"),
):
    """Get recent check-ins with user avatars for map display (last 24 hours)."""
    require_feature("check_ins_enabled")
    
    logger = logging.getLogger(__name__)
    
    # Build base query
    params: List[Any] = []
    param_num = 1
    
    sql = """
        SELECT DISTINCT ON (ci.location_id, ci.user_id)
            ci.location_id,
            ci.user_id,
            ci.created_at,
            l.lat,
            l.lng,
            up.display_name,
            up.avatar_url
        FROM check_ins ci
        INNER JOIN locations l ON ci.location_id = l.id
        LEFT JOIN user_profiles up ON ci.user_id = up.id
        WHERE ci.user_id IS NOT NULL
          AND ci.created_at >= NOW() - INTERVAL '24 hours'
          AND l.lat IS NOT NULL 
          AND l.lng IS NOT NULL
    """
    
    # Add bbox filter if provided
    if bbox:
        try:
            parts = bbox.split(",")
            if len(parts) == 4:
                min_lng, min_lat, max_lng, max_lat = map(float, parts)
                logger.info(f"[check-ins] Filtering by bbox: {min_lng},{min_lat},{max_lng},{max_lat}")
                sql += f"""
                  AND l.lng >= ${param_num} AND l.lng <= ${param_num + 1}
                  AND l.lat >= ${param_num + 2} AND l.lat <= ${param_num + 3}
                """
                params.extend([min_lng, max_lng, min_lat, max_lat])
                param_num += 4
        except (ValueError, IndexError) as e:
            # Invalid bbox format, ignore it
            logger.warning(f"[check-ins] Invalid bbox format: {bbox}, error: {e}")
            pass
    
    sql += f"""
        ORDER BY ci.location_id, ci.user_id, ci.created_at DESC
        LIMIT ${param_num}
    """
    params.append(limit)
    
    logger.info(f"[check-ins] Executing query with {len(params)} params, limit={limit}")
    logger.debug(f"[check-ins] SQL: {sql}")
    
    rows = await fetch(sql, *params)
    logger.info(f"[check-ins] Query returned {len(rows)} rows")
    
    # Group by location_id
    locations_map: Dict[int, List[Dict]] = defaultdict(list)
    skipped_count = 0
    for r in rows:
        loc_id = r["location_id"]
        # Ensure lat/lng are floats (they might come as strings from DB)
        try:
            lat = float(r["lat"]) if r["lat"] is not None else None
            lng = float(r["lng"]) if r["lng"] is not None else None
        except (ValueError, TypeError) as e:
            logger.warning(f"[check-ins] Invalid lat/lng for location {loc_id}: lat={r.get('lat')}, lng={r.get('lng')}, error={e}")
            skipped_count += 1
            continue
        
        if lat is None or lng is None:
            logger.warning(f"[check-ins] Missing lat/lng for location {loc_id}")
            skipped_count += 1
            continue  # Skip entries without valid coordinates
        
        locations_map[loc_id].append({
            "user_id": str(r["user_id"]),
            "lat": lat,
            "lng": lng,
            "display_name": r.get("display_name"),
            "avatar_url": r.get("avatar_url"),
            "checked_in_at": r["created_at"].isoformat() if isinstance(r["created_at"], datetime) else str(r["created_at"]),
        })
    
    logger.info(f"[check-ins] Grouped into {len(locations_map)} locations, skipped {skipped_count} rows")
    
    # Convert to response format
    items: List[CheckInItem] = []
    for loc_id, users in locations_map.items():
        if len(users) == 0:
            continue
        
        # Limit users per location to 5 for preview
        preview_users = users[:5]
        
        if len(users) == 1:
            items.append(CheckInItem(
                location_id=loc_id,
                type="single",
                lat=preview_users[0]["lat"],
                lng=preview_users[0]["lng"],
                users=[
                    UserCheckIn(
                        user_id=u["user_id"],
                        display_name=u["display_name"],
                        avatar_url=u["avatar_url"],
                        checked_in_at=u["checked_in_at"],
                    )
                    for u in preview_users
                ],
            ))
        else:
            items.append(CheckInItem(
                location_id=loc_id,
                type="cluster",
                lat=preview_users[0]["lat"],
                lng=preview_users[0]["lng"],
                count=len(users),
                users=[
                    UserCheckIn(
                        user_id=u["user_id"],
                        display_name=u["display_name"],
                        avatar_url=u["avatar_url"],
                        checked_in_at=u["checked_in_at"],
                    )
                    for u in preview_users
                ],
            ))
    
    logger.info(f"[check-ins] Returning {len(items)} items")
    return ActiveCheckInsResponse(items=items)

