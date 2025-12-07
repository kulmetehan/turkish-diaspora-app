# Backend/services/badge_service.py
"""
Badge awarding service.

Checks badge conditions and awards badges to users.
"""

from __future__ import annotations

from typing import Optional, List
from datetime import datetime, timezone

from services.db_service import fetch, execute
from app.core.logging import get_logger

logger = get_logger()

# Badge types (must match enum in database)
BADGE_TYPES = {
    "explorer_city": "10 unique locations in city",
    "early_adopter": "First 1000 users",
    "poll_master": "100 polls answered",
    "super_supporter": "50 notes written",
    "local_guide": "10 notes with positive feedback",
    "streak_7": "7 day streak",
    "streak_30": "30 day streak",
    "check_in_100": "100 check-ins total",
}


async def check_and_award_badges(user_id: str) -> List[str]:
    """
    Check all badge conditions and award any new badges.
    
    Returns list of newly awarded badge types.
    """
    awarded = []
    
    try:
        # Check each badge type
        # Note: Some badges require complex queries, so we'll implement the key ones
        
        # 1. Streak badges (streak_7, streak_30)
        streak_badges = await _check_streak_badges(user_id)
        awarded.extend(streak_badges)
        
        # 2. Activity count badges (check_in_100, super_supporter, poll_master)
        activity_badges = await _check_activity_badges(user_id)
        awarded.extend(activity_badges)
        
        # 3. Explorer badge (explorer_city) - requires checking unique locations per city
        explorer_badges = await _check_explorer_badges(user_id)
        awarded.extend(explorer_badges)
        
        # Note: early_adopter badge should be awarded via a separate process/worker
        # that checks user creation order
        
    except Exception as e:
        logger.error(
            "badge_check_error",
            user_id=user_id,
            error=str(e),
        )
    
    return awarded


async def _check_streak_badges(user_id: str) -> List[str]:
    """Check and award streak-based badges."""
    awarded = []
    
    sql = """
        SELECT current_streak_days
        FROM user_streaks
        WHERE user_id = $1::uuid
    """
    rows = await fetch(sql, user_id)
    
    if not rows:
        return awarded
    
    current_streak = rows[0].get("current_streak_days", 0) or 0
    
    # Check streak_7
    if current_streak >= 7:
        if await _award_badge(user_id, "streak_7", None):
            awarded.append("streak_7")
    
    # Check streak_30
    if current_streak >= 30:
        if await _award_badge(user_id, "streak_30", None):
            awarded.append("streak_30")
    
    return awarded


async def _check_activity_badges(user_id: str) -> List[str]:
    """Check and award activity count-based badges."""
    awarded = []
    
    # Check check-in count
    check_ins_sql = """
        SELECT COUNT(*) as count
        FROM check_ins
        WHERE user_id = $1::uuid
    """
    check_ins_rows = await fetch(check_ins_sql, user_id)
    check_in_count = check_ins_rows[0].get("count", 0) or 0 if check_ins_rows else 0
    
    if check_in_count >= 100:
        if await _award_badge(user_id, "check_in_100", None):
            awarded.append("check_in_100")
    
    # Check notes count
    notes_sql = """
        SELECT COUNT(*) as count
        FROM location_notes
        WHERE user_id = $1::uuid
    """
    notes_rows = await fetch(notes_sql, user_id)
    notes_count = notes_rows[0].get("count", 0) or 0 if notes_rows else 0
    
    if notes_count >= 50:
        if await _award_badge(user_id, "super_supporter", None):
            awarded.append("super_supporter")
    
    # Check poll responses count
    polls_sql = """
        SELECT COUNT(DISTINCT poll_id) as count
        FROM poll_responses
        WHERE user_id = $1::uuid
    """
    polls_rows = await fetch(polls_sql, user_id)
    polls_count = polls_rows[0].get("count", 0) or 0 if polls_rows else 0
    
    if polls_count >= 100:
        if await _award_badge(user_id, "poll_master", None):
            awarded.append("poll_master")
    
    return awarded


async def _check_explorer_badges(user_id: str) -> List[str]:
    """Check and award explorer badges (10 unique locations per city)."""
    awarded = []
    
    # Get unique locations per city from check-ins
    sql = """
        SELECT 
            l.city_key,
            COUNT(DISTINCT ci.location_id) as unique_locations
        FROM check_ins ci
        JOIN locations l ON ci.location_id = l.id
        WHERE ci.user_id = $1::uuid
          AND l.city_key IS NOT NULL
        GROUP BY l.city_key
        HAVING COUNT(DISTINCT ci.location_id) >= 10
    """
    
    rows = await fetch(sql, user_id)
    
    for row in rows:
        city_key = row.get("city_key")
        if city_key:
            # Check if badge already awarded
            if await _award_badge(user_id, "explorer_city", city_key):
                awarded.append(f"explorer_city:{city_key}")
    
    return awarded


async def _award_badge(user_id: str, badge_type: str, city_key: Optional[str]) -> bool:
    """
    Award a badge to a user if they don't already have it.
    
    Returns True if badge was awarded, False if already exists.
    """
    try:
        # Try to insert badge (will fail if already exists due to unique constraint)
        sql = """
            INSERT INTO user_badges (user_id, badge_type, city_key, earned_at)
            VALUES ($1::uuid, $2::badge_type, $3, now())
            ON CONFLICT (user_id, badge_type, city_key) DO NOTHING
            RETURNING id
        """
        
        rows = await fetch(sql, user_id, badge_type, city_key)
        
        if rows:
            logger.info(
                "badge_awarded",
                user_id=user_id,
                badge_type=badge_type,
                city_key=city_key,
            )
            return True
        
        return False
        
    except Exception as e:
        logger.error(
            "badge_award_error",
            user_id=user_id,
            badge_type=badge_type,
            error=str(e),
        )
        return False





