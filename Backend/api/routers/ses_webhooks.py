# Backend/api/routers/ses_webhooks.py
"""
SES webhook handler for processing bounce and delivery events.

AWS SES sends notifications via SNS (Simple Notification Service).
This endpoint receives SNS notifications and processes SES events.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional, Dict, Any
import json
import hmac
import hashlib
import base64

from app.core.logging import get_logger
from services.db_service import execute, fetch
from datetime import datetime

logger = get_logger()

router = APIRouter(prefix="/ses", tags=["ses"])


async def verify_sns_signature(
    payload: bytes,
    signature: str,
    signing_cert_url: str,
) -> bool:
    """
    Verify SNS message signature.
    
    Note: In production, you should:
    1. Download the certificate from signing_cert_url
    2. Verify the certificate is from AWS
    3. Verify the signature using the certificate
    
    For now, we'll do basic validation. Full implementation requires:
    - Certificate download and verification
    - Signature verification using the certificate's public key
    
    Args:
        payload: Raw message payload
        signature: Base64-encoded signature
        signing_cert_url: URL to AWS certificate
        
    Returns:
        True if signature is valid (or if verification is skipped in dev)
    """
    # TODO: Implement full SNS signature verification
    # For now, we'll accept all messages (in production, implement proper verification)
    # In production, you should:
    # 1. Download certificate from signing_cert_url (must be from sns.{region}.amazonaws.com)
    # 2. Verify certificate chain
    # 3. Extract public key from certificate
    # 4. Verify signature using public key
    
    # Basic check: signing_cert_url should be from AWS
    if not signing_cert_url.startswith("https://sns.") or ".amazonaws.com" not in signing_cert_url:
        logger.warning(
            "sns_invalid_cert_url",
            signing_cert_url=signing_cert_url,
        )
        return False
    
    # In development, we might skip full verification
    # In production, implement full verification
    return True


@router.post("/webhook")
async def ses_webhook(
    request: Request,
    x_amz_sns_message_type: Optional[str] = Header(None, alias="x-amz-sns-message-type"),
    x_amz_sns_topic_arn: Optional[str] = Header(None, alias="x-amz-sns-topic-arn"),
):
    """
    Handle SES webhook events via SNS.
    
    AWS SES sends notifications through SNS. This endpoint:
    1. Receives SNS notifications
    2. Verifies SNS message signature (basic check)
    3. Processes SES bounce/delivery events
    4. Updates outreach_emails status
    
    SNS Message Types:
    - SubscriptionConfirmation: Initial subscription confirmation
    - Notification: Actual SES event (bounce, delivery, etc.)
    """
    try:
        # Get raw body
        body = await request.body()
        
        # Parse JSON payload
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(
                "ses_webhook_invalid_json",
                error=str(e),
            )
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Handle SNS message types
        message_type = payload.get("Type") or x_amz_sns_message_type
        
        if message_type == "SubscriptionConfirmation":
            # SNS subscription confirmation - return subscribe URL
            subscribe_url = payload.get("SubscribeURL")
            logger.info(
                "sns_subscription_confirmation",
                subscribe_url=subscribe_url,
            )
            return {
                "ok": True,
                "message": "Subscription confirmation received",
                "subscribe_url": subscribe_url,
            }
        
        elif message_type == "Notification":
            # Actual SES event notification
            message = payload.get("Message")
            if not message:
                logger.error("ses_webhook_no_message")
                raise HTTPException(status_code=400, detail="No message in notification")
            
            # Parse SES event message (it's a JSON string)
            try:
                ses_event = json.loads(message) if isinstance(message, str) else message
            except json.JSONDecodeError:
                # Message might already be a dict
                ses_event = message
            
            # Verify signature (basic check)
            signing_cert_url = payload.get("SigningCertURL", "")
            signature = payload.get("Signature", "")
            
            if not verify_sns_signature(body, signature, signing_cert_url):
                logger.warning(
                    "ses_webhook_signature_verification_failed",
                    signing_cert_url=signing_cert_url,
                )
                # In production, reject invalid signatures
                # For now, we'll process but log warning
            
            # Process SES event
            event_type = ses_event.get("eventType")
            
            if event_type == "Bounce":
                await _handle_bounce_event(ses_event)
            elif event_type == "Delivery":
                await _handle_delivery_event(ses_event)
            elif event_type == "Complaint":
                await _handle_complaint_event(ses_event)
            else:
                logger.info(
                    "ses_webhook_unhandled_event",
                    event_type=event_type,
                    ses_event=ses_event,
                )
            
            return {"ok": True, "message": f"Processed {event_type} event"}
        
        else:
            logger.warning(
                "ses_webhook_unknown_message_type",
                message_type=message_type,
            )
            return {"ok": True, "message": f"Unknown message type: {message_type}"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "ses_webhook_error",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")


async def _handle_bounce_event(ses_event: Dict[str, Any]) -> None:
    """
    Handle SES bounce event.
    
    Updates outreach_emails status to 'bounced' and records bounce reason.
    """
    try:
        mail = ses_event.get("mail", {})
        message_id = mail.get("messageId", "")
        bounce = ses_event.get("bounce", {})
        bounce_type = bounce.get("bounceType", "Unknown")
        bounce_subtype = bounce.get("bounceSubType", "Unknown")
        bounce_reason = f"{bounce_type}: {bounce_subtype}"
        
        # Find email by message_id (generic field) or ses_message_id (for backward compatibility)
        sql = """
            SELECT id, email, location_id
            FROM outreach_emails
            WHERE message_id = $1 OR ses_message_id = $1
            LIMIT 1
        """
        rows = await fetch(sql, message_id)
        
        if not rows:
            logger.warning(
                "ses_bounce_email_not_found",
                message_id=message_id,
            )
            return
        
        email_record = dict(rows[0])
        email_id = email_record["id"]
        
        # Update email status to bounced
        sql_update = """
            UPDATE outreach_emails
            SET status = 'bounced',
                bounced_at = NOW(),
                bounce_reason = $1,
                updated_at = NOW()
            WHERE id = $2
        """
        await execute(sql_update, bounce_reason, email_id)
        
        logger.info(
            "ses_bounce_processed",
            email_id=email_id,
            message_id=message_id,
            bounce_type=bounce_type,
            bounce_subtype=bounce_subtype,
            email=email_record.get("email"),
            location_id=email_record.get("location_id"),
        )
    
    except Exception as e:
        logger.error(
            "ses_bounce_processing_error",
            error=str(e),
            ses_event=ses_event,
            exc_info=True,
        )
        raise


async def _handle_delivery_event(ses_event: Dict[str, Any]) -> None:
    """
    Handle SES delivery event.
    
    Updates outreach_emails status to 'delivered'.
    """
    try:
        mail = ses_event.get("mail", {})
        message_id = mail.get("messageId", "")
        delivery = ses_event.get("delivery", {})
        
        # Find email by message_id (generic field) or ses_message_id (for backward compatibility)
        sql = """
            SELECT id, email, location_id
            FROM outreach_emails
            WHERE message_id = $1 OR ses_message_id = $1
            LIMIT 1
        """
        rows = await fetch(sql, message_id)
        
        if not rows:
            logger.warning(
                "ses_delivery_email_not_found",
                message_id=message_id,
            )
            return
        
        email_record = dict(rows[0])
        email_id = email_record["id"]
        
        # Update email status to delivered
        sql_update = """
            UPDATE outreach_emails
            SET status = 'delivered',
                delivered_at = NOW(),
                updated_at = NOW()
            WHERE id = $1
        """
        await execute(sql_update, email_id)
        
        logger.info(
            "ses_delivery_processed",
            email_id=email_id,
            message_id=message_id,
            email=email_record.get("email"),
            location_id=email_record.get("location_id"),
        )
    
    except Exception as e:
        logger.error(
            "ses_delivery_processing_error",
            error=str(e),
            ses_event=ses_event,
            exc_info=True,
        )
        raise


async def _handle_complaint_event(ses_event: Dict[str, Any]) -> None:
    """
    Handle SES complaint event (user marked email as spam).
    
    Updates outreach_emails status to 'opted_out' (treating complaint as opt-out).
    """
    try:
        mail = ses_event.get("mail", {})
        message_id = mail.get("messageId", "")
        complaint = ses_event.get("complaint", {})
        complaint_type = complaint.get("complaintFeedbackType", "unknown")
        
        # Find email by message_id (generic field) or ses_message_id (for backward compatibility)
        sql = """
            SELECT id, email, location_id
            FROM outreach_emails
            WHERE message_id = $1 OR ses_message_id = $1
            LIMIT 1
        """
        rows = await fetch(sql, message_id)
        
        if not rows:
            logger.warning(
                "ses_complaint_email_not_found",
                message_id=message_id,
            )
            return
        
        email_record = dict(rows[0])
        email_id = email_record["id"]
        
        # Update email status to opted_out (complaint = opt-out)
        sql_update = """
            UPDATE outreach_emails
            SET status = 'opted_out',
                updated_at = NOW()
            WHERE id = $1
        """
        await execute(sql_update, email_id)
        
        logger.info(
            "ses_complaint_processed",
            email_id=email_id,
            message_id=message_id,
            complaint_type=complaint_type,
            email=email_record.get("email"),
            location_id=email_record.get("location_id"),
        )
    
    except Exception as e:
        logger.error(
            "ses_complaint_processing_error",
            error=str(e),
            ses_event=ses_event,
            exc_info=True,
        )
        raise

