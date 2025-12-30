# Backend/api/routers/activity.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Path, HTTPException
from typing import List, Optional, Tuple, Any, Dict
from pydantic import BaseModel
from datetime import datetime, timedelta
import math
import json

from app.core.client_id import get_client_id
from app.core.feature_flags import require_feature
from app.deps.auth import get_current_user_optional, User
from services.db_service import fetch, execute

router = APIRouter(prefix="/activity", tags=["activity"])


class ActivityUser(BaseModel):
    id: str  # UUID as string
    name: Optional[str] = None  # display_name
    avatar_url: Optional[str] = None
    primary_role: Optional[str] = None
    secondary_role: Optional[str] = None


class ActivityItem(BaseModel):
    id: int
    activity_type: str  # 'check_in', 'reaction', 'note', 'poll_response', 'favorite', 'bulletin_post', 'event'
    location_id: Optional[int]
    location_name: Optional[str]
    payload: dict  # Activity-specific details
    created_at: datetime
    is_promoted: bool = False
    media_url: Optional[str] = None
    user: Optional[ActivityUser] = None
    like_count: int = 0
    is_liked: bool = False
    is_bookmarked: bool = False
    reactions: Optional[dict] = None  # Reaction counts: {"fire": 5, "heart": 3, ...}
    user_reaction: Optional[str] = None  # Current user's reaction type, if any
    labels: Optional[List[str]] = None  # Labels like "sözü_dinlenir", "yerinde_tespit"


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


def _parse_reactions(reactions: Any) -> Optional[Dict[str, int]]:
    """Parse reactions JSON from database (json_object_agg returns string, not dict)."""
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


def _calculate_labels(activity_type: str, reactions: Optional[Dict[str, int]]) -> List[str]:
    """Calculate labels for activity items based on criteria."""
    labels = []
    
    if activity_type == "note" and reactions:
        # Calculate total reaction count
        total_reactions = sum(reactions.values())
        
        # Sözü Dinlenir: Average reactions >= 5
        # For now, we use total reactions >= 5 as a simple threshold
        # In the future, we could calculate average per reaction type
        if total_reactions >= 5:
            labels.append("sözü_dinlenir")
        
        # Yerinde Tespit: Future implementation requires "nuttig" markers in database
        # For now, we skip this label
    
    return labels


def _normalize_user_name(user_name: Optional[str], user_id: Optional[str]) -> Optional[str]:
    """
    Normalize user_name: if it equals user_id (UUID), treat it as None.
    This fixes cases where display_name was incorrectly set to user_id.
    """
    if not user_name or not user_id:
        return user_name
    
    # If display_name equals user_id, treat it as if no username was set
    if user_name.strip() == str(user_id):
        return None
    
    return user_name


@router.get("", response_model=List[ActivityItem])
async def get_own_activity(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    activity_type: Optional[str] = Query(None, description="Filter by activity type (check_in, reaction, note, poll_response, favorite)"),
    client_id: Optional[str] = Depends(get_client_id),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Get activity feed - shows all activity (including bots) with user's like/bookmark status."""
    require_feature("check_ins_enabled")  # Or create separate flag
    
    user_id = user.user_id if user else None
    
    # Build WHERE clause - show ALL activity (not filtered by user_id/client_id)
    # This allows bots and other users' activity to appear in the feed
    conditions = []
    params = []
    param_num = 1
    
    # Optional activity_type filter
    if activity_type:
        # Validate activity_type
        valid_types = ["check_in", "reaction", "note", "poll_response", "favorite", "bulletin_post", "event"]
        if activity_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid activity_type. Must be one of: {', '.join(valid_types)}"
            )
        conditions.append(f"ast.activity_type = ${param_num}")
        params.append(activity_type)
        param_num += 1
    
    # If no conditions, show all activity
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Build LIKE join condition for current user/client
    # This still tracks whether the current user has liked/bookmarked/reacted
    like_join_condition = "al.activity_id = ast.id AND "
    bookmark_join_condition = "ab.activity_id = ast.id AND "
    if user_id:
        # Check by user_id if authenticated
        like_join_condition += f"(al.user_id = '{user_id}')"
        bookmark_join_condition += f"(ab.user_id = '{user_id}')"
        user_reaction_condition = f"ar2.user_id = '{user_id}'"
    elif client_id:
        # Fallback to client_id if not authenticated
        like_join_condition += f"(al.client_id = '{client_id}')"
        bookmark_join_condition += f"(ab.client_id = '{client_id}')"
        user_reaction_condition = f"ar2.client_id = '{client_id}'"
    else:
        # No user or client_id - no likes/bookmarks/reactions
        like_join_condition += "al.client_id IS NULL"
        bookmark_join_condition += "ab.client_id IS NULL"
        user_reaction_condition = "ar2.client_id IS NULL"
    
    sql = f"""
        SELECT 
            ast.id,
            ast.activity_type,
            ast.location_id,
            l.name as location_name,
            ast.payload,
            ast.created_at,
            ast.media_url,
            up.id as user_id,
            up.display_name as user_name,
            up.avatar_url as user_avatar_url,
            ur.primary_role as user_primary_role,
            ur.secondary_role as user_secondary_role,
            COALESCE(like_counts.like_count, 0) as like_count,
            CASE WHEN al.id IS NOT NULL THEN true ELSE false END as is_liked,
            CASE WHEN ab.id IS NOT NULL THEN true ELSE false END as is_bookmarked,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                    AND pl.promotion_type IN ('feed', 'both')
                    AND pl.starts_at <= now()
                    AND pl.ends_at > now()
                THEN true 
                ELSE false 
            END as is_promoted,
            COALESCE(
                (
                    SELECT json_object_agg(reaction_type, count)
                    FROM (
                        SELECT reaction_type, COUNT(*)::int as count
                        FROM activity_reactions
                        WHERE activity_id = ast.id
                        GROUP BY reaction_type
                    ) reaction_counts
                ),
                '{{}}'::json
            ) as reactions,
            (
                SELECT reaction_type
                FROM activity_reactions ar2
                WHERE ar2.activity_id = ast.id AND ({user_reaction_condition})
                LIMIT 1
            ) as user_reaction
        FROM activity_stream ast
        LEFT JOIN locations l ON ast.location_id = l.id
        LEFT JOIN promoted_locations pl ON pl.location_id = ast.location_id
        LEFT JOIN user_profiles up ON ast.actor_id = up.id AND ast.actor_type = 'user'
        LEFT JOIN user_roles ur ON up.id = ur.user_id
        LEFT JOIN (
            SELECT activity_id, COUNT(*) as like_count
            FROM activity_likes
            GROUP BY activity_id
        ) like_counts ON like_counts.activity_id = ast.id
        LEFT JOIN activity_likes al ON {like_join_condition}
        LEFT JOIN activity_bookmarks ab ON {bookmark_join_condition}
        WHERE {where_clause}
        ORDER BY is_promoted DESC, ast.created_at DESC
        LIMIT ${param_num} OFFSET ${param_num + 1}
    """
    
    params.extend([limit, offset])
    
    rows = await fetch(sql, *params)
    
    result = []
    for row in rows:
        parsed_reactions = _parse_reactions(row.get("reactions"))
        labels = _calculate_labels(row["activity_type"], parsed_reactions)
        
        result.append(
            ActivityItem(
                id=row["id"],
                activity_type=row["activity_type"],
                location_id=row.get("location_id"),
                location_name=row.get("location_name"),
                payload=_parse_payload(row.get("payload")),
                created_at=row["created_at"],
                is_promoted=row.get("is_promoted", False),
                media_url=row.get("media_url"),
                user=ActivityUser(
                    id=str(row["user_id"]),
                    name=_normalize_user_name(row.get("user_name"), str(row["user_id"]) if row.get("user_id") else None),
                    avatar_url=row.get("user_avatar_url"),
                    primary_role=row.get("user_primary_role"),
                    secondary_role=row.get("user_secondary_role"),
                ) if row.get("user_id") else None,
                like_count=row.get("like_count", 0) or 0,
                is_liked=row.get("is_liked", False) or False,
                is_bookmarked=row.get("is_bookmarked", False) or False,
                reactions=parsed_reactions,
                user_reaction=row.get("user_reaction"),
                labels=labels if labels else None,
            )
        )
    
    return result


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
    client_id: Optional[str] = Depends(get_client_id),
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
    
    # Build LIKE join condition for current user/client
    like_join_condition = "al.activity_id = ast.id AND "
    bookmark_join_condition = "ab.activity_id = ast.id AND "
    if client_id:
        like_join_condition += f"(al.client_id = '{client_id}')"
        bookmark_join_condition += f"(ab.client_id = '{client_id}')"
        user_reaction_condition = f"ar2.client_id = '{client_id}'"
    else:
        like_join_condition += "al.client_id IS NULL"
        bookmark_join_condition += "ab.client_id IS NULL"
        user_reaction_condition = "ar2.client_id IS NULL"
    
    sql = f"""
        SELECT 
            ast.id,
            ast.activity_type,
            ast.location_id,
            l.name as location_name,
            ast.payload,
            ast.created_at,
            ast.media_url,
            up.id as user_id,
            up.display_name as user_name,
            up.avatar_url as user_avatar_url,
            ur.primary_role as user_primary_role,
            ur.secondary_role as user_secondary_role,
            COALESCE(like_counts.like_count, 0) as like_count,
            CASE WHEN al.id IS NOT NULL THEN true ELSE false END as is_liked,
            CASE WHEN ab.id IS NOT NULL THEN true ELSE false END as is_bookmarked,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                    AND pl.promotion_type IN ('feed', 'both')
                    AND pl.starts_at <= now()
                    AND pl.ends_at > now()
                THEN true 
                ELSE false 
            END as is_promoted,
            COALESCE(
                (
                    SELECT json_object_agg(reaction_type, count)
                    FROM (
                        SELECT reaction_type, COUNT(*)::int as count
                        FROM activity_reactions
                        WHERE activity_id = ast.id
                        GROUP BY reaction_type
                    ) reaction_counts
                ),
                '{{}}'::json
            ) as reactions,
            (
                SELECT reaction_type
                FROM activity_reactions ar2
                WHERE ar2.activity_id = ast.id AND ({user_reaction_condition})
                LIMIT 1
            ) as user_reaction
        FROM activity_stream ast
        INNER JOIN locations l ON ast.location_id = l.id
        LEFT JOIN promoted_locations pl ON pl.location_id = ast.location_id
        LEFT JOIN user_profiles up ON ast.actor_id = up.id AND ast.actor_type = 'user'
        LEFT JOIN user_roles ur ON up.id = ur.user_id
        LEFT JOIN (
            SELECT activity_id, COUNT(*) as like_count
            FROM activity_likes
            GROUP BY activity_id
        ) like_counts ON like_counts.activity_id = ast.id
        LEFT JOIN activity_likes al ON {like_join_condition}
        LEFT JOIN activity_bookmarks ab ON {bookmark_join_condition}
        WHERE {where_clause}
        ORDER BY is_promoted DESC, ast.created_at DESC
        LIMIT ${param_num}
    """
    params.append(limit)
    
    rows = await fetch(sql, *params)
    
    result = []
    for row in rows:
        parsed_reactions = _parse_reactions(row.get("reactions"))
        labels = _calculate_labels(row["activity_type"], parsed_reactions)
        
        result.append(
            ActivityItem(
                id=row["id"],
                activity_type=row["activity_type"],
                location_id=row.get("location_id"),
                location_name=row.get("location_name"),
                payload=_parse_payload(row.get("payload")),
                created_at=row["created_at"],
                is_promoted=row.get("is_promoted", False),
                media_url=row.get("media_url"),
                user=ActivityUser(
                    id=str(row["user_id"]),
                    name=_normalize_user_name(row.get("user_name"), str(row["user_id"]) if row.get("user_id") else None),
                    avatar_url=row.get("user_avatar_url"),
                    primary_role=row.get("user_primary_role"),
                    secondary_role=row.get("user_secondary_role"),
                ) if row.get("user_id") else None,
                like_count=row.get("like_count", 0) or 0,
                is_liked=row.get("is_liked", False) or False,
                is_bookmarked=row.get("is_bookmarked", False) or False,
                reactions=parsed_reactions,
                user_reaction=row.get("user_reaction"),
                labels=labels if labels else None,
            )
        )
    
    return result


@router.get("/locations/{location_id}", response_model=List[ActivityItem])
async def get_location_activity(
    location_id: int = Path(..., description="Location ID"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    client_id: Optional[str] = Depends(get_client_id),
):
    """Get activity for a specific location."""
    require_feature("check_ins_enabled")
    
    # Build LIKE join condition for current user/client
    like_join_condition = "al.activity_id = ast.id AND "
    bookmark_join_condition = "ab.activity_id = ast.id AND "
    if client_id:
        like_join_condition += f"(al.client_id = '{client_id}')"
        bookmark_join_condition += f"(ab.client_id = '{client_id}')"
        user_reaction_condition = f"ar2.client_id = '{client_id}'"
    else:
        like_join_condition += "al.client_id IS NULL"
        bookmark_join_condition += "ab.client_id IS NULL"
        user_reaction_condition = "ar2.client_id IS NULL"
    
    sql = f"""
        SELECT 
            ast.id,
            ast.activity_type,
            ast.location_id,
            l.name as location_name,
            ast.payload,
            ast.created_at,
            ast.media_url,
            up.id as user_id,
            up.display_name as user_name,
            up.avatar_url as user_avatar_url,
            ur.primary_role as user_primary_role,
            ur.secondary_role as user_secondary_role,
            COALESCE(like_counts.like_count, 0) as like_count,
            CASE WHEN al.id IS NOT NULL THEN true ELSE false END as is_liked,
            CASE WHEN ab.id IS NOT NULL THEN true ELSE false END as is_bookmarked,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                    AND pl.promotion_type IN ('feed', 'both')
                    AND pl.starts_at <= now()
                    AND pl.ends_at > now()
                THEN true 
                ELSE false 
            END as is_promoted,
            COALESCE(
                (
                    SELECT json_object_agg(reaction_type, count)
                    FROM (
                        SELECT reaction_type, COUNT(*)::int as count
                        FROM activity_reactions
                        WHERE activity_id = ast.id
                        GROUP BY reaction_type
                    ) reaction_counts
                ),
                '{{}}'::json
            ) as reactions,
            (
                SELECT reaction_type
                FROM activity_reactions ar2
                WHERE ar2.activity_id = ast.id AND ({user_reaction_condition})
                LIMIT 1
            ) as user_reaction
        FROM activity_stream ast
        LEFT JOIN locations l ON ast.location_id = l.id
        LEFT JOIN promoted_locations pl ON pl.location_id = ast.location_id
        LEFT JOIN user_profiles up ON ast.actor_id = up.id AND ast.actor_type = 'user'
        LEFT JOIN user_roles ur ON up.id = ur.user_id
        LEFT JOIN (
            SELECT activity_id, COUNT(*) as like_count
            FROM activity_likes
            GROUP BY activity_id
        ) like_counts ON like_counts.activity_id = ast.id
        LEFT JOIN activity_likes al ON {like_join_condition}
        LEFT JOIN activity_bookmarks ab ON {bookmark_join_condition}
        WHERE ast.location_id = $1
        ORDER BY is_promoted DESC, ast.created_at DESC
        LIMIT $2 OFFSET $3
    """
    
    rows = await fetch(sql, location_id, limit, offset)
    
    result = []
    for row in rows:
        parsed_reactions = _parse_reactions(row.get("reactions"))
        labels = _calculate_labels(row["activity_type"], parsed_reactions)
        
        result.append(
            ActivityItem(
                id=row["id"],
                activity_type=row["activity_type"],
                location_id=row.get("location_id"),
                location_name=row.get("location_name"),
                payload=_parse_payload(row.get("payload")),
                created_at=row["created_at"],
                is_promoted=row.get("is_promoted", False),
                media_url=row.get("media_url"),
                user=ActivityUser(
                    id=str(row["user_id"]),
                    name=_normalize_user_name(row.get("user_name"), str(row["user_id"]) if row.get("user_id") else None),
                    avatar_url=row.get("user_avatar_url"),
                    primary_role=row.get("user_primary_role"),
                    secondary_role=row.get("user_secondary_role"),
                ) if row.get("user_id") else None,
                like_count=row.get("like_count", 0) or 0,
                is_liked=row.get("is_liked", False) or False,
                is_bookmarked=row.get("is_bookmarked", False) or False,
                reactions=parsed_reactions,
                user_reaction=row.get("user_reaction"),
                labels=labels if labels else None,
            )
        )
    
    return result


@router.post("/{activity_id}/bookmark", response_model=dict)
async def toggle_activity_bookmark(
    activity_id: int = Path(..., description="Activity ID"),
    client_id: Optional[str] = Depends(get_client_id),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Toggle bookmark on activity item."""
    require_feature("check_ins_enabled")
    
    user_id = user.user_id if user else None
    
    if not user_id and not client_id:
        raise HTTPException(status_code=400, detail="Either authentication or client_id required")
    
    # Check if activity exists
    check_sql = "SELECT id FROM activity_stream WHERE id = $1"
    check_rows = await fetch(check_sql, activity_id)
    if not check_rows:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Check if already bookmarked (similar to likes logic)
    if user_id:
        check_bookmark_sql = "SELECT id FROM activity_bookmarks WHERE activity_id = $1 AND user_id = $2"
        existing = await fetch(check_bookmark_sql, activity_id, user_id)
    else:
        check_bookmark_sql = "SELECT id FROM activity_bookmarks WHERE activity_id = $1 AND client_id = $2::uuid"
        existing = await fetch(check_bookmark_sql, activity_id, client_id)
    
    if existing:
        # Unbookmark
        if user_id:
            delete_sql = "DELETE FROM activity_bookmarks WHERE activity_id = $1 AND user_id = $2"
            await execute(delete_sql, activity_id, user_id)
        else:
            delete_sql = "DELETE FROM activity_bookmarks WHERE activity_id = $1 AND client_id = $2::uuid"
            await execute(delete_sql, activity_id, client_id)
        return {"bookmarked": False}
    else:
        # Bookmark
        if user_id:
            insert_sql = "INSERT INTO activity_bookmarks (activity_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING"
            await execute(insert_sql, activity_id, user_id)
        else:
            insert_sql = "INSERT INTO activity_bookmarks (activity_id, client_id) VALUES ($1, $2::uuid) ON CONFLICT DO NOTHING"
            await execute(insert_sql, activity_id, client_id)
        return {"bookmarked": True}


class ReactionToggleRequest(BaseModel):
    reaction_type: str  # Emoji string (e.g., "🔥", "❤️", "👍", etc.)


@router.post("/{activity_id}/reactions", response_model=dict)
async def toggle_activity_reaction(
    activity_id: int = Path(..., description="Activity ID"),
    request: ReactionToggleRequest = ...,
    client_id: Optional[str] = Depends(get_client_id),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Toggle emoji reaction on activity item."""
    require_feature("check_ins_enabled")
    
    user_id = user.user_id if user else None
    
    if not user_id and not client_id:
        raise HTTPException(status_code=400, detail="Either authentication or client_id required")
    
    # Basic validation: ensure reaction_type is a non-empty string
    if not request.reaction_type or not isinstance(request.reaction_type, str) or len(request.reaction_type.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="reaction_type must be a non-empty string (emoji)"
        )
    
    # Limit emoji length to prevent abuse (reasonable limit for emoji sequences)
    if len(request.reaction_type) > 10:
        raise HTTPException(
            status_code=400,
            detail="reaction_type too long (max 10 characters)"
        )
    
    # Check if activity exists
    check_sql = "SELECT id FROM activity_stream WHERE id = $1"
    check_rows = await fetch(check_sql, activity_id)
    if not check_rows:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Check if already reacted with this type
    if user_id:
        check_reaction_sql = """
            SELECT id FROM activity_reactions 
            WHERE activity_id = $1 AND user_id = $2 AND reaction_type = $3
        """
        existing = await fetch(check_reaction_sql, activity_id, user_id, request.reaction_type)
    else:
        check_reaction_sql = """
            SELECT id FROM activity_reactions 
            WHERE activity_id = $1 AND client_id = $2 AND reaction_type = $3
        """
        existing = await fetch(check_reaction_sql, activity_id, client_id, request.reaction_type)
    
    if existing:
        # Remove reaction
        if user_id:
            delete_sql = """
                DELETE FROM activity_reactions 
                WHERE activity_id = $1 AND user_id = $2 AND reaction_type = $3
            """
            await execute(delete_sql, activity_id, user_id, request.reaction_type)
        else:
            delete_sql = """
                DELETE FROM activity_reactions 
                WHERE activity_id = $1 AND client_id = $2 AND reaction_type = $3
            """
            await execute(delete_sql, activity_id, client_id, request.reaction_type)
        is_active = False
    else:
        # Add reaction
        if user_id:
            insert_sql = """
                INSERT INTO activity_reactions (activity_id, user_id, reaction_type) 
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """
            await execute(insert_sql, activity_id, user_id, request.reaction_type)
        else:
            insert_sql = """
                INSERT INTO activity_reactions (activity_id, client_id, reaction_type) 
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """
            await execute(insert_sql, activity_id, client_id, request.reaction_type)
        is_active = True
    
    # Get updated count
    count_sql = """
        SELECT COUNT(*) as count 
        FROM activity_reactions 
        WHERE activity_id = $1 AND reaction_type = $2
    """
    count_rows = await fetch(count_sql, activity_id, request.reaction_type)
    count = count_rows[0]["count"] if count_rows else 0
    
    return {
        "reaction_type": request.reaction_type,
        "is_active": is_active,
        "count": count
    }


@router.get("/{activity_id}/reactions", response_model=dict)
async def get_activity_reactions(
    activity_id: int = Path(..., description="Activity ID"),
):
    """Get reaction counts for an activity item."""
    require_feature("check_ins_enabled")
    
    # Check if activity exists
    check_sql = "SELECT id FROM activity_stream WHERE id = $1"
    check_rows = await fetch(check_sql, activity_id)
    if not check_rows:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Get reaction counts grouped by type
    counts_sql = """
        SELECT reaction_type, COUNT(*) as count
        FROM activity_reactions
        WHERE activity_id = $1
        GROUP BY reaction_type
        ORDER BY count DESC, reaction_type ASC
    """
    count_rows = await fetch(counts_sql, activity_id)
    
    # Build reactions dict dynamically from database results
    reactions: Dict[str, int] = {}
    for row in count_rows:
        reaction_type = row["reaction_type"]
        reactions[reaction_type] = row["count"]
    
    return {"reactions": reactions}



