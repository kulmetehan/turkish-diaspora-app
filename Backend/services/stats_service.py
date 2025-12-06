# Backend/services/stats_service.py
"""
City & Category Statistics Service.

Aggregates activity stream data to provide statistics per city and category.
"""

from __future__ import annotations

from typing import Dict, Optional
from datetime import datetime, timedelta, timezone

from services.db_service import fetch
from app.core.logging import get_logger

logger = get_logger()


async def get_city_stats(city_key: str, window_days: int = 7) -> Dict:
    """
    Get aggregated statistics for a city.
    
    Returns:
        {
            "city_key": str,
            "check_ins_count": int,
            "reactions_count": int,
            "notes_count": int,
            "favorites_count": int,
            "poll_responses_count": int,
            "trending_locations_count": int,
            "unique_locations_count": int,
            "total_activity": int,
            "window_days": int,
        }
    """
    window_start = datetime.now(timezone.utc) - timedelta(days=window_days)
    
    # Aggregate from activity_stream
    sql = """
        SELECT 
            COUNT(*) FILTER (WHERE activity_type = 'check_in') as check_ins_count,
            COUNT(*) FILTER (WHERE activity_type = 'reaction') as reactions_count,
            COUNT(*) FILTER (WHERE activity_type = 'note') as notes_count,
            COUNT(*) FILTER (WHERE activity_type = 'favorite') as favorites_count,
            COUNT(*) FILTER (WHERE activity_type = 'poll_response') as poll_responses_count,
            COUNT(DISTINCT location_id) FILTER (WHERE location_id IS NOT NULL) as unique_locations_count
        FROM activity_stream
        WHERE city_key = $1
          AND created_at >= $2
    """
    
    rows = await fetch(sql, city_key, window_start)
    
    if not rows:
        return {
            "city_key": city_key,
            "check_ins_count": 0,
            "reactions_count": 0,
            "notes_count": 0,
            "favorites_count": 0,
            "poll_responses_count": 0,
            "trending_locations_count": 0,
            "unique_locations_count": 0,
            "total_activity": 0,
            "window_days": window_days,
        }
    
    row = rows[0]
    
    # Get trending locations count for this city
    trending_sql = """
        SELECT COUNT(DISTINCT location_id) as count
        FROM trending_locations
        WHERE city_key = $1
    """
    trending_rows = await fetch(trending_sql, city_key)
    trending_count = trending_rows[0].get("count", 0) or 0 if trending_rows else 0
    
    check_ins = row.get("check_ins_count", 0) or 0
    reactions = row.get("reactions_count", 0) or 0
    notes = row.get("notes_count", 0) or 0
    favorites = row.get("favorites_count", 0) or 0
    poll_responses = row.get("poll_responses_count", 0) or 0
    unique_locations = row.get("unique_locations_count", 0) or 0
    
    total_activity = check_ins + reactions + notes + favorites + poll_responses
    
    return {
        "city_key": city_key,
        "check_ins_count": check_ins,
        "reactions_count": reactions,
        "notes_count": notes,
        "favorites_count": favorites,
        "poll_responses_count": poll_responses,
        "trending_locations_count": trending_count,
        "unique_locations_count": unique_locations,
        "total_activity": total_activity,
        "window_days": window_days,
    }


async def get_category_stats(category_key: str, city_key: Optional[str] = None, window_days: int = 7) -> Dict:
    """
    Get aggregated statistics for a category (optionally filtered by city).
    
    Returns:
        {
            "category_key": str,
            "city_key": Optional[str],
            "check_ins_count": int,
            "reactions_count": int,
            "notes_count": int,
            "favorites_count": int,
            "poll_responses_count": int,
            "unique_locations_count": int,
            "total_activity": int,
            "window_days": int,
        }
    """
    window_start = datetime.now(timezone.utc) - timedelta(days=window_days)
    
    conditions = ["category_key = $1", "created_at >= $2"]
    params = [category_key, window_start]
    param_num = 3
    
    if city_key:
        conditions.append(f"city_key = ${param_num}")
        params.append(city_key)
        param_num += 1
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            COUNT(*) FILTER (WHERE activity_type = 'check_in') as check_ins_count,
            COUNT(*) FILTER (WHERE activity_type = 'reaction') as reactions_count,
            COUNT(*) FILTER (WHERE activity_type = 'note') as notes_count,
            COUNT(*) FILTER (WHERE activity_type = 'favorite') as favorites_count,
            COUNT(*) FILTER (WHERE activity_type = 'poll_response') as poll_responses_count,
            COUNT(DISTINCT location_id) FILTER (WHERE location_id IS NOT NULL) as unique_locations_count
        FROM activity_stream
        WHERE {where_clause}
    """
    
    rows = await fetch(sql, *params)
    
    if not rows:
        return {
            "category_key": category_key,
            "city_key": city_key,
            "check_ins_count": 0,
            "reactions_count": 0,
            "notes_count": 0,
            "favorites_count": 0,
            "poll_responses_count": 0,
            "unique_locations_count": 0,
            "total_activity": 0,
            "window_days": window_days,
        }
    
    row = rows[0]
    
    check_ins = row.get("check_ins_count", 0) or 0
    reactions = row.get("reactions_count", 0) or 0
    notes = row.get("notes_count", 0) or 0
    favorites = row.get("favorites_count", 0) or 0
    poll_responses = row.get("poll_responses_count", 0) or 0
    unique_locations = row.get("unique_locations_count", 0) or 0
    
    total_activity = check_ins + reactions + notes + favorites + poll_responses
    
    return {
        "category_key": category_key,
        "city_key": city_key,
        "check_ins_count": check_ins,
        "reactions_count": reactions,
        "notes_count": notes,
        "favorites_count": favorites,
        "poll_responses_count": poll_responses,
        "unique_locations_count": unique_locations,
        "total_activity": total_activity,
        "window_days": window_days,
    }



