# Backend/api/routers/outreach_tracking.py
"""
Outreach tracking endpoints for click tracking and opt-out functionality.

Handles:
- Click tracking when users click links in outreach emails
- Opt-out functionality via secure tokens
"""

from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.core.logging import get_logger
from services.db_service import fetch, execute
from services.outreach_audit_service import log_outreach_action
from services.consent_service import get_consent_service

logger = get_logger()

router = APIRouter(prefix="/outreach", tags=["outreach"])


class OptOutResponse(BaseModel):
    ok: bool
    message: str


class ClickTrackingResponse(BaseModel):
    ok: bool
    message: str


@router.post("/opt-out", response_model=OptOutResponse)
async def opt_out(
    token: str = Query(..., description="Opt-out token from email"),
):
    """
    Handle opt-out request via secure token.
    
    Updates outreach_emails status to 'opted_out' and prevents further emails
    to this contact for this location.
    
    Args:
        token: Secure opt-out token from email link
        
    Returns:
        Confirmation message
    """
    try:
        # Find email by opt-out token
        sql = """
            SELECT id, email, location_id, status
            FROM outreach_emails
            WHERE opt_out_token = $1
            LIMIT 1
        """
        rows = await fetch(sql, token)
        
        if not rows:
            logger.warning(
                "opt_out_token_not_found",
                token=token[:10] + "...",  # Log partial token for security
            )
            # Return success even if token not found (security: don't reveal if token exists)
            return OptOutResponse(
                ok=True,
                message="U bent succesvol afgemeld. U ontvangt geen verdere emails meer.",
            )
        
        email_record = dict(rows[0])
        email_id = email_record["id"]
        
        # Check if already opted out
        if email_record["status"] == "opted_out":
            logger.info(
                "opt_out_already_opted_out",
                email_id=email_id,
                email=email_record.get("email"),
            )
            return OptOutResponse(
                ok=True,
                message="U bent al afgemeld. U ontvangt geen verdere emails meer.",
            )
        
        # Update email status to opted_out
        sql_update = """
            UPDATE outreach_emails
            SET status = 'opted_out',
                updated_at = NOW()
            WHERE id = $1
        """
        await execute(sql_update, email_id)
        
        # Update consent flags (opt out from all emails)
        consent_service = get_consent_service()
        await consent_service.opt_out(
            email=email_record.get("email"),
            reason=f"Opt-out via email link (token: {token[:10]}...)",
        )
        
        logger.info(
            "opt_out_successful",
            email_id=email_id,
            email=email_record.get("email"),
            location_id=email_record.get("location_id"),
        )
        
        # Log to audit log
        await log_outreach_action(
            action_type="opt_out",
            location_id=email_record.get("location_id"),
            email=email_record.get("email"),
            details={
                "email_id": email_id,
                "opt_out_token": token[:10] + "...",  # Partial token for security
            },
        )
        
        return OptOutResponse(
            ok=True,
            message="U bent succesvol afgemeld. U ontvangt geen verdere emails meer.",
        )
    
    except Exception as e:
        logger.error(
            "opt_out_error",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Er is een fout opgetreden bij het afmelden.")


@router.post("/track-click", response_model=ClickTrackingResponse)
async def track_click(
    email_id: int = Query(..., description="Outreach email ID for tracking"),
):
    """
    Track when a user clicks a link in an outreach email.
    
    Updates outreach_emails status to 'clicked' and records click timestamp.
    This is called by the frontend when a user opens the mapview from an email link.
    
    Args:
        email_id: Outreach email ID from URL parameter
        
    Returns:
        Confirmation message
    """
    try:
        # Find email by ID
        sql = """
            SELECT id, email, location_id, status
            FROM outreach_emails
            WHERE id = $1
            LIMIT 1
        """
        rows = await fetch(sql, email_id)
        
        if not rows:
            logger.warning(
                "click_tracking_email_not_found",
                email_id=email_id,
            )
            return ClickTrackingResponse(
                ok=False,
                message="Email not found",
            )
        
        email_record = dict(rows[0])
        
        # Only update if not already clicked (idempotent)
        if email_record["status"] == "clicked":
            logger.debug(
                "click_tracking_already_clicked",
                email_id=email_id,
            )
            return ClickTrackingResponse(
                ok=True,
                message="Click already tracked",
            )
        
        # Update email status to clicked
        sql_update = """
            UPDATE outreach_emails
            SET status = 'clicked',
                clicked_at = NOW(),
                updated_at = NOW()
            WHERE id = $1
        """
        await execute(sql_update, email_id)
        
        logger.info(
            "click_tracking_successful",
            email_id=email_id,
            email=email_record.get("email"),
            location_id=email_record.get("location_id"),
        )
        
        return ClickTrackingResponse(
            ok=True,
            message="Click tracked",
        )
    
    except Exception as e:
        logger.error(
            "click_tracking_error",
            email_id=email_id,
            error=str(e),
            exc_info=True,
        )
        # Don't raise error - tracking failures shouldn't break user experience
        return ClickTrackingResponse(
            ok=False,
            message="Tracking failed",
        )

