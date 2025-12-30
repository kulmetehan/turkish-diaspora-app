# Backend/api/routers/brevo_webhooks.py
"""
Brevo webhook handler for processing bounce and delivery events.

Brevo sends webhook notifications for email events.
This endpoint receives Brevo webhooks and processes events.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional, Dict, Any
import json
import os

from app.core.logging import get_logger
from services.db_service import execute, fetch
from services.outreach_analytics_service import get_outreach_analytics_service
from datetime import datetime

logger = get_logger()

router = APIRouter(prefix="/brevo", tags=["brevo"])


@router.post("/webhook")
async def brevo_webhook(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_brevo_signature: Optional[str] = Header(None, alias="X-Brevo-Signature"),
):
    """
    Handle Brevo webhook events.
    
    Brevo sends webhook notifications for:
    - Email delivered
    - Email bounced
    - Email opened
    - Email clicked
    - Email unsubscribed
    
    Args:
        request: FastAPI request object
        authorization: Authorization header (for Token authentication)
        x_brevo_signature: Brevo webhook signature for verification (if using signature auth)
    """
    try:
        # Verify token authentication if configured
        webhook_secret = os.getenv("BREVO_WEBHOOK_SECRET")
        if webhook_secret:
            if not authorization:
                logger.warning("brevo_webhook_missing_auth")
                raise HTTPException(status_code=401, detail="Missing authorization header")
            
            # Brevo sends token as "Bearer <token>" or just "<token>"
            token = authorization.replace("Bearer ", "").strip() if authorization.startswith("Bearer ") else authorization.strip()
            
            if token != webhook_secret:
                logger.warning("brevo_webhook_invalid_token")
                raise HTTPException(status_code=401, detail="Invalid webhook token")
        
        # Get raw body
        body = await request.body()
        
        # Parse JSON payload
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(
                "brevo_webhook_invalid_json",
                error=str(e),
            )
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Verify webhook signature (if configured)
        # TODO: Implement signature verification using BREVO_WEBHOOK_SECRET
        # For now, we'll process all webhooks (in production, verify signature)
        
        # Process Brevo event
        # Brevo webhooks can be single events or arrays of events
        events = payload if isinstance(payload, list) else [payload]
        
        for event in events:
            event_type = event.get("event")
            
            if event_type == "hard_bounce" or event_type == "soft_bounce":
                await _handle_bounce_event(event)
            elif event_type == "delivered":
                await _handle_delivery_event(event)
            elif event_type == "unsubscribed":
                await _handle_unsubscribe_event(event)
            else:
                logger.info(
                    "brevo_webhook_unhandled_event",
                    event_type=event_type,
                    event_data=event,
                )
        
        return {"ok": True, "message": f"Processed {len(events)} event(s)"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "brevo_webhook_error",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")


async def _handle_bounce_event(payload: Dict[str, Any]) -> None:
    """Handle Brevo bounce event."""
    try:
        message_id = payload.get("message-id", "")
        email = payload.get("email", "")
        reason = payload.get("reason", "Unknown bounce")
        event_type = payload.get("event", "bounce")
        
        # Find email by message_id
        sql = """
            SELECT id, email, location_id, campaign_day
            FROM outreach_emails
            WHERE message_id = $1
            LIMIT 1
        """
        rows = await fetch(sql, message_id)
        
        if not rows:
            logger.warning(
                "brevo_bounce_email_not_found",
                message_id=message_id,
                email=email,
            )
            return
        
        email_record = dict(rows[0])
        email_id = email_record["id"]
        location_id = email_record["location_id"]
        campaign_day = email_record.get("campaign_day")
        
        # Update email status to bounced
        sql_update = """
            UPDATE outreach_emails
            SET status = 'bounced',
                bounced_at = NOW(),
                bounce_reason = $1,
                updated_at = NOW()
            WHERE id = $2
        """
        await execute(sql_update, f"{event_type}: {reason}", email_id)
        
        logger.info(
            "brevo_bounce_processed",
            email_id=email_id,
            message_id=message_id,
            email=email,
            reason=reason,
            event_type=event_type,
        )
    
    except Exception as e:
        logger.error(
            "brevo_bounce_processing_error",
            error=str(e),
            payload=payload,
            exc_info=True,
        )
        raise


async def _handle_delivery_event(payload: Dict[str, Any]) -> None:
    """Handle Brevo delivery event."""
    try:
        message_id = payload.get("message-id", "")
        email = payload.get("email", "")
        
        # Find email by message_id
        sql = """
            SELECT id, email, location_id, campaign_day
            FROM outreach_emails
            WHERE message_id = $1
            LIMIT 1
        """
        rows = await fetch(sql, message_id)
        
        if not rows:
            logger.warning(
                "brevo_delivery_email_not_found",
                message_id=message_id,
                email=email,
            )
            return
        
        email_record = dict(rows[0])
        email_id = email_record["id"]
        location_id = email_record["location_id"]
        campaign_day = email_record.get("campaign_day")
        
        # Update email status to delivered
        sql_update = """
            UPDATE outreach_emails
            SET status = 'delivered',
                delivered_at = NOW(),
                updated_at = NOW()
            WHERE id = $1
        """
        await execute(sql_update, email_id)
        
        # Track in PostHog
        analytics_service = get_outreach_analytics_service()
        await analytics_service.track_outreach_email_delivered(
            email_id=email_id,
            location_id=location_id,
            campaign_day=campaign_day,
        )
        
        logger.info(
            "brevo_delivery_processed",
            email_id=email_id,
            message_id=message_id,
            email=email,
        )
    
    except Exception as e:
        logger.error(
            "brevo_delivery_processing_error",
            error=str(e),
            payload=payload,
            exc_info=True,
        )
        raise


async def _handle_unsubscribe_event(payload: Dict[str, Any]) -> None:
    """Handle Brevo unsubscribe event."""
    try:
        message_id = payload.get("message-id", "")
        email = payload.get("email", "")
        
        # Find email by message_id
        sql = """
            SELECT id, email, location_id
            FROM outreach_emails
            WHERE message_id = $1
            LIMIT 1
        """
        rows = await fetch(sql, message_id)
        
        if not rows:
            logger.warning(
                "brevo_unsubscribe_email_not_found",
                message_id=message_id,
                email=email,
            )
            return
        
        email_record = dict(rows[0])
        email_id = email_record["id"]
        
        # Update email status to opted_out
        sql_update = """
            UPDATE outreach_emails
            SET status = 'opted_out',
                updated_at = NOW()
            WHERE id = $1
        """
        await execute(sql_update, email_id)
        
        logger.info(
            "brevo_unsubscribe_processed",
            email_id=email_id,
            message_id=message_id,
            email=email,
        )
    
    except Exception as e:
        logger.error(
            "brevo_unsubscribe_processing_error",
            error=str(e),
            payload=payload,
            exc_info=True,
        )
        raise

