# Backend/services/outreach_analytics_service.py
"""
PostHog analytics service for backend outreach tracking.

Tracks outreach events server-side for complete funnel visibility.
Provides centralized analytics tracking for outreach campaigns.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import os
import httpx
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger()


class OutreachAnalyticsService:
    """
    Service for tracking outreach events in PostHog.
    
    Provides server-side event tracking for outreach campaigns,
    enabling complete funnel visibility from email sent to claim.
    """
    
    def __init__(self):
        """Initialize PostHog analytics service."""
        # Support both POSTHOG_API_KEY and VITE_PUBLIC_POSTHOG_KEY for backward compatibility
        self.posthog_key = os.getenv("POSTHOG_API_KEY") or os.getenv("VITE_PUBLIC_POSTHOG_KEY")
        # Support both POSTHOG_HOST and VITE_PUBLIC_POSTHOG_HOST for backward compatibility
        self.posthog_host = os.getenv("POSTHOG_HOST") or os.getenv("VITE_PUBLIC_POSTHOG_HOST") or "https://app.posthog.com"
        self.enabled = bool(self.posthog_key)
        
        if not self.enabled:
            logger.debug(
                "posthog_analytics_disabled",
                reason="POSTHOG_API_KEY not set",
            )
    
    async def track_outreach_email_sent(
        self,
        email_id: int,
        location_id: int,
        email: str,
        campaign_day: Optional[int] = None,
        batch_size: Optional[int] = None,
    ) -> None:
        """
        Track when an outreach email is sent.
        
        Args:
            email_id: Outreach email ID
            location_id: Location ID
            email: Recipient email address
            campaign_day: Campaign day number (optional)
            batch_size: Batch size for this campaign day (optional)
        """
        if not self.enabled:
            return
        
        await self._capture_event(
            event="outreach_email_sent",
            distinct_id=f"email_{email_id}",
            properties={
                "email_id": email_id,
                "location_id": location_id,
                "email": email,  # Consider hashing for privacy in future
                "campaign_day": campaign_day,
                "batch_size": batch_size,
            }
        )
    
    async def track_outreach_email_delivered(
        self,
        email_id: int,
        location_id: int,
        campaign_day: Optional[int] = None,
    ) -> None:
        """
        Track when an email is delivered.
        
        Args:
            email_id: Outreach email ID
            location_id: Location ID
            campaign_day: Campaign day number (optional)
        """
        if not self.enabled:
            return
        
        await self._capture_event(
            event="outreach_email_delivered",
            distinct_id=f"email_{email_id}",
            properties={
                "email_id": email_id,
                "location_id": location_id,
                "campaign_day": campaign_day,
            }
        )
    
    async def track_outreach_email_clicked(
        self,
        email_id: int,
        location_id: int,
        campaign_day: Optional[int] = None,
    ) -> None:
        """
        Track when an email link is clicked.
        
        Args:
            email_id: Outreach email ID
            location_id: Location ID
            campaign_day: Campaign day number (optional)
        """
        if not self.enabled:
            return
        
        await self._capture_event(
            event="outreach_email_clicked",
            distinct_id=f"email_{email_id}",
            properties={
                "email_id": email_id,
                "location_id": location_id,
                "campaign_day": campaign_day,
            }
        )
    
    async def track_outreach_claim(
        self,
        email_id: int,
        location_id: int,
        campaign_day: Optional[int] = None,
        claim_type: str = "unknown",
    ) -> None:
        """
        Track when a location is claimed after outreach.
        
        Args:
            email_id: Outreach email ID
            location_id: Location ID
            campaign_day: Campaign day number (optional)
            claim_type: Type of claim ("token" or "authenticated")
        """
        if not self.enabled:
            return
        
        await self._capture_event(
            event="outreach_claim",
            distinct_id=f"email_{email_id}",
            properties={
                "email_id": email_id,
                "location_id": location_id,
                "campaign_day": campaign_day,
                "claim_type": claim_type,
            }
        )
    
    async def track_campaign_day_summary(
        self,
        campaign_day: int,
        emails_sent: int,
        emails_delivered: int,
        emails_clicked: int,
        emails_bounced: int,
        claims: int,
        removals: int = 0,
    ) -> None:
        """
        Track daily campaign summary.
        
        Args:
            campaign_day: Campaign day number
            emails_sent: Number of emails sent
            emails_delivered: Number of emails delivered
            emails_clicked: Number of emails clicked
            emails_bounced: Number of emails bounced
            claims: Number of claims
            removals: Number of removals (optional)
        """
        if not self.enabled:
            return
        
        delivery_rate = (emails_delivered / emails_sent * 100) if emails_sent > 0 else 0.0
        click_rate = (emails_clicked / emails_delivered * 100) if emails_delivered > 0 else 0.0
        bounce_rate = (emails_bounced / emails_sent * 100) if emails_sent > 0 else 0.0
        claim_rate = (claims / emails_delivered * 100) if emails_delivered > 0 else 0.0
        
        await self._capture_event(
            event="outreach_campaign_day_summary",
            distinct_id="campaign",
            properties={
                "campaign_day": campaign_day,
                "emails_sent": emails_sent,
                "emails_delivered": emails_delivered,
                "emails_clicked": emails_clicked,
                "emails_bounced": emails_bounced,
                "claims": claims,
                "removals": removals,
                "delivery_rate": round(delivery_rate, 2),
                "click_rate": round(click_rate, 2),
                "bounce_rate": round(bounce_rate, 2),
                "claim_rate": round(claim_rate, 2),
            }
        )
    
    async def _capture_event(
        self,
        event: str,
        distinct_id: str,
        properties: Dict[str, Any],
    ) -> None:
        """
        Send event to PostHog API.
        
        Args:
            event: Event name
            distinct_id: Distinct identifier (e.g., email_id)
            properties: Event properties
        """
        if not self.enabled:
            return
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.posthog_host}/capture/",
                    json={
                        "api_key": self.posthog_key,
                        "event": event,
                        "distinct_id": distinct_id,
                        "properties": {
                            **properties,
                            "$lib": "turkspot-backend",
                            "$lib_version": "1.0.0",
                        },
                        "timestamp": datetime.now().isoformat(),
                    },
                )
                response.raise_for_status()
                
                logger.debug(
                    "posthog_event_sent",
                    posthog_event=event,
                    distinct_id=distinct_id,
                )
        except httpx.HTTPError as e:
            logger.warning(
                "posthog_event_failed",
                posthog_event=event,
                distinct_id=distinct_id,
                error=str(e),
                error_type=type(e).__name__,
            )
        except Exception as e:
            logger.warning(
                "posthog_event_unexpected_error",
                posthog_event=event,
                distinct_id=distinct_id,
                error=str(e),
                error_type=type(e).__name__,
            )


# Global instance (lazy initialization)
_analytics_service: Optional[OutreachAnalyticsService] = None


def get_outreach_analytics_service() -> OutreachAnalyticsService:
    """
    Get or create the global outreach analytics service instance.
    
    Returns:
        OutreachAnalyticsService instance
    """
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = OutreachAnalyticsService()
    return _analytics_service

