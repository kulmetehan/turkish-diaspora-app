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
        
        Counts locations that were claimed after email was sent, either via:
        - Token-based claims (token_location_claims where claim_status IN ('claimed_free', 'expired'))
        - Authenticated claims (location_owners, which is created when authenticated_location_claims is approved)
        
        Returns:
            Claim rate as percentage (0.0 to 100.0)
            Returns 0.0 if no emails have been sent
        """
        # Count total sent emails
        sql_total = """
            SELECT COUNT(*)::INTEGER as count
            FROM outreach_emails
            WHERE status IN ('sent', 'delivered', 'clicked')
        """
        rows_total = await fetch(sql_total)
        total = dict(rows_total[0]).get("count", 0) or 0 if rows_total and len(rows_total) > 0 else 0
        
        if total == 0:
            return 0.0
        
        # Count locations with claims after email was sent
        # Token-based claims
        sql_token_claims = """
            SELECT COUNT(DISTINCT oe.location_id)::INTEGER as count
            FROM outreach_emails oe
            INNER JOIN token_location_claims tlc ON oe.location_id = tlc.location_id
            WHERE oe.status IN ('sent', 'delivered', 'clicked')
            AND tlc.claim_status IN ('claimed_free', 'expired')
            AND tlc.claimed_at >= oe.sent_at
        """
        
        # Authenticated claims (via location_owners)
        sql_auth_claims = """
            SELECT COUNT(DISTINCT oe.location_id)::INTEGER as count
            FROM outreach_emails oe
            INNER JOIN location_owners lo ON oe.location_id = lo.location_id
            WHERE oe.status IN ('sent', 'delivered', 'clicked')
            AND lo.claimed_at >= oe.sent_at
        """
        
        rows_token = await fetch(sql_token_claims)
        rows_auth = await fetch(sql_auth_claims)
        
        token_count = dict(rows_token[0]).get("count", 0) or 0 if rows_token and len(rows_token) > 0 else 0
        auth_count = dict(rows_auth[0]).get("count", 0) or 0 if rows_auth and len(rows_auth) > 0 else 0
        
        # Count unique locations that have either type of claim
        sql_unique_claims = """
            SELECT COUNT(DISTINCT location_id)::INTEGER as count
            FROM (
                SELECT DISTINCT oe.location_id
                FROM outreach_emails oe
                INNER JOIN token_location_claims tlc ON oe.location_id = tlc.location_id
                WHERE oe.status IN ('sent', 'delivered', 'clicked')
                AND tlc.claim_status IN ('claimed_free', 'expired')
                AND tlc.claimed_at >= oe.sent_at
                
                UNION
                
                SELECT DISTINCT oe.location_id
                FROM outreach_emails oe
                INNER JOIN location_owners lo ON oe.location_id = lo.location_id
                WHERE oe.status IN ('sent', 'delivered', 'clicked')
                AND lo.claimed_at >= oe.sent_at
            ) claimed_locations
        """
        
        rows_unique = await fetch(sql_unique_claims)
        claimed_count = dict(rows_unique[0]).get("count", 0) or 0 if rows_unique and len(rows_unique) > 0 else 0
        
        # Calculate percentage
        claim_rate = (claimed_count / total) * 100.0 if total > 0 else 0.0
        
        return round(claim_rate, 2)
    
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
    
    async def get_removal_rate(self) -> float:
        """
        Calculate removal rate as percentage (percentage of emails that resulted in removals).
        
        Counts locations that were removed after email was sent via token-based claims.
        
        Returns:
            Removal rate as percentage (0.0 to 100.0)
            Returns 0.0 if no emails have been sent
        """
        # Count total sent emails
        sql_total = """
            SELECT COUNT(*)::INTEGER as count
            FROM outreach_emails
            WHERE status IN ('sent', 'delivered', 'clicked')
        """
        rows_total = await fetch(sql_total)
        total = dict(rows_total[0]).get("count", 0) or 0 if rows_total and len(rows_total) > 0 else 0
        
        if total == 0:
            return 0.0
        
        # Count locations with removals after email was sent
        sql_removals = """
            SELECT COUNT(DISTINCT oe.location_id)::INTEGER as count
            FROM outreach_emails oe
            INNER JOIN token_location_claims tlc ON oe.location_id = tlc.location_id
            WHERE oe.status IN ('sent', 'delivered', 'clicked')
            AND tlc.claim_status = 'removed'
            AND tlc.removed_at >= oe.sent_at
        """
        
        rows_removals = await fetch(sql_removals)
        removed_count = dict(rows_removals[0]).get("count", 0) or 0 if rows_removals and len(rows_removals) > 0 else 0
        
        # Calculate percentage
        removal_rate = (removed_count / total) * 100.0 if total > 0 else 0.0
        
        return round(removal_rate, 2)
    
    async def get_no_action_rate(self) -> float:
        """
        Calculate no-action rate as percentage (percentage of emails with no claim or removal).
        
        Returns:
            No-action rate as percentage (0.0 to 100.0)
            Returns 100.0 if no emails have been sent (no action possible)
        """
        # Count total sent emails
        sql_total = """
            SELECT COUNT(*)::INTEGER as count
            FROM outreach_emails
            WHERE status IN ('sent', 'delivered', 'clicked')
        """
        rows_total = await fetch(sql_total)
        total = dict(rows_total[0]).get("count", 0) or 0 if rows_total and len(rows_total) > 0 else 0
        
        if total == 0:
            return 100.0  # No emails sent, so 100% no action
        
        # Count locations with either claim or removal after email was sent
        sql_actions = """
            SELECT COUNT(DISTINCT location_id)::INTEGER as count
            FROM (
                SELECT DISTINCT oe.location_id
                FROM outreach_emails oe
                INNER JOIN token_location_claims tlc ON oe.location_id = tlc.location_id
                WHERE oe.status IN ('sent', 'delivered', 'clicked')
                AND (
                    (tlc.claim_status IN ('claimed_free', 'expired') AND tlc.claimed_at >= oe.sent_at)
                    OR (tlc.claim_status = 'removed' AND tlc.removed_at >= oe.sent_at)
                )
                
                UNION
                
                SELECT DISTINCT oe.location_id
                FROM outreach_emails oe
                INNER JOIN location_owners lo ON oe.location_id = lo.location_id
                WHERE oe.status IN ('sent', 'delivered', 'clicked')
                AND lo.claimed_at >= oe.sent_at
            ) action_locations
        """
        
        rows_actions = await fetch(sql_actions)
        action_count = dict(rows_actions[0]).get("count", 0) or 0 if rows_actions and len(rows_actions) > 0 else 0
        
        # Calculate no-action count and percentage
        no_action_count = total - action_count
        no_action_rate = (no_action_count / total) * 100.0 if total > 0 else 100.0
        
        return round(no_action_rate, 2)
    
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
        
        removal_rate = await self.get_removal_rate()
        no_action_rate = await self.get_no_action_rate()
        
        return {
            "mails_sent": mails_sent,
            "bounce_rate": bounce_rate,
            "click_rate": click_rate,
            "claim_rate": claim_rate,
            "removal_rate": removal_rate,
            "no_action_rate": no_action_rate,
        }


# Global instance (lazy initialization)
_metrics_service: Optional[OutreachMetricsService] = None


def get_outreach_metrics_service() -> OutreachMetricsService:
    """Get or create the global outreach metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = OutreachMetricsService()
    return _metrics_service

