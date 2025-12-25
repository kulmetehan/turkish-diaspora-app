# Backend/services/outreach_rate_limiting_service.py
"""
Rate limiting service for outreach email sending.

Tracks daily email limits to prevent exceeding SES quotas and maintain
good sender reputation. Uses database tracking for simplicity and reliability.
"""

from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Optional
import os

from app.core.logging import get_logger
from services.db_service import fetch, execute

logger = get_logger()


class OutreachRateLimitingService:
    """
    Service for managing rate limits for outreach email sending.
    
    Tracks daily email counts and enforces limits to prevent exceeding
    SES quotas and maintain good sender reputation.
    """
    
    def __init__(self, daily_limit: Optional[int] = None):
        """
        Initialize rate limiting service.
        
        Args:
            daily_limit: Maximum emails per day (defaults to OUTREACH_DAILY_LIMIT env var or 50)
        """
        self.daily_limit = daily_limit or int(
            os.getenv("OUTREACH_DAILY_LIMIT", "50")
        )
    
    async def can_send_email(self) -> bool:
        """
        Check if we can send an email today (under daily limit).
        
        Returns:
            True if under limit (can send), False if over limit (cannot send)
        """
        today = date.today()
        count = await self._get_today_count(today)
        
        can_send = count < self.daily_limit
        
        if not can_send:
            logger.info(
                "outreach_rate_limit_exceeded",
                daily_limit=self.daily_limit,
                today_count=count,
                date=today.isoformat(),
            )
        
        return can_send
    
    async def record_email_sent(self) -> None:
        """
        Record that an email was sent (increment today's count).
        
        This should be called after successfully sending an email.
        """
        today = date.today()
        await self._increment_today_count(today)
        
        # Log for monitoring
        count = await self._get_today_count(today)
        logger.info(
            "outreach_email_recorded",
            today_count=count,
            daily_limit=self.daily_limit,
            date=today.isoformat(),
        )
    
    async def get_today_count(self) -> int:
        """
        Get the number of emails sent today.
        
        Returns:
            Number of emails sent today
        """
        today = date.today()
        return await self._get_today_count(today)
    
    async def get_remaining_quota(self) -> int:
        """
        Get the remaining email quota for today.
        
        Returns:
            Number of emails that can still be sent today (0 if at limit)
        """
        today = date.today()
        count = await self._get_today_count(today)
        remaining = max(0, self.daily_limit - count)
        return remaining
    
    async def _get_today_count(self, target_date: date) -> int:
        """
        Get the count of emails sent on a specific date.
        
        Args:
            target_date: Date to check
            
        Returns:
            Number of emails sent on that date
        """
        # Count emails sent today (status = 'sent' or 'delivered' or 'clicked')
        # We count sent/delivered/clicked to avoid counting queued emails that failed
        sql = """
            SELECT COUNT(*)::INTEGER
            FROM outreach_emails
            WHERE DATE(sent_at) = $1
              AND status IN ('sent', 'delivered', 'clicked')
        """
        
        rows = await fetch(sql, target_date)
        
        if rows and len(rows) > 0:
            row_dict = dict(rows[0])
            return row_dict.get("count", 0) or 0
        
        return 0
    
    async def _increment_today_count(self, target_date: date) -> None:
        """
        Increment the count for a specific date.
        
        Note: This is a no-op since we count from outreach_emails table.
        The actual counting happens in _get_today_count() by querying
        the outreach_emails table. This method exists for future use
        if we want to add a separate tracking table for performance.
        
        Args:
            target_date: Date to increment
        """
        # For now, we don't need a separate tracking table.
        # We count directly from outreach_emails table.
        # This method is here for future optimization if needed.
        pass


# Global instance (lazy initialization)
_rate_limiting_service: Optional[OutreachRateLimitingService] = None


def get_outreach_rate_limiting_service() -> OutreachRateLimitingService:
    """Get or create the global outreach rate limiting service instance."""
    global _rate_limiting_service
    if _rate_limiting_service is None:
        _rate_limiting_service = OutreachRateLimitingService()
    return _rate_limiting_service

