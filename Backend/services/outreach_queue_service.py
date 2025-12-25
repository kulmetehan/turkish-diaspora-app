# Backend/services/outreach_queue_service.py
"""
Outreach queue service for selecting eligible locations and managing email queue.

Handles:
- Selection of locations eligible for outreach emails
- Queue management with rate limiting
- Prioritization of locations (oldest verified first)
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.logging import get_logger
from services.db_service import fetch, execute
from services.outreach_rate_limiting_service import get_outreach_rate_limiting_service

logger = get_logger()


async def get_eligible_locations(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get locations that are eligible for outreach emails.
    
    Selects locations based on:
    - state = 'VERIFIED'
    - No approved claim in authenticated_location_claims or location_owners
    - Contact found in outreach_contacts
    - No email sent yet (no entry in outreach_emails with sent/delivered/clicked/bounced status)
    
    Prioritizes oldest verified locations first.
    
    Args:
        limit: Maximum number of locations to return
        
    Returns:
        List of eligible locations with contact info, each dict contains:
        - id: location ID
        - name: location name
        - address: location address
        - lat: latitude
        - lng: longitude
        - email: contact email
        - contact_id: outreach_contacts.id
        - confidence_score: contact confidence score
    """
    sql = """
        SELECT 
            l.id,
            l.name,
            l.address,
            l.lat,
            l.lng,
            oc.id as contact_id,
            oc.email,
            oc.confidence_score
        FROM locations l
        INNER JOIN outreach_contacts oc ON l.id = oc.location_id
        -- Check if location has an approved claim (authenticated or owner)
        LEFT JOIN authenticated_location_claims alc ON l.id = alc.location_id 
            AND alc.status = 'approved'
        LEFT JOIN location_owners lo ON l.id = lo.location_id
        -- Check if email has already been sent
        LEFT JOIN outreach_emails oe ON l.id = oe.location_id 
            AND oe.status IN ('sent', 'delivered', 'clicked', 'bounced')
        WHERE l.state = 'VERIFIED'
            -- No approved claim exists
            AND alc.id IS NULL
            AND lo.id IS NULL
            -- No email sent yet
            AND oe.id IS NULL
        ORDER BY l.first_seen_at ASC  -- Oldest verified locations first
        LIMIT $1
    """
    
    try:
        rows = await fetch(sql, limit)
        
        if not rows:
            logger.debug(
                "no_eligible_locations",
                limit=limit,
            )
            return []
        
        locations = []
        for row in rows:
            row_dict = dict(row)
            locations.append({
                "id": row_dict.get("id"),
                "name": row_dict.get("name"),
                "address": row_dict.get("address"),
                "lat": float(row_dict.get("lat")) if row_dict.get("lat") else None,
                "lng": float(row_dict.get("lng")) if row_dict.get("lng") else None,
                "contact_id": row_dict.get("contact_id"),
                "email": row_dict.get("email"),
                "confidence_score": row_dict.get("confidence_score"),
            })
        
        logger.info(
            "eligible_locations_found",
            count=len(locations),
            limit=limit,
        )
        
        return locations
        
    except Exception as e:
        logger.error(
            "get_eligible_locations_failed",
            limit=limit,
            error=str(e),
            exc_info=True,
        )
        raise


async def queue_emails_for_sending(limit: int = 100) -> int:
    """
    Queue emails for sending by selecting eligible locations and creating queue entries.
    
    Process:
    1. Get eligible locations (via get_eligible_locations)
    2. Check rate limiting (how many emails can still be sent today)
    3. Create outreach_emails entries with status 'queued' for as many as possible
    4. Return number of emails queued
    
    Args:
        limit: Maximum number of locations to consider for queueing
        
    Returns:
        Number of emails successfully queued
    """
    rate_limiting_service = get_outreach_rate_limiting_service()
    
    # Check if we can send any emails today
    can_send = await rate_limiting_service.can_send_email()
    if not can_send:
        logger.info(
            "outreach_rate_limit_reached",
            daily_limit=rate_limiting_service.daily_limit,
            today_count=await rate_limiting_service.get_today_count(),
        )
        return 0
    
    # Get remaining quota
    remaining_quota = await rate_limiting_service.get_remaining_quota()
    if remaining_quota <= 0:
        logger.info(
            "outreach_quota_exhausted",
            daily_limit=rate_limiting_service.daily_limit,
            today_count=await rate_limiting_service.get_today_count(),
        )
        return 0
    
    # Limit to remaining quota
    effective_limit = min(limit, remaining_quota)
    
    # Get eligible locations
    eligible_locations = await get_eligible_locations(effective_limit)
    
    if not eligible_locations:
        logger.debug("no_eligible_locations_for_queue")
        return 0
    
    # Create queue entries
    queued_count = 0
    errors = []
    
    for location in eligible_locations:
        try:
            # Check again if we can still send (in case we hit limit during processing)
            if not await rate_limiting_service.can_send_email():
                logger.info(
                    "outreach_rate_limit_reached_during_queue",
                    queued_so_far=queued_count,
                )
                break
            
            # Insert queue entry
            insert_sql = """
                INSERT INTO outreach_emails (
                    location_id,
                    contact_id,
                    email,
                    status
                )
                VALUES ($1, $2, $3, 'queued')
                ON CONFLICT DO NOTHING
                RETURNING id
            """
            
            result = await fetch(
                insert_sql,
                location["id"],
                location["contact_id"],
                location["email"],
            )
            
            if result and len(result) > 0:
                queued_count += 1
                logger.debug(
                    "outreach_email_queued",
                    location_id=location["id"],
                    email=location["email"],
                    contact_id=location["contact_id"],
                )
            else:
                # Conflict - email already queued or sent
                logger.debug(
                    "outreach_email_already_exists",
                    location_id=location["id"],
                    email=location["email"],
                )
                
        except Exception as e:
            error_msg = f"Failed to queue email for location {location['id']}: {str(e)}"
            errors.append(error_msg)
            logger.error(
                "outreach_queue_entry_failed",
                location_id=location["id"],
                email=location["email"],
                error=str(e),
                exc_info=True,
            )
    
    if errors:
        logger.warning(
            "outreach_queue_errors",
            error_count=len(errors),
            queued_count=queued_count,
        )
    
    logger.info(
        "outreach_emails_queued",
        queued_count=queued_count,
        eligible_count=len(eligible_locations),
        remaining_quota=await rate_limiting_service.get_remaining_quota(),
    )
    
    return queued_count


def get_outreach_queue_service():
    """
    Get the outreach queue service instance.
    
    Returns:
        Module-level functions for outreach queue management
    """
    return {
        "get_eligible_locations": get_eligible_locations,
        "queue_emails_for_sending": queue_emails_for_sending,
    }

