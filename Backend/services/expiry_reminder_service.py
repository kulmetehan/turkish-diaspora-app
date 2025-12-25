# Backend/services/expiry_reminder_service.py
"""
Expiry reminder service for sending reminder emails to users with expiring claims.

Handles:
- Finding claims that are expiring soon
- Sending reminder emails
- Marking reminders as sent
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from app.core.logging import get_logger
from services.db_service import fetch, execute
from services.email_service import get_email_service
from services.email_template_service import get_email_template_service
from services.mapview_link_service import generate_mapview_link

logger = get_logger()


async def get_expiring_claims(days_before_expiry: int = 7) -> List[Dict[str, Any]]:
    """
    Get claims that are expiring within the specified number of days.
    
    Args:
        days_before_expiry: Number of days before expiry to send reminder (default: 7)
        
    Returns:
        List of expiring claim records, each dict contains:
        - id: token_location_claims.id
        - location_id: location ID
        - claimed_by_email: email address of claimer
        - free_until: expiry date
        - location_name: location name
        - location_lat: location latitude
        - location_lng: location longitude
    """
    sql = """
        SELECT 
            tlc.id,
            tlc.location_id,
            tlc.claimed_by_email,
            tlc.free_until,
            l.name as location_name,
            l.lat as location_lat,
            l.lng as location_lng
        FROM token_location_claims tlc
        INNER JOIN locations l ON tlc.location_id = l.id
        WHERE tlc.claim_status = 'claimed_free'
            AND tlc.free_until <= NOW() + INTERVAL '%s days'
            AND tlc.reminder_sent_at IS NULL
            AND tlc.claimed_by_email IS NOT NULL
        ORDER BY tlc.free_until ASC
    """ % (days_before_expiry,)
    
    try:
        rows = await fetch(sql)
        
        if not rows:
            logger.debug("no_expiring_claims", days_before_expiry=days_before_expiry)
            return []
        
        claims = []
        for row in rows:
            row_dict = dict(row)
            claims.append({
                "id": row_dict.get("id"),
                "location_id": row_dict.get("location_id"),
                "claimed_by_email": row_dict.get("claimed_by_email"),
                "free_until": row_dict.get("free_until"),
                "location_name": row_dict.get("location_name"),
                "location_lat": float(row_dict.get("location_lat")) if row_dict.get("location_lat") else None,
                "location_lng": float(row_dict.get("location_lng")) if row_dict.get("location_lng") else None,
            })
        
        logger.info("expiring_claims_found", count=len(claims), days_before_expiry=days_before_expiry)
        return claims
        
    except Exception as e:
        logger.error(
            "get_expiring_claims_failed",
            days_before_expiry=days_before_expiry,
            error=str(e),
            exc_info=True,
        )
        raise


async def send_expiry_reminder(
    claim_id: int,
    location_id: int,
    email: str,
    location_name: str,
    free_until: datetime,
    location_lat: Optional[float] = None,
    location_lng: Optional[float] = None,
    language: str = "nl",
) -> bool:
    """
    Send expiry reminder email to claim owner.
    
    Args:
        claim_id: Token location claim ID
        location_id: Location ID
        email: Recipient email address
        location_name: Name of the location
        free_until: Expiry date
        location_lat: Location latitude (optional)
        location_lng: Location longitude (optional)
        language: Language code (nl, tr, en)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Generate mapview link
        mapview_link = generate_mapview_link(location_id, location_lat, location_lng)
        
        # Format expiry date
        expiry_date_str = free_until.strftime("%d-%m-%Y") if free_until else "binnenkort"
        
        # Prepare template context
        context = {
            "location_name": location_name,
            "mapview_link": mapview_link,
            "expiry_date": expiry_date_str,
            "free_until": free_until.isoformat() if free_until else None,
        }
        
        # Get email template service
        template_service = get_email_template_service()
        
        # Render templates
        html_body, text_body = template_service.render_template(
            "expiry_reminder",
            context=context,
            language=language,
        )
        
        # Get subject based on language
        if language == "tr":
            subject = f"Ücretsiz döneminiz yakında sona eriyor - {location_name}"
        elif language == "en":
            subject = f"Your free period is ending soon - {location_name}"
        else:
            subject = f"Uw gratis periode loopt bijna af - {location_name}"
        
        # Get email service
        email_service = get_email_service()
        
        # Send email
        success = await email_service.send_email(
            to_email=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
        
        if success:
            logger.info(
                "expiry_reminder_sent",
                claim_id=claim_id,
                location_id=location_id,
                email=email,
                language=language,
            )
        else:
            logger.warning(
                "expiry_reminder_send_failed",
                claim_id=claim_id,
                location_id=location_id,
                email=email,
            )
        
        return success
        
    except Exception as e:
        logger.error(
            "send_expiry_reminder_failed",
            claim_id=claim_id,
            location_id=location_id,
            email=email,
            error=str(e),
            exc_info=True,
        )
        return False


async def mark_reminder_sent(claim_id: int) -> bool:
    """
    Mark reminder as sent by updating reminder_sent_at timestamp.
    
    Args:
        claim_id: Token location claim ID
        
    Returns:
        True if update successful, False otherwise
    """
    sql = """
        UPDATE token_location_claims
        SET reminder_sent_at = NOW(),
            updated_at = NOW()
        WHERE id = $1
    """
    
    try:
        await execute(sql, claim_id)
        logger.debug("reminder_marked_sent", claim_id=claim_id)
        return True
        
    except Exception as e:
        logger.error(
            "mark_reminder_sent_failed",
            claim_id=claim_id,
            error=str(e),
            exc_info=True,
        )
        return False


async def process_expiring_claims(
    days_before_expiry: int = 7,
    batch_size: int = 50,
    language: str = "nl",
) -> Dict[str, Any]:
    """
    Process expiring claims and send reminder emails.
    
    Args:
        days_before_expiry: Number of days before expiry to send reminder
        batch_size: Maximum number of reminders to send in one batch
        language: Default language for emails (nl, tr, en)
        
    Returns:
        Dictionary with processing results:
        - total_found: Number of expiring claims found
        - sent: Number of reminders sent successfully
        - failed: Number of reminders that failed to send
    """
    # Get expiring claims
    claims = await get_expiring_claims(days_before_expiry)
    
    if not claims:
        return {
            "total_found": 0,
            "sent": 0,
            "failed": 0,
        }
    
    # Limit batch size
    claims = claims[:batch_size]
    
    sent = 0
    failed = 0
    
    for claim in claims:
        claim_id = claim["id"]
        location_id = claim["location_id"]
        email = claim["claimed_by_email"]
        location_name = claim["location_name"]
        free_until = claim["free_until"]
        location_lat = claim.get("location_lat")
        location_lng = claim.get("location_lng")
        
        # Send reminder
        success = await send_expiry_reminder(
            claim_id=claim_id,
            location_id=location_id,
            email=email,
            location_name=location_name,
            free_until=free_until,
            location_lat=location_lat,
            location_lng=location_lng,
            language=language,
        )
        
        if success:
            # Mark as sent
            await mark_reminder_sent(claim_id)
            sent += 1
        else:
            failed += 1
    
    result = {
        "total_found": len(claims),
        "sent": sent,
        "failed": failed,
    }
    
    logger.info(
        "expiry_reminders_processed",
        **result,
        days_before_expiry=days_before_expiry,
    )
    
    return result

