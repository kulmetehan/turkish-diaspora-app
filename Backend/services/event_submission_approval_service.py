"""
Event Submission Approval Service
Handles the business logic for approving/rejecting user-submitted events.
"""
from __future__ import annotations

import hashlib
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from services.db_service import fetch, execute, fetchrow
from services.email_service import EmailService
from services.email_template_service import get_email_template_service
from services.event_raw_service import insert_event_raw, update_event_raw_processing_state
from services.event_candidate_service import insert_event_candidate
from services.event_sources_service import get_event_source, create_event_source
from app.models.event_raw import EventRawCreate
from app.models.event_candidate import EventCandidateCreate
from app.models.event_sources import EventSourceCreate
from app.core.logging import get_logger

logger = get_logger()


async def _get_or_create_user_submitted_event_source() -> int:
    """
    Get or create the event source for user-submitted events.
    Returns the event_source_id.
    """
    # Try to find existing source
    sources_sql = """
        SELECT id FROM event_sources WHERE key = 'user_submitted' LIMIT 1
    """
    source_rows = await fetch(sources_sql)
    
    if source_rows:
        return int(source_rows[0]["id"])
    
    # Create new source if it doesn't exist
    # Use "ai_page" format which doesn't require selectors (events are manually submitted, not scraped)
    source_create = EventSourceCreate(
        key="user_submitted",
        name="User Submitted Events",
        base_url="https://turkspot.app",
        list_url=None,
        city_key=None,
        selectors={"format": "ai_page"},  # ai_page format doesn't require selectors
        interval_minutes=60,  # Must be > 0, but won't be used for manual submissions
        status="active",
    )
    
    created_source = await create_event_source(source_create)
    logger.info(
        "user_submitted_event_source_created",
        source_id=created_source.id,
    )
    return created_source.id


def _compute_ingest_hash(submission_id: int, title: str, start_time_utc: datetime, url: Optional[str]) -> str:
    """
    Compute ingest hash for user-submitted event.
    Uses submission_id to ensure uniqueness.
    """
    # Use submission_id + title + start_time to create unique hash
    hash_input = f"user_submitted_{submission_id}_{title}_{start_time_utc.isoformat()}"
    if url:
        hash_input += f"_{url}"
    return hashlib.sha1(hash_input.encode("utf-8")).hexdigest()


async def approve_submission(
    submission_id: int,
    admin_user_id: UUID,
) -> dict:
    """
    Approve submission and create event via event_raw pipeline.
    
    This function:
    1. Gets submission details
    2. Gets or creates user_submitted event source
    3. Creates event_raw entry with processing_state='pending'
    4. Normalization bot will process it → events_candidate with state='candidate'
    5. Updates submission status to 'approved'
    6. Links created_event_id (after normalization)
    7. Sends approval email
    8. Logs audit action
    
    Args:
        submission_id: The ID of the submission to approve
        admin_user_id: The UUID of the admin user approving the submission
    
    Returns:
        dict with submission and event_raw information
    
    Raises:
        ValueError: If submission not found, already processed, or event_raw creation fails
    """
    # Get submission details
    submission_sql = """
        SELECT 
            id, title, description, start_time_utc, end_time_utc, location_text,
            lat, lng, url, category_key, user_id, status
        FROM user_submitted_events
        WHERE id = $1
    """
    submission_rows = await fetch(submission_sql, submission_id)
    
    if not submission_rows:
        raise ValueError(f"Submission {submission_id} not found")
    
    submission = submission_rows[0]
    
    if submission["status"] != "pending":
        raise ValueError(f"Cannot approve submission with status: {submission['status']}")
    
    # Get or create user_submitted event source
    event_source_id = await _get_or_create_user_submitted_event_source()
    
    # Compute ingest hash
    ingest_hash = _compute_ingest_hash(
        submission_id=submission_id,
        title=submission["title"],
        start_time_utc=submission["start_time_utc"],
        url=submission.get("url"),
    )
    
    # Create event_raw entry
    raw_payload = {
        "submitted_via": "user_submission",
        "submission_id": submission_id,
        "user_id": str(submission["user_id"]),
        "admin_user_id": str(admin_user_id),
    }
    
    # Combine location_text and venue if both exist
    location_text = submission.get("location_text")
    venue = None
    if location_text and submission.get("lat") and submission.get("lng"):
        # If we have coordinates, we can use location_text as venue
        venue = location_text
    
    event_raw = EventRawCreate(
        event_source_id=event_source_id,
        title=submission["title"],
        description=submission.get("description"),
        location_text=location_text,
        venue=venue,
        event_url=submission.get("url"),
        image_url=None,
        start_at=submission["start_time_utc"],
        end_at=submission.get("end_time_utc"),
        detected_format="json",
        ingest_hash=ingest_hash,
        raw_payload=raw_payload,
        processing_state="pending",
    )
    
    event_raw_id = await insert_event_raw(event_raw)
    
    if event_raw_id is None:
        # Check if it was deduplicated (shouldn't happen with unique hash, but handle it)
        raise ValueError(f"Failed to create event_raw for submission {submission_id}")
    
    logger.info(
        "event_raw_created_from_submission",
        submission_id=submission_id,
        event_raw_id=event_raw_id,
        user_id=str(submission["user_id"]),
    )
    
    # Mark event_raw as enriched (user submissions don't need AI enrichment)
    await update_event_raw_processing_state(
        event_raw_id=event_raw_id,
        state="enriched",
        errors=None,
    )
    
    # Get event source for source_key
    event_source = await get_event_source(event_source_id)
    source_key = event_source.key if event_source else f"user_submitted_{event_source_id}"
    
    # Create events_candidate directly with state='published' so it appears on frontend immediately
    # User submissions are already validated and don't need the normal candidate → verified → published flow
    event_candidate = EventCandidateCreate(
        event_source_id=event_source_id,
        event_raw_id=event_raw_id,
        title=submission["title"],
        description=submission.get("description"),
        start_time_utc=submission["start_time_utc"],
        end_time_utc=submission.get("end_time_utc"),
        location_text=location_text,
        url=submission.get("url"),
        source_key=source_key,
        ingest_hash=ingest_hash,
        state="published",  # Directly publish user-submitted events
    )
    
    # Set category if provided
    if submission.get("category_key"):
        # We need to update the event_candidate after creation to set event_category
        # For now, we'll insert it and then update the category
        pass
    
    created_event_id = await insert_event_candidate(event_candidate)
    
    if created_event_id is None:
        # Check if it was deduplicated
        # Try to find existing event_candidate by event_raw_id
        existing_sql = """
            SELECT id FROM events_candidate WHERE event_raw_id = $1 LIMIT 1
        """
        existing_rows = await fetch(existing_sql, event_raw_id)
        if existing_rows:
            created_event_id = existing_rows[0]["id"]
        else:
            raise ValueError(f"Failed to create events_candidate for submission {submission_id}")
    
    # Update event_category, lat, lng, and country if provided
    updates = []
    params = [created_event_id]
    param_num = 2
    
    if submission.get("category_key"):
        updates.append(f"event_category = ${param_num}")
        params.append(submission["category_key"])
        param_num += 1
    
    # Add lat/lng if provided (user already geocoded the location)
    if submission.get("lat") is not None and submission.get("lng") is not None:
        updates.append(f"lat = ${param_num}")
        params.append(float(submission["lat"]))
        param_num += 1
        updates.append(f"lng = ${param_num}")
        params.append(float(submission["lng"]))
        param_num += 1
        # Set country to 'netherlands' if coordinates are in Netherlands
        # For now, we'll set it to NULL and let the geocoding bot determine it
        # But if we have coordinates, we can assume Netherlands for user submissions
        updates.append(f"country = ${param_num}")
        params.append("netherlands")  # User submissions are assumed to be in Netherlands
        param_num += 1
    
    if updates:
        update_sql = f"""
            UPDATE events_candidate
            SET {', '.join(updates)}
            WHERE id = $1
        """
        await execute(update_sql, *params)
    
    logger.info(
        "event_candidate_created_from_submission",
        submission_id=submission_id,
        event_raw_id=event_raw_id,
        event_candidate_id=created_event_id,
        user_id=str(submission["user_id"]),
    )
    
    # Update submission status to approved and link created_event_id
    update_sql = """
        UPDATE user_submitted_events
        SET status = 'approved',
            reviewed_by = $1,
            reviewed_at = now(),
            created_event_id = $2,
            updated_at = now()
        WHERE id = $3
        RETURNING 
            id, title, description, start_time_utc, end_time_utc, location_text,
            lat, lng, url, category_key, user_id,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_event_id, created_at, updated_at
    """
    
    update_result = await fetch(
        update_sql,
        admin_user_id,
        created_event_id,
        submission_id,
    )
    
    if not update_result:
        raise ValueError(f"Failed to update submission {submission_id} status")
    
    logger.info(
        "event_submission_approved",
        submission_id=submission_id,
        event_raw_id=event_raw_id,
        user_id=str(submission["user_id"]),
        admin_user_id=str(admin_user_id),
    )
    
    # Get user email for email sending
    user_email_sql = """
        SELECT email, raw_user_meta_data->>'name' as user_name
        FROM auth.users WHERE id = $1
    """
    user_rows = await fetch(user_email_sql, submission["user_id"])
    
    # Send approval email
    try:
        if user_rows and user_rows[0].get("email"):
            user_email = user_rows[0]["email"]
            user_name = user_rows[0].get("user_name") or "Gebruiker"
            
            # Get event title
            event_title = submission["title"]
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "event_submission_approved",
                context={
                    "user_name": user_name,
                    "event_title": event_title,
                },
                language=language,
            )
            
            # Send email
            email_service = EmailService()
            subject = f"Uw event is goedgekeurd - {event_title}"
            if language == "tr":
                subject = f"Etkinliğiniz onaylandı - {event_title}"
            elif language == "en":
                subject = f"Your event has been approved - {event_title}"
            
            await email_service.send_email(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "event_submission_approval_email_sent",
                submission_id=submission_id,
                user_email=user_email,
            )
    except Exception as e:
        # Email failure should not block approval
        logger.warning(
            "event_submission_approval_email_failed",
            submission_id=submission_id,
            error=str(e),
        )
    
    return {
        "submission_id": submission_id,
        "event_raw_id": event_raw_id,
        "event_candidate_id": created_event_id,
        "user_id": submission["user_id"],
    }


async def reject_submission(
    submission_id: int,
    admin_user_id: UUID,
    rejection_reason: Optional[str] = None,
) -> dict:
    """
    Reject submission.
    
    This function:
    1. Updates submission status to 'rejected'
    2. Sets rejection_reason
    3. Sends rejection email
    4. Logs audit action
    
    Args:
        submission_id: The ID of the submission to reject
        admin_user_id: The UUID of the admin user rejecting the submission
        rejection_reason: Optional reason for rejection
    
    Returns:
        dict with submission information
    
    Raises:
        ValueError: If submission not found or already processed
    """
    # Get submission details
    submission_sql = """
        SELECT id, status, user_id, title
        FROM user_submitted_events
        WHERE id = $1
    """
    submission_rows = await fetch(submission_sql, submission_id)
    
    if not submission_rows:
        raise ValueError(f"Submission {submission_id} not found")
    
    submission = submission_rows[0]
    
    if submission["status"] != "pending":
        raise ValueError(f"Cannot reject submission with status: {submission['status']}")
    
    # Update submission status to rejected
    update_sql = """
        UPDATE user_submitted_events
        SET status = 'rejected',
            reviewed_by = $1,
            reviewed_at = now(),
            rejection_reason = $2,
            updated_at = now()
        WHERE id = $3
        RETURNING 
            id, title, description, start_time_utc, end_time_utc, location_text,
            lat, lng, url, category_key, user_id,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_event_id, created_at, updated_at
    """
    
    update_result = await fetch(
        update_sql,
        admin_user_id,
        rejection_reason,
        submission_id,
    )
    
    if not update_result:
        raise ValueError(f"Failed to update submission {submission_id} status")
    
    logger.info(
        "event_submission_rejected",
        submission_id=submission_id,
        user_id=str(submission["user_id"]),
        admin_user_id=str(admin_user_id),
        rejection_reason=rejection_reason,
    )
    
    # Get user email for email sending
    user_email_sql = """
        SELECT email, raw_user_meta_data->>'name' as user_name
        FROM auth.users WHERE id = $1
    """
    user_rows = await fetch(user_email_sql, submission["user_id"])
    
    # Send rejection email
    try:
        if user_rows and user_rows[0].get("email"):
            user_email = user_rows[0]["email"]
            user_name = user_rows[0].get("user_name") or "Gebruiker"
            
            # Get event title
            event_title = submission["title"]
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "event_submission_rejected",
                context={
                    "user_name": user_name,
                    "event_title": event_title,
                    "rejection_reason": rejection_reason,
                },
                language=language,
            )
            
            # Send email
            email_service = EmailService()
            subject = f"Uw event is afgewezen - {event_title}"
            if language == "tr":
                subject = f"Etkinliğiniz reddedildi - {event_title}"
            elif language == "en":
                subject = f"Your event has been rejected - {event_title}"
            
            await email_service.send_email(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "event_submission_rejection_email_sent",
                submission_id=submission_id,
                user_email=user_email,
            )
    except Exception as e:
        # Email failure should not block rejection
        logger.warning(
            "event_submission_rejection_email_failed",
            submission_id=submission_id,
            error=str(e),
        )
    
    return {
        "submission_id": submission_id,
        "user_id": submission["user_id"],
        "rejection_reason": rejection_reason,
    }


async def unpublish_submission(
    submission_id: int,
    admin_user_id: UUID,
) -> dict:
    """
    Unpublish/remove an approved event submission.
    
    This function:
    1. Gets submission details (must be approved)
    2. Sets the event_candidate state to 'rejected' so it no longer appears on frontend
    3. Updates submission status to 'rejected'
    4. Logs audit action
    
    Args:
        submission_id: The ID of the submission to unpublish
        admin_user_id: The UUID of the admin user unpublishing the submission
    
    Returns:
        dict with submission and event_candidate information
    
    Raises:
        ValueError: If submission not found or not approved
    """
    # Get submission details
    submission_sql = """
        SELECT 
            id, status, user_id, title, created_event_id
        FROM user_submitted_events
        WHERE id = $1
    """
    submission_rows = await fetch(submission_sql, submission_id)
    
    if not submission_rows:
        raise ValueError(f"Submission {submission_id} not found")
    
    submission = submission_rows[0]
    
    if submission["status"] != "approved":
        raise ValueError(f"Cannot unpublish submission with status: {submission['status']}. Only approved submissions can be unpublished.")
    
    event_candidate_id = submission.get("created_event_id")
    
    # If no created_event_id, try to find event_candidate via event_raw
    if not event_candidate_id:
        # Try to find event_raw_id from submission metadata or find event_candidate by matching title/start_time
        # First, try to find via event_raw that was created from this submission
        event_raw_sql = """
            SELECT er.id as event_raw_id
            FROM event_raw er
            WHERE er.raw_payload->>'submission_id' = $1::text
            LIMIT 1
        """
        event_raw_rows = await fetch(event_raw_sql, str(submission_id))
        
        if event_raw_rows:
            event_raw_id = event_raw_rows[0]["event_raw_id"]
            # Find event_candidate by event_raw_id
            candidate_find_sql = """
                SELECT id, state FROM events_candidate WHERE event_raw_id = $1 LIMIT 1
            """
            candidate_find_rows = await fetch(candidate_find_sql, event_raw_id)
            
            if candidate_find_rows:
                event_candidate_id = candidate_find_rows[0]["id"]
                # Update submission with found event_candidate_id
                await execute(
                    """
                    UPDATE user_submitted_events
                    SET created_event_id = $1
                    WHERE id = $2
                    """,
                    event_candidate_id,
                    submission_id,
                )
                logger.info(
                    "found_and_linked_event_candidate",
                    submission_id=submission_id,
                    event_candidate_id=event_candidate_id,
                    event_raw_id=event_raw_id,
                )
    
    # If we have an event_candidate_id, update its state
    if event_candidate_id:
        # Check current state of event_candidate
        candidate_state_sql = """
            SELECT id, state FROM events_candidate WHERE id = $1
        """
        candidate_rows = await fetch(candidate_state_sql, event_candidate_id)
        
        if candidate_rows:
            current_state = candidate_rows[0]["state"]
            
            # Only update state if it's not already rejected
            if current_state != "rejected":
                # Directly update state to 'rejected' without transition check
                # This allows us to remove events in any state (candidate, verified, published)
                await execute(
                    """
                    UPDATE events_candidate
                    SET state = 'rejected',
                        updated_at = $2
                    WHERE id = $1
                    """,
                    event_candidate_id,
                    datetime.now(timezone.utc),
                )
                
                logger.info(
                    "event_candidate_state_updated_to_rejected",
                    submission_id=submission_id,
                    event_candidate_id=event_candidate_id,
                    previous_state=current_state,
                )
            else:
                # Already rejected, just log it
                logger.info(
                    "event_candidate_already_rejected",
                    submission_id=submission_id,
                    event_candidate_id=event_candidate_id,
                )
        else:
            logger.warning(
                "event_candidate_not_found_for_unpublish",
                submission_id=submission_id,
                event_candidate_id=event_candidate_id,
            )
    else:
        # No event_candidate found - just mark submission as rejected
        # This can happen if the event was never created or was already deleted
        logger.warning(
            "no_event_candidate_found_for_unpublish",
            submission_id=submission_id,
            message="No event_candidate found. Only marking submission as rejected.",
        )
    
    # Update submission status to rejected
    update_sql = """
        UPDATE user_submitted_events
        SET status = 'rejected',
            reviewed_by = $1,
            reviewed_at = now(),
            rejection_reason = 'Event verwijderd door admin',
            updated_at = now()
        WHERE id = $2
        RETURNING 
            id, title, description, start_time_utc, end_time_utc, location_text,
            lat, lng, url, category_key, user_id,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_event_id, created_at, updated_at
    """
    
    update_result = await fetch(
        update_sql,
        admin_user_id,
        submission_id,
    )
    
    if not update_result:
        raise ValueError(f"Failed to update submission {submission_id} status")
    
    logger.info(
        "event_submission_unpublished",
        submission_id=submission_id,
        event_candidate_id=event_candidate_id,
        user_id=str(submission["user_id"]),
        admin_user_id=str(admin_user_id),
    )
    
    return {
        "submission_id": submission_id,
        "event_candidate_id": event_candidate_id,
        "user_id": submission["user_id"],
    }

