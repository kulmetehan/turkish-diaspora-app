# Backend/services/activity_summary_service.py
"""
Activity Summary Service

Calculates and maintains pre-aggregated user activity metrics for gamification queries.
This service updates the user_activity_summary table with metrics such as:
- Last 4 weeks active days
- Total counts of various activity types
- Most recent activity date
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID
import logging

from services.db_service import fetch, fetchrow, execute

logger = logging.getLogger(__name__)


async def update_user_activity_summary(user_id: UUID, city_key: Optional[str] = None) -> None:
    """
    Calculate and update activity summary for a user.
    
    This function:
    1. Calculates last_4_weeks_active_days (unique days with activity in last 4 weeks)
    2. Calculates total counts (söz, check-ins, poll responses)
    3. Finds last_activity_date (most recent activity timestamp)
    4. Gets city_key from user_profiles if not provided
    5. Upserts the summary into user_activity_summary table
    
    Args:
        user_id: UUID of the user
        city_key: Optional city_key. If not provided, will be fetched from user_profiles.
    
    Raises:
        Exception: If database operations fail (logged but not propagated to caller)
    """
    try:
        # Get city_key from user_profiles if not provided
        if city_key is None:
            city_key_sql = """
                SELECT city_key
                FROM user_profiles
                WHERE id = $1
            """
            city_row = await fetchrow(city_key_sql, user_id)
            if city_row:
                city_key = city_row.get("city_key")
        
        # Calculate last_4_weeks_active_days
        # Count distinct days with activity in last 4 weeks from all activity types
        active_days_sql = """
            SELECT COUNT(DISTINCT DATE(created_at)) as active_days
            FROM (
                SELECT created_at FROM check_ins 
                WHERE user_id = $1 AND created_at > NOW() - INTERVAL '4 weeks'
                UNION ALL
                SELECT created_at FROM location_notes 
                WHERE user_id = $1 AND created_at > NOW() - INTERVAL '4 weeks'
                UNION ALL
                SELECT created_at FROM poll_responses 
                WHERE user_id = $1 AND created_at > NOW() - INTERVAL '4 weeks'
            ) activities
        """
        active_days_row = await fetchrow(active_days_sql, user_id)
        last_4_weeks_active_days = int(active_days_row.get("active_days", 0)) if active_days_row else 0
        
        # Calculate totals and last_activity_date in a single query
        totals_sql = """
            SELECT 
                (SELECT COUNT(*) FROM location_notes WHERE user_id = $1) as total_söz_count,
                (SELECT COUNT(*) FROM check_ins WHERE user_id = $1) as total_check_in_count,
                (SELECT COUNT(*) FROM poll_responses WHERE user_id = $1) as total_poll_response_count,
                (SELECT MAX(created_at) FROM (
                    SELECT created_at FROM check_ins WHERE user_id = $1
                    UNION ALL
                    SELECT created_at FROM location_notes WHERE user_id = $1
                    UNION ALL
                    SELECT created_at FROM poll_responses WHERE user_id = $1
                ) all_activities) as last_activity_date
        """
        totals_row = await fetchrow(totals_sql, user_id)
        
        if not totals_row:
            # No activities found, set defaults
            total_söz_count = 0
            total_check_in_count = 0
            total_poll_response_count = 0
            last_activity_date = None
        else:
            total_söz_count = int(totals_row.get("total_söz_count", 0) or 0)
            total_check_in_count = int(totals_row.get("total_check_in_count", 0) or 0)
            total_poll_response_count = int(totals_row.get("total_poll_response_count", 0) or 0)
            last_activity_date = totals_row.get("last_activity_date")
        
        # Upsert into user_activity_summary
        upsert_sql = """
            INSERT INTO user_activity_summary (
                user_id,
                last_4_weeks_active_days,
                last_activity_date,
                total_söz_count,
                total_check_in_count,
                total_poll_response_count,
                city_key,
                updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, NOW()
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                last_4_weeks_active_days = EXCLUDED.last_4_weeks_active_days,
                last_activity_date = EXCLUDED.last_activity_date,
                total_söz_count = EXCLUDED.total_söz_count,
                total_check_in_count = EXCLUDED.total_check_in_count,
                total_poll_response_count = EXCLUDED.total_poll_response_count,
                city_key = EXCLUDED.city_key,
                updated_at = NOW()
        """
        
        await execute(
            upsert_sql,
            user_id,
            last_4_weeks_active_days,
            last_activity_date,
            total_söz_count,
            total_check_in_count,
            total_poll_response_count,
            city_key,
        )
        
        logger.debug(
            f"Updated activity summary for user {user_id}: "
            f"{last_4_weeks_active_days} active days, "
            f"{total_söz_count} söz, {total_check_in_count} check-ins, "
            f"{total_poll_response_count} poll responses"
        )
        
    except Exception as e:
        # Log error but don't propagate - we don't want summary updates to break API calls
        logger.error(
            f"Failed to update activity summary for user {user_id}: {e}",
            exc_info=True
        )
        # Don't re-raise - fail silently to not impact user experience
        # Summary updates are non-critical and can be retried later

