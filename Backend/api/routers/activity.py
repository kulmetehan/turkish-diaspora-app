# Backend/api/routers/activity.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Path
from typing import List, Optional, Tuple, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import math
import json

from app.core.client_id import get_client_id
from app.core.feature_flags import require_feature
from services.db_service import fetch

router = APIRouter(prefix="/activity", tags=["activity"])


class ActivityItem(BaseModel):
    id: int
    activity_type: str  # 'check_in', 'reaction', 'note', 'poll_response', 'favorite'
    location_id: Optional[int]
    location_name: Optional[str]
    payload: dict  # Activity-specific details
    created_at: datetime
    is_promoted: bool = False


def _parse_payload(payload: Any) -> dict:
    """Parse payload from database (can be string or dict)."""
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            return json.loads(payload) if payload else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


@router.get("", response_model=List[ActivityItem])
async def get_own_activity(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    activity_type: Optional[str] = Query(None, description="Filter by activity type (check_in, reaction, note, poll_response, favorite)"),
    client_id: Optional[str] = Depends(get_client_id),
    # TODO: current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get own activity stream (user_id or client_id)."""
    require_feature("check_ins_enabled")  # Or create separate flag
    
    if not client_id:
        return []
    
    # Build WHERE clause with optional activity_type filter
    conditions = ["ast.client_id = $1"]
    params = [client_id]
    param_num = 2
    
    if activity_type:
        # Validate activity_type
        valid_types = ["check_in", "reaction", "note", "poll_response", "favorite"]
        if activity_type not in valid_types:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Invalid activity_type. Must be one of: {', '.join(valid_types)}"
            )
        conditions.append(f"ast.activity_type = ${param_num}")
        params.append(activity_type)
        param_num += 1
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            ast.id,
            ast.activity_type,
            ast.location_id,
            l.name as location_name,
            ast.payload,
            ast.created_at,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                    AND pl.promotion_type IN ('feed', 'both')
                    AND pl.starts_at <= now()
                    AND pl.ends_at > now()
                THEN true 
                ELSE false 
            END as is_promoted
        FROM activity_stream ast
        LEFT JOIN locations l ON ast.location_id = l.id
        LEFT JOIN promoted_locations pl ON pl.location_id = ast.location_id
        WHERE {where_clause}
        ORDER BY is_promoted DESC, ast.created_at DESC
        LIMIT ${param_num} OFFSET ${param_num + 1}
    """
    
    params.extend([limit, offset])
    
    rows = await fetch(sql, *params)
    
    return [
        ActivityItem(
            id=row["id"],
            activity_type=row["activity_type"],
            location_id=row.get("location_id"),
            location_name=row.get("location_name"),
            payload=_parse_payload(row.get("payload")),
            created_at=row["created_at"],
            is_promoted=row.get("is_promoted", False),
        )
        for row in rows
    ]


def calculate_bbox(center_lat: float, center_lng: float, radius_m: int) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box from center point and radius.
    
    Returns: (lat_min, lat_max, lng_min, lng_max)
    """
    # Approximate: 1 degree latitude ≈ 111 km
    # Longitude depends on latitude (smaller at higher latitudes)
    lat_pad = radius_m / 111000.0
    lng_pad = radius_m / (111000.0 * max(math.cos(math.radians(center_lat)), 0.2))
    
    return (
        center_lat - lat_pad,
        center_lat + lat_pad,
        center_lng - lng_pad,
        center_lng + lng_pad,
    )


def parse_time_window(window_str: str) -> Optional[timedelta]:
    """
    Parse time window string like "24h", "7d", "1w" into timedelta.
    Returns None if invalid.
    """
    if not window_str:
        return timedelta(hours=24)  # Default 24 hours
    
    window_str = window_str.strip().lower()
    
    try:
        if window_str.endswith("h"):
            hours = int(window_str[:-1])
            return timedelta(hours=hours)
        elif window_str.endswith("d"):
            days = int(window_str[:-1])
            return timedelta(days=days)
        elif window_str.endswith("w"):
            weeks = int(window_str[:-1])
            return timedelta(weeks=weeks)
        else:
            # Try to parse as hours if no suffix
            hours = int(window_str)
            return timedelta(hours=hours)
    except (ValueError, AttributeError):
        return timedelta(hours=24)  # Default fallback


@router.get("/nearby", response_model=List[ActivityItem])
async def get_nearby_activity(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius_m: int = Query(1000, description="Radius in meters"),
    window: str = Query("24h", description="Time window (e.g., '24h', '7d', '1w')"),
    limit: int = Query(50, le=100),
):
    """Get nearby activity feed."""
    require_feature("check_ins_enabled")
    
    # Calculate bounding box
    lat_min, lat_max, lng_min, lng_max = calculate_bbox(lat, lng, radius_m)
    
    # Parse time window
    time_window = parse_time_window(window)
    window_start = datetime.now() - time_window if time_window else None
    
    # Build SQL query with bounding box filter
    # Join activity_stream with locations to get coordinates
    conditions = [
        "l.lat IS NOT NULL",
        "l.lng IS NOT NULL",
        "l.lat BETWEEN $1 AND $2",
        "l.lng BETWEEN $3 AND $4",
    ]
    params = [lat_min, lat_max, lng_min, lng_max]
    param_num = 5
    
    if window_start:
        conditions.append(f"ast.created_at >= ${param_num}")
        params.append(window_start)
        param_num += 1
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            ast.id,
            ast.activity_type,
            ast.location_id,
            l.name as location_name,
            ast.payload,
            ast.created_at,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                    AND pl.promotion_type IN ('feed', 'both')
                    AND pl.starts_at <= now()
                    AND pl.ends_at > now()
                THEN true 
                ELSE false 
            END as is_promoted
        FROM activity_stream ast
        INNER JOIN locations l ON ast.location_id = l.id
        LEFT JOIN promoted_locations pl ON pl.location_id = ast.location_id
        WHERE {where_clause}
        ORDER BY is_promoted DESC, ast.created_at DESC
        LIMIT ${param_num}
    """
    params.append(limit)
    
    rows = await fetch(sql, *params)
    
    return [
        ActivityItem(
            id=row["id"],
            activity_type=row["activity_type"],
            location_id=row.get("location_id"),
            location_name=row.get("location_name"),
            payload=_parse_payload(row.get("payload")),
            created_at=row["created_at"],
            is_promoted=row.get("is_promoted", False),
        )
        for row in rows
    ]


@router.get("/locations/{location_id}", response_model=List[ActivityItem])
async def get_location_activity(
    location_id: int = Path(..., description="Location ID"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
):
    """Get activity for a specific location."""
    require_feature("check_ins_enabled")
    
    sql = """
        SELECT 
            ast.id,
            ast.activity_type,
            ast.location_id,
            l.name as location_name,
            ast.payload,
            ast.created_at,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                    AND pl.promotion_type IN ('feed', 'both')
                    AND pl.starts_at <= now()
                    AND pl.ends_at > now()
                THEN true 
                ELSE false 
            END as is_promoted
        FROM activity_stream ast
        LEFT JOIN locations l ON ast.location_id = l.id
        LEFT JOIN promoted_locations pl ON pl.location_id = ast.location_id
        WHERE ast.location_id = $1
        ORDER BY is_promoted DESC, ast.created_at DESC
        LIMIT $2 OFFSET $3
    """
    
    rows = await fetch(sql, location_id, limit, offset)
    
    return [
        ActivityItem(
            id=row["id"],
            activity_type=row["activity_type"],
            location_id=row.get("location_id"),
            location_name=row.get("location_name"),
            payload=_parse_payload(row.get("payload")),
            created_at=row["created_at"],
            is_promoted=row.get("is_promoted", False),
        )
        for row in rows
    ]



