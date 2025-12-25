# Backend/services/consent_service.py
"""
Consent Service for managing user consent flags.

Handles:
- Service consent (implicit for outreach)
- Marketing consent (explicit opt-in)
- Opt-out functionality
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from app.core.logging import get_logger
from services.db_service import fetchrow, execute

logger = get_logger()


class ConsentService:
    """
    Service for managing user consent flags.
    
    Tracks service consent (implicit for outreach) and marketing consent (explicit opt-in).
    """

    async def check_service_consent(self, email: str) -> bool:
        """
        Check if user has service consent (for outreach emails).
        
        Args:
            email: Email address to check
            
        Returns:
            True if service consent is granted, False otherwise.
            Returns True by default if no consent record exists (implicit consent).
        """
        sql = """
            SELECT service_consent
            FROM user_consents
            WHERE email = $1
        """
        row = await fetchrow(sql, email.lower())
        
        if not row:
            # No consent record = implicit consent for service emails
            return True
        
        return bool(row.get("service_consent", True))

    async def check_marketing_consent(self, email: str) -> bool:
        """
        Check if user has marketing consent.
        
        Args:
            email: Email address to check
            
        Returns:
            True if marketing consent is granted, False otherwise.
            Defaults to False (requires explicit opt-in).
        """
        sql = """
            SELECT marketing_consent
            FROM user_consents
            WHERE email = $1
        """
        row = await fetchrow(sql, email.lower())
        
        if not row:
            # No consent record = no marketing consent (requires explicit opt-in)
            return False
        
        return bool(row.get("marketing_consent", False))

    async def opt_out(self, email: str, reason: Optional[str] = None) -> None:
        """
        Opt out user from all emails (sets both consents to false).
        
        Args:
            email: Email address to opt out
            reason: Optional reason for opt-out
        """
        email_lower = email.lower()
        now = datetime.now()
        
        sql = """
            INSERT INTO user_consents (
                email, service_consent, marketing_consent,
                opted_out_at, opt_out_reason, created_at, updated_at
            )
            VALUES ($1, false, false, $2, $3, $4, $4)
            ON CONFLICT (email)
            DO UPDATE SET
                service_consent = false,
                marketing_consent = false,
                opted_out_at = $2,
                opt_out_reason = $3,
                updated_at = $4
        """
        
        await execute(sql, email_lower, now, reason, now)
        
        logger.info(
            "user_opted_out",
            email=email_lower,
            reason=reason,
        )

    async def update_marketing_consent(self, email: str, consent: bool) -> None:
        """
        Update marketing consent (explicit opt-in/opt-out).
        
        Args:
            email: Email address
            consent: True to grant marketing consent, False to revoke
        """
        email_lower = email.lower()
        now = datetime.now()
        
        sql = """
            INSERT INTO user_consents (
                email, service_consent, marketing_consent,
                created_at, updated_at
            )
            VALUES ($1, true, $2, $3, $3)
            ON CONFLICT (email)
            DO UPDATE SET
                marketing_consent = $2,
                updated_at = $3
            WHERE user_consents.opted_out_at IS NULL  -- Don't update if user opted out
        """
        
        await execute(sql, email_lower, consent, now)
        
        logger.info(
            "marketing_consent_updated",
            email=email_lower,
            consent=consent,
        )

    async def ensure_service_consent(self, email: str) -> None:
        """
        Ensure service consent exists (implicit consent for outreach).
        
        This is called when sending outreach emails to ensure consent record exists.
        Does not override opt-out (if opted_out_at is set, consent remains false).
        
        Args:
            email: Email address
        """
        email_lower = email.lower()
        now = datetime.now()
        
        sql = """
            INSERT INTO user_consents (
                email, service_consent, marketing_consent,
                created_at, updated_at
            )
            VALUES ($1, true, false, $2, $2)
            ON CONFLICT (email)
            DO UPDATE SET
                service_consent = true,
                updated_at = $2
            WHERE user_consents.opted_out_at IS NULL  -- Don't override if user opted out
        """
        
        await execute(sql, email_lower, now)


# Singleton instance
_consent_service: Optional[ConsentService] = None


def get_consent_service() -> ConsentService:
    """
    Get singleton instance of ConsentService.
    
    Returns:
        ConsentService instance
    """
    global _consent_service
    if _consent_service is None:
        _consent_service = ConsentService()
    return _consent_service

