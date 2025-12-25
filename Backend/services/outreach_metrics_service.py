# Backend/services/outreach_metrics_service.py
"""
Outreach metrics service for tracking and calculating outreach email statistics.

This is a foundation service that provides basic metrics calculation.
Full implementation with additional metrics will come later in the outreach plan (Fase 9).
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.core.logging import get_logger
from services.db_service import fetch

logger = get_logger()


class OutreachMetricsService:
    """
    Service for calculating outreach email metrics.
    
    Provides metrics for monitoring outreach effectiveness and compliance.
    """
    
    async def get_mails_sent_count(self) -> int:
        """
        Get total number of emails sent (status = 'sent', 'delivered', or 'clicked').
        
        Returns:
            Total number of emails sent
        """
        sql = """
            SELECT COUNT(*)::INTEGER as count
            FROM outreach_emails
            WHERE status IN ('sent', 'delivered', 'clicked')
        """
        
        rows = await fetch(sql)
        
        if rows and len(rows) > 0:
            row_dict = dict(rows[0])
            return row_dict.get("count", 0) or 0
        
        return 0
    
    async def get_bounce_rate(self) -> float:
        """
        Calculate bounce rate as percentage.
        
        Returns:
            Bounce rate as percentage (0.0 to 100.0)
            Returns 0.0 if no emails have been sent
        """
        # Count total sent emails (sent, delivered, clicked, bounced)
        sql_total = """
            SELECT COUNT(*)::INTEGER as count
            FROM outreach_emails
            WHERE status IN ('sent', 'delivered', 'clicked', 'bounced')
        """
        
        rows_total = await fetch(sql_total)
        total = dict(rows_total[0]).get("count", 0) or 0 if rows_total and len(rows_total) > 0 else 0
        
        if total == 0:
            return 0.0
        
        # Count bounced emails
        sql_bounced = """
            SELECT COUNT(*)::INTEGER as count
            FROM outreach_emails
            WHERE status = 'bounced'
        """
        
        rows_bounced = await fetch(sql_bounced)
        bounced = dict(rows_bounced[0]).get("count", 0) or 0 if rows_bounced and len(rows_bounced) > 0 else 0
        
        # Calculate percentage
        bounce_rate = (bounced / total) * 100.0 if total > 0 else 0.0
        
        return round(bounce_rate, 2)
    
    async def get_claim_rate(self) -> float:
        """
        Calculate claim rate as percentage (percentage of emails that resulted in claims).
        
        Note: This requires authenticated_location_claims or token_location_claims to be linked.
        For now, this is a placeholder that returns 0.0.
        Full implementation will come later when claim tracking is integrated.
        
        Returns:
            Claim rate as percentage (0.0 to 100.0)
        """
        # TODO: Implement claim rate calculation when claim tracking is integrated
        # This will require joining outreach_emails with authenticated_location_claims
        # or token_location_claims to count how many emails resulted in claims
        
        logger.debug(
            "outreach_claim_rate_not_implemented",
            message="Claim rate calculation not yet implemented. Will be added when claim tracking is integrated."
        )
        
        return 0.0
    
    async def get_click_rate(self) -> float:
        """
        Calculate click rate as percentage (percentage of emails with clicked status).
        
        Returns:
            Click rate as percentage (0.0 to 100.0)
            Returns 0.0 if no emails have been sent
        """
        # Count total sent emails (sent, delivered, clicked)
        sql_total = """
            SELECT COUNT(*)::INTEGER as count
            FROM outreach_emails
            WHERE status IN ('sent', 'delivered', 'clicked')
        """
        
        rows_total = await fetch(sql_total)
        total = dict(rows_total[0]).get("count", 0) or 0 if rows_total and len(rows_total) > 0 else 0
        
        if total == 0:
            return 0.0
        
        # Count clicked emails
        sql_clicked = """
            SELECT COUNT(*)::INTEGER as count
            FROM outreach_emails
            WHERE status = 'clicked'
        """
        
        rows_clicked = await fetch(sql_clicked)
        clicked = dict(rows_clicked[0]).get("count", 0) or 0 if rows_clicked and len(rows_clicked) > 0 else 0
        
        # Calculate percentage
        click_rate = (clicked / total) * 100.0 if total > 0 else 0.0
        
        return round(click_rate, 2)
    
    async def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all outreach metrics in a single call.
        
        Returns:
            Dictionary with all metrics:
            - mails_sent: Total number of emails sent
            - bounce_rate: Bounce rate as percentage
            - click_rate: Click rate as percentage
            - claim_rate: Claim rate as percentage (placeholder, returns 0.0)
        """
        mails_sent = await self.get_mails_sent_count()
        bounce_rate = await self.get_bounce_rate()
        click_rate = await self.get_click_rate()
        claim_rate = await self.get_claim_rate()
        
        return {
            "mails_sent": mails_sent,
            "bounce_rate": bounce_rate,
            "click_rate": click_rate,
            "claim_rate": claim_rate,
            # Placeholder for future metrics
            "removal_rate": 0.0,  # Will be implemented later
            "no_action_rate": 0.0,  # Will be implemented later
        }


# Global instance (lazy initialization)
_metrics_service: Optional[OutreachMetricsService] = None


def get_outreach_metrics_service() -> OutreachMetricsService:
    """Get or create the global outreach metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = OutreachMetricsService()
    return _metrics_service

