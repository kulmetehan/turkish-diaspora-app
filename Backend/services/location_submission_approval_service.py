"""
Location Submission Approval Service
Handles the business logic for approving/rejecting user-submitted locations.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID
from datetime import datetime

from services.db_service import fetch, execute, fetchrow
from services.role_service import assign_role
from services.email_service import EmailService
from services.email_template_service import get_email_template_service
from services.outreach_audit_service import log_outreach_action
from app.core.logging import get_logger

logger = get_logger()


async def approve_submission(
    submission_id: int,
    admin_user_id: UUID,
) -> dict:
    """
    Approve submission and create location.
    
    This function:
    1. Gets submission details
    2. Creates location in locations table with state='CANDIDATE_MANUAL'
    3. If is_owner=True: creates location_owners entry and assigns role
    4. Updates submission status to 'approved'
    5. Links created_location_id
    6. Sends approval email
    7. Logs audit action
    
    Args:
        submission_id: The ID of the submission to approve
        admin_user_id: The UUID of the admin user approving the submission
    
    Returns:
        dict with submission and location information
    
    Raises:
        ValueError: If submission not found, already processed, or location creation fails
    """
    # Get submission details
    submission_sql = """
        SELECT 
            id, name, address, lat, lng, category, user_id, is_owner, status
        FROM user_submitted_locations
        WHERE id = $1
    """
    submission_rows = await fetch(submission_sql, submission_id)
    
    if not submission_rows:
        raise ValueError(f"Submission {submission_id} not found")
    
    submission = submission_rows[0]
    
    if submission["status"] != "pending":
        raise ValueError(f"Cannot approve submission with status: {submission['status']}")
    
    # Generate place_id for new location
    place_id = f"user_submitted_{submission_id}"
    
    # Create location in locations table with state CANDIDATE_MANUAL
    location_insert_sql = """
        INSERT INTO locations (
            place_id, source, name, address, lat, lng, category,
            state, confidence_score, first_seen_at, last_seen_at,
            notes
        )
        VALUES (
            $1, 'USER_SUBMITTED', $2, $3, $4, $5, $6,
            'CANDIDATE_MANUAL', NULL, now(), now(),
            $7
        )
        RETURNING id
    """
    
    notes = f"[User submitted by user_id: {submission['user_id']}, submission_id: {submission_id}]"
    
    location_result = await fetch(
        location_insert_sql,
        place_id,
        submission["name"],
        submission.get("address"),
        float(submission["lat"]),
        float(submission["lng"]),
        submission["category"],
        notes,
    )
    
    if not location_result:
        raise ValueError(f"Failed to create location for submission {submission_id}")
    
    created_location_id = location_result[0]["id"]
    
    # If is_owner=True, create location_owners entry and assign role
    owner_entry_created = False
    if submission["is_owner"]:
        try:
            # Create location_owners entry
            owner_insert_sql = """
                INSERT INTO location_owners (
                    location_id, user_id, claimed_at, created_at, updated_at
                )
                VALUES ($1, $2, now(), now(), now())
                ON CONFLICT (location_id) DO NOTHING
                RETURNING id
            """
            
            owner_result = await fetch(
                owner_insert_sql,
                created_location_id,
                submission["user_id"],
            )
            
            if owner_result:
                owner_entry_created = True
                
                # Assign location_owner role
                try:
                    await assign_role(
                        user_id=submission["user_id"],
                        role="location_owner",
                        city_key=None,
                        is_primary=True,
                    )
                    logger.info(
                        "location_owner_role_assigned",
                        submission_id=submission_id,
                        location_id=created_location_id,
                        user_id=str(submission["user_id"]),
                    )
                except Exception as e:
                    logger.error(
                        "location_owner_role_assignment_failed",
                        submission_id=submission_id,
                        user_id=str(submission["user_id"]),
                        error=str(e),
                        exc_info=True,
                    )
                    # Continue anyway - role assignment is not critical
                    # But log as error so we can see it in production
        except Exception as e:
            logger.warning(
                "location_owner_entry_failed",
                submission_id=submission_id,
                location_id=created_location_id,
                user_id=str(submission["user_id"]),
                error=str(e),
            )
            # Continue anyway - owner entry failure is not critical
    
    # Update submission status to approved
    update_sql = """
        UPDATE user_submitted_locations
        SET status = 'approved',
            reviewed_by = $1,
            reviewed_at = now(),
            created_location_id = $2,
            updated_at = now()
        WHERE id = $3
        RETURNING 
            id, name, address, lat, lng, category, user_id, is_owner,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_location_id, created_at, updated_at
    """
    
    update_result = await fetch(
        update_sql,
        admin_user_id,
        created_location_id,
        submission_id,
    )
    
    if not update_result:
        raise ValueError(f"Failed to update submission {submission_id} status")
    
    logger.info(
        "location_submission_approved",
        submission_id=submission_id,
        location_id=created_location_id,
        user_id=str(submission["user_id"]),
        admin_user_id=str(admin_user_id),
        is_owner=submission["is_owner"],
        owner_entry_created=owner_entry_created,
    )
    
    # Get user email for audit logging and email sending
    user_email_sql = """
        SELECT email, raw_user_meta_data->>'name' as user_name
        FROM auth.users WHERE id = $1
    """
    user_rows = await fetch(user_email_sql, submission["user_id"])
    user_email = user_rows[0]["email"] if user_rows and user_rows[0].get("email") else None
    
    # Log to audit log
    await log_outreach_action(
        action_type="location_submission_approved",
        location_id=created_location_id,
        email=user_email,
        details={
            "submission_id": submission_id,
            "user_id": str(submission["user_id"]),
            "admin_user_id": str(admin_user_id),
            "is_owner": submission["is_owner"],
            "approved_at": datetime.now().isoformat(),
        },
    )
    
    # Send approval email
    try:
        if user_rows and user_rows[0].get("email"):
            user_email = user_rows[0]["email"]
            user_name = user_rows[0].get("user_name") or "Gebruiker"
            
            # Get location name
            location_name = submission["name"]
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "location_submission_approved",
                context={
                    "user_name": user_name,
                    "location_name": location_name,
                    "is_owner": submission["is_owner"],
                },
                language=language,
            )
            
            # Send email
            email_service = EmailService()
            subject = f"Uw locatie is goedgekeurd - {location_name}"
            if language == "tr":
                subject = f"Konumunuz onaylandı - {location_name}"
            elif language == "en":
                subject = f"Your location has been approved - {location_name}"
            
            await email_service.send_email(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "location_submission_approval_email_sent",
                submission_id=submission_id,
                user_email=user_email,
            )
    except Exception as e:
        # Email failure should not block approval
        logger.warning(
            "location_submission_approval_email_failed",
            submission_id=submission_id,
            error=str(e),
        )
    
    return {
        "submission_id": submission_id,
        "location_id": created_location_id,
        "user_id": submission["user_id"],
        "is_owner": submission["is_owner"],
        "owner_entry_created": owner_entry_created,
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
        SELECT id, status, user_id, name
        FROM user_submitted_locations
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
        UPDATE user_submitted_locations
        SET status = 'rejected',
            reviewed_by = $1,
            reviewed_at = now(),
            rejection_reason = $2,
            updated_at = now()
        WHERE id = $3
        RETURNING 
            id, name, address, lat, lng, category, user_id, is_owner,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_location_id, created_at, updated_at
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
        "location_submission_rejected",
        submission_id=submission_id,
        user_id=str(submission["user_id"]),
        admin_user_id=str(admin_user_id),
        rejection_reason=rejection_reason,
    )
    
    # Get user email for audit logging and email sending
    user_email_sql = """
        SELECT email, raw_user_meta_data->>'name' as user_name
        FROM auth.users WHERE id = $1
    """
    user_rows = await fetch(user_email_sql, submission["user_id"])
    user_email = user_rows[0]["email"] if user_rows and user_rows[0].get("email") else None
    
    # Log to audit log
    await log_outreach_action(
        action_type="location_submission_rejected",
        location_id=None,  # No location created
        email=user_email,
        details={
            "submission_id": submission_id,
            "user_id": str(submission["user_id"]),
            "admin_user_id": str(admin_user_id),
            "rejection_reason": rejection_reason,
            "rejected_at": datetime.now().isoformat(),
        },
    )
    
    # Send rejection email
    try:
        if user_rows and user_rows[0].get("email"):
            user_email = user_rows[0]["email"]
            user_name = user_rows[0].get("user_name") or "Gebruiker"
            
            # Get location name
            location_name = submission["name"]
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "location_submission_rejected",
                context={
                    "user_name": user_name,
                    "location_name": location_name,
                    "rejection_reason": rejection_reason,
                },
                language=language,
            )
            
            # Send email
            email_service = EmailService()
            subject = f"Uw locatie is afgewezen - {location_name}"
            if language == "tr":
                subject = f"Konumunuz reddedildi - {location_name}"
            elif language == "en":
                subject = f"Your location has been rejected - {location_name}"
            
            await email_service.send_email(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "location_submission_rejection_email_sent",
                submission_id=submission_id,
                user_email=user_email,
            )
    except Exception as e:
        # Email failure should not block rejection
        logger.warning(
            "location_submission_rejection_email_failed",
            submission_id=submission_id,
            error=str(e),
        )
    
    return {
        "submission_id": submission_id,
        "user_id": submission["user_id"],
        "rejection_reason": rejection_reason,
    }

