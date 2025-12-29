# Backend/services/outreach_mailer_service.py
"""
Outreach mailer service for sending queued outreach emails.

Handles:
- Fetching queued emails from database
- Generating mapview links for locations
- Rendering email templates
- Sending emails via email service
- Updating email status and tracking
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
import secrets
import os

from app.core.logging import get_logger
from services.db_service import fetch, execute
from services.email_service import get_email_service
from services.email_template_service import get_email_template_service
from services.mapview_link_service import generate_mapview_link
from services.outreach_rate_limiting_service import get_outreach_rate_limiting_service
from services.outreach_audit_service import log_outreach_action
from services.consent_service import get_consent_service
from services.outreach_analytics_service import get_outreach_analytics_service

logger = get_logger()


def generate_opt_out_token() -> str:
    """
    Generate a secure token for opt-out links.
    
    Returns:
        URL-safe token string (32 characters)
    """
    return secrets.token_urlsafe(32)


def generate_opt_out_link(opt_out_token: str) -> str:
    """
    Generate an opt-out link URL.
    
    Args:
        opt_out_token: Secure token for opt-out
        
    Returns:
        Full URL for opt-out endpoint
    """
    backend_url = os.getenv("BACKEND_URL", "https://api.turkspot.nl")
    return f"{backend_url}/api/v1/outreach/opt-out?token={opt_out_token}"


def generate_mapview_link_with_tracking(location_id: int, email_id: int) -> str:
    """
    Generate a mapview link with email tracking parameters.
    
    Args:
        location_id: Location ID to focus on
        email_id: Outreach email ID for tracking
        
    Returns:
        Mapview URL with tracking parameters
    """
    base_link = generate_mapview_link(location_id)
    # Add email_id as query parameter for tracking
    separator = "&" if "?" in base_link else "?"
    return f"{base_link}{separator}utm_source=outreach&utm_medium=email&email_id={email_id}"


async def get_queued_emails(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get queued emails from outreach_emails table.
    
    Args:
        limit: Maximum number of queued emails to return
        
    Returns:
        List of queued email records, each dict contains:
        - id: outreach_emails.id
        - location_id: location ID
        - contact_id: outreach_contacts.id
        - email: recipient email address
        - location_name: location name
        - location_lat: location latitude
        - location_lng: location longitude
    """
    sql = """
        SELECT 
            oe.id,
            oe.location_id,
            oe.contact_id,
            oe.email,
            l.name as location_name,
            l.lat as location_lat,
            l.lng as location_lng,
            oe.retry_count,
            oe.last_retry_at,
            oe.campaign_day
        FROM outreach_emails oe
        INNER JOIN locations l ON oe.location_id = l.id
        WHERE oe.status = 'queued'
            AND oe.retry_count < 2  -- Max 2 retries
            AND (
                -- New emails (no retry yet)
                (oe.retry_count = 0 AND oe.last_retry_at IS NULL)
                OR
                -- First retry: wait 1 hour
                (
                    oe.retry_count = 1 
                    AND oe.last_retry_at IS NOT NULL 
                    AND oe.last_retry_at < NOW() - INTERVAL '1 hour'
                )
            )
        ORDER BY 
            oe.retry_count ASC,  -- New emails first, then retries
            oe.created_at ASC    -- Oldest first within same retry count
        LIMIT $1
    """
    
    try:
        rows = await fetch(sql, limit)
        
        if not rows:
            logger.debug("no_queued_emails", limit=limit)
            return []
        
        emails = []
        for row in rows:
            row_dict = dict(row)
            emails.append({
                "id": row_dict.get("id"),
                "location_id": row_dict.get("location_id"),
                "contact_id": row_dict.get("contact_id"),
                "email": row_dict.get("email"),
                "location_name": row_dict.get("location_name"),
                "location_lat": float(row_dict.get("location_lat")) if row_dict.get("location_lat") else None,
                "location_lng": float(row_dict.get("location_lng")) if row_dict.get("location_lng") else None,
            })
        
        logger.info("queued_emails_found", count=len(emails), limit=limit)
        return emails
        
    except Exception as e:
        logger.error(
            "get_queued_emails_failed",
            limit=limit,
            error=str(e),
            exc_info=True,
        )
        raise


async def send_queued_emails(limit: int = 50) -> Dict[str, Any]:
    """
    Send queued outreach emails.
    
    Process:
    1. Get queued emails (via get_queued_emails)
    2. For each email:
       - Generate mapview link
       - Render email template
       - Send email via email service
       - Update status to 'sent'
       - Record in rate limiting service
    3. Return statistics
    
    Args:
        limit: Maximum number of emails to process
        
    Returns:
        Dictionary with statistics:
        - sent: number of emails successfully sent
        - failed: number of emails that failed
        - errors: list of error messages
    """
    rate_limiting_service = get_outreach_rate_limiting_service()
    email_service = get_email_service()
    template_service = get_email_template_service()
    consent_service = get_consent_service()
    
    # Check if we can send emails today
    can_send = await rate_limiting_service.can_send_email()
    if not can_send:
        logger.info(
            "outreach_rate_limit_reached",
            daily_limit=rate_limiting_service.daily_limit,
            today_count=await rate_limiting_service.get_today_count(),
        )
        return {
            "sent": 0,
            "failed": 0,
            "errors": ["Rate limit reached for today"],
        }
    
    # Get queued emails
    queued_emails = await get_queued_emails(limit)
    
    if not queued_emails:
        logger.debug("no_queued_emails_to_send")
        return {
            "sent": 0,
            "failed": 0,
            "errors": [],
        }
    
    # Process emails
    sent_count = 0
    failed_count = 0
    skipped_count = 0
    errors = []
    
    for email_record in queued_emails:
        # Check rate limiting before each email
        if not await rate_limiting_service.can_send_email():
            logger.info(
                "outreach_rate_limit_reached_during_sending",
                sent_so_far=sent_count,
            )
            break
        
        # Check consent before sending
        email_address = email_record["email"]
        has_consent = await consent_service.check_service_consent(email_address)
        if not has_consent:
            logger.info(
                "outreach_email_skipped_no_consent",
                location_id=email_record["location_id"],
                email=email_address,
            )
            # Mark email as skipped (or update status accordingly)
            sql_update_skipped = """
                UPDATE outreach_emails
                SET status = 'opted_out',
                    updated_at = NOW()
                WHERE id = $1
            """
            await execute(sql_update_skipped, email_record["id"])
            skipped_count += 1
            continue
        
        # Check if email is unsubscribed
        check_unsubscribed_sql = """
            SELECT unsubscribed_at FROM email_preferences
            WHERE email = $1 AND unsubscribed_at IS NOT NULL
            LIMIT 1
        """
        unsubscribed_rows = await fetch(check_unsubscribed_sql, email_address)
        if unsubscribed_rows:
            logger.info(
                "outreach_email_skipped_unsubscribed",
                location_id=email_record["location_id"],
                email=email_address,
            )
            # Mark email as skipped
            sql_update_skipped = """
                UPDATE outreach_emails
                SET status = 'opted_out',
                    updated_at = NOW()
                WHERE id = $1
            """
            await execute(sql_update_skipped, email_record["id"])
            skipped_count += 1
            continue
        
        # Ensure service consent record exists (implicit consent for outreach)
        await consent_service.ensure_service_consent(email_address)
        
        try:
            # Generate opt-out token
            opt_out_token = generate_opt_out_token()
            
            # Save opt-out token to database before sending
            sql_update_token = """
                UPDATE outreach_emails
                SET opt_out_token = $1
                WHERE id = $2
            """
            await execute(sql_update_token, opt_out_token, email_record["id"])
            
            # Generate links
            mapview_link = generate_mapview_link_with_tracking(
                location_id=email_record["location_id"],
                email_id=email_record["id"],
            )
            opt_out_link = generate_opt_out_link(opt_out_token)
            
            # Prepare template context
            template_context = {
                "location_name": email_record["location_name"] or "Uw locatie",
                "mapview_link": mapview_link,
                "opt_out_link": opt_out_link,
            }
            
            # Determine language (default to 'nl', can be extended later)
            language = "nl"
            
            # Render email template
            try:
                html_body, text_body = template_service.render_template(
                    template_name="outreach_email",
                    context=template_context,
                    language=language,
                    email=email_record["email"],
                )
            except Exception as e:
                error_msg = f"Template rendering failed for location {email_record['location_id']}: {str(e)}"
                errors.append(error_msg)
                logger.error(
                    "outreach_template_render_failed",
                    location_id=email_record["location_id"],
                    email=email_record["email"],
                    error=str(e),
                    exc_info=True,
                )
                failed_count += 1
                continue
            
            # Determine email subject based on language
            if language == "tr":
                subject = f"Konumunuz Turkspot'ta - {email_record['location_name']}"
            elif language == "en":
                subject = f"Your location is on Turkspot - {email_record['location_name']}"
            else:
                subject = f"Uw locatie staat op Turkspot - {email_record['location_name']}"
            
            # Send email and get message ID
            try:
                message_id = await email_service.send_email_with_message_id(
                    to_email=email_record["email"],
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                )
                
                if not message_id:
                    raise Exception("Email service returned no message ID")
                
            except Exception as e:
                # Handle specific error types
                error_str = str(e).lower()
                
                # SES throttling error (soft fail - retry)
                if "throttling" in error_str or "rate" in error_str:
                    error_msg = f"SES throttling error for location {email_record['location_id']}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(
                        "outreach_ses_throttling",
                        location_id=email_record["location_id"],
                        email=email_record["email"],
                        error=str(e),
                    )
                    # Mark for retry (increment retry_count)
                    await _mark_for_retry(email_record["id"], email_record.get("retry_count", 0))
                    continue
                
                # Invalid email address
                elif "invalid" in error_str or "bounce" in error_str or "rejected" in error_str:
                    error_msg = f"Invalid email address for location {email_record['location_id']}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(
                        "outreach_invalid_email",
                        location_id=email_record["location_id"],
                        email=email_record["email"],
                        error=str(e),
                    )
                    # Mark as bounced
                    await _update_email_status(
                        email_record["id"],
                        status="bounced",
                        bounce_reason=str(e),
                    )
                    failed_count += 1
                    continue
                
                # Other errors (soft fail - retry if retry_count < 2)
                else:
                    error_msg = f"Email send failed for location {email_record['location_id']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(
                        "outreach_email_send_failed",
                        location_id=email_record["location_id"],
                        email=email_record["email"],
                        error=str(e),
                        exc_info=True,
                    )
                    
                    retry_count = email_record.get("retry_count", 0)
                    if retry_count < 2:
                        # Mark for retry
                        await _mark_for_retry(email_record["id"], retry_count)
                    else:
                        # Max retries reached - mark as failed
                        failed_count += 1
                    continue
            
            # Update email status to 'sent' with message ID
            await _update_email_status(
                email_record["id"],
                status="sent",
                sent_at=datetime.utcnow(),
                message_id=message_id,
            )
            
            # Record in rate limiting service
            await rate_limiting_service.record_email_sent()
            
            # Log to audit log
            await log_outreach_action(
                action_type="email_sent",
                location_id=email_record["location_id"],
                email=email_record["email"],
                details={
                    "email_id": email_record["id"],
                    "message_id": message_id,
                    "location_name": email_record["location_name"],
                    "sent_at": datetime.utcnow().isoformat(),
                },
            )
            
            # Track in PostHog
            analytics_service = get_outreach_analytics_service()
            campaign_day = email_record.get("campaign_day")
            await analytics_service.track_outreach_email_sent(
                email_id=email_record["id"],
                location_id=email_record["location_id"],
                email=email_record["email"],
                campaign_day=campaign_day,
                batch_size=None,  # Will be set by campaign manager if needed
            )
            
            sent_count += 1
            
            logger.info(
                "outreach_email_sent",
                location_id=email_record["location_id"],
                email=email_record["email"],
                mapview_link=mapview_link,
            )
            
        except Exception as e:
            error_msg = f"Unexpected error processing email for location {email_record['location_id']}: {str(e)}"
            errors.append(error_msg)
            logger.error(
                "outreach_email_processing_error",
                location_id=email_record["location_id"],
                email=email_record["email"],
                error=str(e),
                exc_info=True,
            )
            failed_count += 1
    
    # Log summary
    logger.info(
        "outreach_emails_processed",
        sent=sent_count,
        failed=failed_count,
        total=len(queued_emails),
        remaining_quota=await rate_limiting_service.get_remaining_quota(),
    )
    
    return {
        "sent": sent_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "errors": errors,
    }


async def _update_email_status(
    email_id: int,
    status: str,
    sent_at: Optional[datetime] = None,
    bounce_reason: Optional[str] = None,
    message_id: Optional[str] = None,
    delivered_at: Optional[datetime] = None,
) -> None:
    """
    Update outreach email status in database.
    
    Args:
        email_id: outreach_emails.id
        status: New status ('sent', 'bounced', 'delivered', etc.)
        sent_at: Timestamp when email was sent (for 'sent' status)
        bounce_reason: Reason for bounce (for 'bounced' status)
        message_id: Provider message ID (SES, Brevo, etc.) - generic field
        delivered_at: Timestamp when email was delivered (for 'delivered' status)
    """
    try:
        if status == "sent" and sent_at:
            if message_id:
                # Use generic message_id column (also update ses_message_id for backward compatibility)
                sql = """
                    UPDATE outreach_emails
                    SET status = $1,
                        sent_at = $2,
                        message_id = $3,
                        ses_message_id = $3,
                        updated_at = NOW()
                    WHERE id = $4
                """
                await execute(sql, status, sent_at, message_id, email_id)
            else:
                sql = """
                    UPDATE outreach_emails
                    SET status = $1,
                        sent_at = $2,
                        updated_at = NOW()
                    WHERE id = $3
                """
                await execute(sql, status, sent_at, email_id)
        elif status == "bounced" and bounce_reason:
            sql = """
                UPDATE outreach_emails
                SET status = $1,
                    bounced_at = NOW(),
                    bounce_reason = $2,
                    updated_at = NOW()
                WHERE id = $3
            """
            await execute(sql, status, bounce_reason, email_id)
        elif status == "delivered" and delivered_at:
            sql = """
                UPDATE outreach_emails
                SET status = $1,
                    delivered_at = $2,
                    updated_at = NOW()
                WHERE id = $3
            """
            await execute(sql, status, delivered_at, email_id)
        else:
            sql = """
                UPDATE outreach_emails
                SET status = $1,
                    updated_at = NOW()
                WHERE id = $2
            """
            await execute(sql, status, email_id)
            
    except Exception as e:
        logger.error(
            "outreach_email_status_update_failed",
            email_id=email_id,
            status=status,
            error=str(e),
            exc_info=True,
        )
        raise


async def _mark_for_retry(email_id: int, current_retry_count: int) -> None:
    """
    Mark email for retry by incrementing retry_count and updating last_retry_at.
    
    Args:
        email_id: outreach_emails.id
        current_retry_count: Current retry count (before increment)
    """
    try:
        new_retry_count = current_retry_count + 1
        sql = """
            UPDATE outreach_emails
            SET retry_count = $1,
                last_retry_at = NOW(),
                updated_at = NOW()
            WHERE id = $2
        """
        await execute(sql, new_retry_count, email_id)
        
        logger.info(
            "outreach_email_marked_for_retry",
            email_id=email_id,
            retry_count=new_retry_count,
        )
    except Exception as e:
        logger.error(
            "outreach_email_retry_mark_failed",
            email_id=email_id,
            error=str(e),
            exc_info=True,
        )
        raise


def get_outreach_mailer_service():
    """
    Get the outreach mailer service instance.
    
    Returns:
        Module-level functions for outreach email sending
    """
    return {
        "get_queued_emails": get_queued_emails,
        "send_queued_emails": send_queued_emails,
    }

