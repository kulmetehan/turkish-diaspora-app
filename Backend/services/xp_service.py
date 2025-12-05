# Backend/services/xp_service.py
"""
XP (Experience Points) awarding service.

Handles XP awarding for various activities with daily caps and logging.
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime, timedelta, timezone

from app.core.xp_config import get_xp_amount, DAILY_XP_CAP
from services.db_service import fetch, execute
from app.core.logging import get_logger

logger = get_logger()


async def award_xp(
    user_id: Optional[str],
    client_id: Optional[str],
    source: str,
    source_id: Optional[int] = None,
    amount: Optional[int] = None,
) -> bool:
    """
    Award XP to a user for an activity.
    
    Args:
        user_id: User UUID (if authenticated)
        client_id: Client ID UUID (if anonymous)
        source: Action source ('check_in', 'reaction', 'note', 'poll_response', 'favorite')
        source_id: Optional ID of the source record (check_ins.id, location_notes.id, etc.)
        amount: Optional custom XP amount (uses config if None)
        
    Returns:
        True if XP was awarded, False if daily cap was reached or user_id/client_id missing
    """
    if not user_id and not client_id:
        logger.warning("xp_award_skipped_no_identity", source=source)
        return False
    
    # Get XP amount from config if not provided
    if amount is None:
        amount = get_xp_amount(source)
    
    if amount <= 0:
        # No XP for this action, skip silently
        return False
    
    # Only award XP to authenticated users for now
    # Anonymous users (client_id only) don't get XP until they sign up
    if not user_id:
        logger.debug("xp_award_skipped_anonymous", source=source, client_id=client_id)
        return False
    
    try:
        # Check daily XP cap and reset if needed
        await _ensure_daily_reset(user_id)
        
        # Check current daily XP
        check_sql = """
            SELECT daily_xp, daily_xp_cap
            FROM user_streaks
            WHERE user_id = $1
        """
        rows = await fetch(check_sql, user_id)
        
        if not rows:
            # Create user_streaks record if it doesn't exist
            create_sql = """
                INSERT INTO user_streaks (user_id, total_xp, daily_xp, daily_xp_cap, updated_at)
                VALUES ($1, 0, 0, $2, now())
                ON CONFLICT (user_id) DO NOTHING
            """
            await execute(create_sql, user_id, DAILY_XP_CAP)
            
            # Re-fetch after creation
            rows = await fetch(check_sql, user_id)
        
        if rows:
            current_daily_xp = rows[0].get("daily_xp", 0) or 0
            daily_cap = rows[0].get("daily_xp_cap", DAILY_XP_CAP) or DAILY_XP_CAP
            
            # Check if awarding this XP would exceed daily cap
            if current_daily_xp + amount > daily_cap:
                # Award only up to the cap
                actual_amount = max(0, daily_cap - current_daily_xp)
                if actual_amount <= 0:
                    logger.debug(
                        "xp_award_skipped_daily_cap",
                        user_id=user_id,
                        source=source,
                        current_daily_xp=current_daily_xp,
                        daily_cap=daily_cap,
                    )
                    return False
                amount = actual_amount
        
        # Award XP: update user_streaks
        update_sql = """
            UPDATE user_streaks
            SET total_xp = total_xp + $1,
                daily_xp = daily_xp + $1,
                updated_at = now()
            WHERE user_id = $2
            RETURNING total_xp, daily_xp
        """
        result_rows = await fetch(update_sql, amount, user_id)
        
        if not result_rows:
            logger.warning("xp_award_failed_update", user_id=user_id, source=source)
            return False
        
        # Log XP award
        log_sql = """
            INSERT INTO user_xp_log (user_id, client_id, xp_amount, source, source_id, created_at)
            VALUES ($1, $2, $3, $4, $5, now())
        """
        await execute(log_sql, user_id, client_id, amount, source, source_id)
        
        # Update streak after XP award (async, don't wait)
        try:
            from services.streak_service import update_streak
            await update_streak(user_id)
        except Exception as e:
            logger.warning("streak_update_failed_after_xp", user_id=user_id, error=str(e))
        
        # Check and award badges (async, don't wait)
        try:
            from services.badge_service import check_and_award_badges
            await check_and_award_badges(user_id)
        except Exception as e:
            logger.warning("badge_check_failed_after_xp", user_id=user_id, error=str(e))
        
        logger.info(
            "xp_awarded",
            user_id=user_id,
            source=source,
            amount=amount,
            source_id=source_id,
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "xp_award_error",
            user_id=user_id,
            source=source,
            error=str(e),
        )
        # Don't fail the request if XP awarding fails
        return False


async def _ensure_daily_reset(user_id: str) -> None:
    """
    Ensure daily XP is reset if 24 hours have passed since last reset.
    
    This is called before awarding XP to check/reset the daily counter.
    """
    check_sql = """
        SELECT last_xp_reset_at, daily_xp
        FROM user_streaks
        WHERE user_id = $1
    """
    rows = await fetch(check_sql, user_id)
    
    if not rows:
        return
    
    last_reset = rows[0].get("last_xp_reset_at")
    if not last_reset:
        return
    
    # Check if 24 hours have passed
    now = datetime.now(timezone.utc)
    
    # Ensure last_reset is a datetime with timezone
    # asyncpg returns datetime objects directly, but check for timezone
    if not isinstance(last_reset, datetime):
        return
    
    if last_reset.tzinfo is None:
        last_reset = last_reset.replace(tzinfo=timezone.utc)
    
    time_since_reset = now - last_reset
    
    if time_since_reset >= timedelta(hours=24):
        # Reset daily XP
        reset_sql = """
            UPDATE user_streaks
            SET daily_xp = 0,
                last_xp_reset_at = now(),
                updated_at = now()
            WHERE user_id = $1
        """
        await execute(reset_sql, user_id)

