# Backend/services/streak_service.py
"""
Streak calculation and management service.

Tracks daily activity streaks for users.
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime, timedelta, timezone

from services.db_service import fetch, execute
from app.core.logging import get_logger

logger = get_logger()

# Streak reset threshold: if user is inactive for more than this many hours, streak resets
STREAK_RESET_HOURS = 48


async def update_streak(user_id: str) -> None:
    """
    Update user streak based on last activity.
    
    Checks the last activity time and updates current_streak_days and longest_streak_days.
    Called after each activity (check-in, note, etc.).
    """
    try:
        # Get current streak info
        get_sql = """
            SELECT current_streak_days, longest_streak_days, last_active_at
            FROM user_streaks
            WHERE user_id = $1::uuid
        """
        rows = await fetch(get_sql, user_id)
        
        if not rows:
            # Create initial streak record
            create_sql = """
                INSERT INTO user_streaks (user_id, current_streak_days, longest_streak_days, last_active_at, updated_at)
                VALUES ($1::uuid, 1, 1, now(), now())
                ON CONFLICT (user_id) DO NOTHING
            """
            await execute(create_sql, user_id)
            return
        
        row = rows[0]
        current_streak = row.get("current_streak_days", 0) or 0
        longest_streak = row.get("longest_streak_days", 0) or 0
        last_active = row.get("last_active_at")
        
        now = datetime.now(timezone.utc)
        
        if last_active:
            # Ensure last_active is a datetime with timezone
            if isinstance(last_active, datetime):
                if last_active.tzinfo is None:
                    last_active = last_active.replace(tzinfo=timezone.utc)
            else:
                # If not a datetime, treat as new activity
                last_active = None
        
        if not last_active:
            # New streak: start at 1 day
            new_streak = 1
        else:
            # Calculate hours since last activity
            time_since = now - last_active
            hours_since = time_since.total_seconds() / 3600
            
            if hours_since < STREAK_RESET_HOURS:
                # Activity within streak window
                # Check if activity is on a new day
                if last_active.date() < now.date():
                    # New day: increment streak
                    new_streak = current_streak + 1
                elif hours_since < 24:
                    # Same day: keep current streak
                    new_streak = current_streak
                else:
                    # More than 24h but less than 48h: might be next day
                    # Check if we're on a different calendar day
                    if last_active.date() < now.date():
                        new_streak = current_streak + 1
                    else:
                        new_streak = current_streak
            else:
                # Streak broken: reset to 1
                new_streak = 1
        
        # Update longest streak if needed
        new_longest = max(longest_streak, new_streak)
        
        # Update streak record
        update_sql = """
            UPDATE user_streaks
            SET current_streak_days = $1,
                longest_streak_days = $2,
                last_active_at = now(),
                updated_at = now()
            WHERE user_id = $3::uuid
        """
        await execute(update_sql, new_streak, new_longest, user_id)
        
        logger.debug(
            "streak_updated",
            user_id=user_id,
            current_streak=new_streak,
            longest_streak=new_longest,
        )
        
    except Exception as e:
        logger.error(
            "streak_update_error",
            user_id=user_id,
            error=str(e),
        )
        # Don't fail the request if streak update fails























