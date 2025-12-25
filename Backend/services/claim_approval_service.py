"""
Claim Approval Service
Handles the business logic for approving/rejecting authenticated location claims.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from services.db_service import fetch, execute
from services.storage_service import move_logo_to_final, delete_temp_logo, get_public_url
from services.email_service import EmailService
from services.email_template_service import get_email_template_service
from app.core.logging import get_logger

logger = get_logger()


async def approve_claim(
    claim_id: int,
    admin_user_id: UUID,
    logo_url: Optional[str] = None,
) -> dict:
    """
    Approve an authenticated location claim.
    
    This function:
    1. Updates claim status to 'approved'
    2. Creates entry in location_owners table
    3. Copies google_business_link and logo_url to location_owners
    4. Updates user role to location_owner (if role system exists)
    
    Args:
        claim_id: The ID of the claim to approve
        admin_user_id: The UUID of the admin user approving the claim
        logo_url: Optional logo URL (will be set from storage path if not provided)
    
    Returns:
        dict with claim and owner information
    
    Raises:
        ValueError: If claim not found, already processed, or location already owned
    """
    # Get claim details
    claim_sql = """
        SELECT 
            alc.id, alc.location_id, alc.user_id, alc.status,
            alc.google_business_link, alc.logo_storage_path
        FROM authenticated_location_claims alc
        WHERE alc.id = $1
    """
    claim_rows = await fetch(claim_sql, claim_id)
    
    if not claim_rows:
        raise ValueError(f"Claim {claim_id} not found")
    
    claim = claim_rows[0]
    
    if claim["status"] != "pending":
        raise ValueError(f"Cannot approve claim with status: {claim['status']}")
    
    # Check if location is already owned
    existing_owner_sql = """
        SELECT id FROM location_owners WHERE location_id = $1
    """
    existing_owner_rows = await fetch(existing_owner_sql, claim["location_id"])
    
    if existing_owner_rows:
        raise ValueError(f"Location {claim['location_id']} is already owned by another user")
    
    # Update claim status to approved
    update_sql = """
        UPDATE authenticated_location_claims
        SET status = 'approved',
            reviewed_by = $1,
            reviewed_at = now(),
            updated_at = now()
        WHERE id = $2
        RETURNING 
            id, location_id, user_id, status,
            google_business_link, logo_url, logo_storage_path,
            submitted_at, reviewed_by, reviewed_at,
            rejection_reason, created_at, updated_at
    """
    
    update_result = await fetch(update_sql, admin_user_id, claim_id)
    
    if not update_result:
        raise ValueError(f"Failed to update claim {claim_id} status")
    
    # Determine logo_url - move from temp to final storage if needed
    final_logo_url = logo_url
    final_storage_path = None
    
    if claim.get("logo_storage_path"):
        try:
            # Move logo from temp to final storage
            final_storage_path = await move_logo_to_final(
                claim_id=claim_id,
                location_id=claim["location_id"],
                temp_storage_path=claim["logo_storage_path"],
            )
            # Generate public URL from final storage path
            final_logo_url = get_public_url(final_storage_path)
        except Exception as e:
            logger.warning(
                "logo_move_failed",
                claim_id=claim_id,
                location_id=claim["location_id"],
                error=str(e),
            )
            # Fallback: use temp storage path as URL
            if not final_logo_url:
                final_logo_url = get_public_url(claim["logo_storage_path"])
    
    # Create location_owners entry
    owner_insert_sql = """
        INSERT INTO location_owners (
            location_id, user_id, google_business_link, logo_url, claimed_at, created_at, updated_at
        )
        VALUES ($1, $2, $3, $4, now(), now(), now())
        ON CONFLICT (location_id) DO NOTHING
        RETURNING id, location_id, user_id, google_business_link, logo_url, claimed_at
    """
    
    owner_result = await fetch(
        owner_insert_sql,
        claim["location_id"],
        claim["user_id"],
        claim.get("google_business_link"),
        final_logo_url,
    )
    
    if not owner_result:
        logger.warning(
            "location_owner_entry_failed",
            claim_id=claim_id,
            location_id=claim["location_id"],
            user_id=str(claim["user_id"]),
        )
        # Continue anyway - claim is approved even if owner entry fails
    
    # Update user role to location_owner (if user_roles table exists)
    try:
        role_check_sql = """
            SELECT user_id FROM user_roles WHERE user_id = $1
        """
        role_rows = await fetch(role_check_sql, claim["user_id"])
        
        if role_rows:
            # Update existing role
            role_update_sql = """
                UPDATE user_roles
                SET primary_role = 'location_owner',
                    updated_at = now()
                WHERE user_id = $1
            """
            await execute(role_update_sql, claim["user_id"])
        else:
            # Insert new role
            role_insert_sql = """
                INSERT INTO user_roles (user_id, primary_role, earned_at, updated_at)
                VALUES ($1, 'location_owner', now(), now())
                ON CONFLICT (user_id) DO UPDATE
                SET primary_role = 'location_owner', updated_at = now()
            """
            await execute(role_insert_sql, claim["user_id"])
    except Exception as e:
        # Role system might not exist or might have different structure
        logger.warning(
            "user_role_update_failed",
            claim_id=claim_id,
            user_id=str(claim["user_id"]),
            error=str(e),
        )
        # Continue anyway - role update is not critical
    
    logger.info(
        "authenticated_location_claim_approved",
        claim_id=claim_id,
        location_id=claim["location_id"],
        user_id=str(claim["user_id"]),
        admin_user_id=str(admin_user_id),
    )
    
    # Send approval email
    try:
        # Get user email
        user_email_sql = """
            SELECT email, raw_user_meta_data->>'name' as user_name
            FROM auth.users WHERE id = $1
        """
        user_rows = await fetch(user_email_sql, claim["user_id"])
        
        if user_rows and user_rows[0].get("email"):
            user_email = user_rows[0]["email"]
            user_name = user_rows[0].get("user_name") or "Gebruiker"
            
            # Get location name
            location_name_sql = """
                SELECT name FROM locations WHERE id = $1
            """
            location_rows = await fetch(location_name_sql, claim["location_id"])
            location_name = location_rows[0]["name"] if location_rows else "Locatie"
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "claim_approved",
                context={
                    "user_name": user_name,
                    "location_name": location_name,
                },
                language=language,
            )
            
            # Send email
            email_service = EmailService()
            subject = f"Uw claim is goedgekeurd - {location_name}"
            if language == "tr":
                subject = f"Talebiniz onaylandı - {location_name}"
            elif language == "en":
                subject = f"Your claim has been approved - {location_name}"
            
            await email_service.send_email(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "claim_approval_email_sent",
                claim_id=claim_id,
                user_email=user_email,
            )
    except Exception as e:
        # Email failure should not block approval
        logger.warning(
            "claim_approval_email_failed",
            claim_id=claim_id,
            error=str(e),
        )
    
    return {
        "claim_id": claim_id,
        "location_id": claim["location_id"],
        "user_id": claim["user_id"],
        "owner_entry_created": bool(owner_result),
    }


async def reject_claim(
    claim_id: int,
    admin_user_id: UUID,
    rejection_reason: Optional[str] = None,
) -> dict:
    """
    Reject an authenticated location claim.
    
    This function:
    1. Updates claim status to 'rejected'
    2. Sets rejection_reason
    3. Cleans up temp logo storage
    
    Args:
        claim_id: The ID of the claim to reject
        admin_user_id: The UUID of the admin user rejecting the claim
        rejection_reason: Optional reason for rejection
    
    Returns:
        dict with claim information
    
    Raises:
        ValueError: If claim not found or already processed
    """
    # Get claim details
    claim_sql = """
        SELECT id, status, logo_storage_path
        FROM authenticated_location_claims
        WHERE id = $1
    """
    claim_rows = await fetch(claim_sql, claim_id)
    
    if not claim_rows:
        raise ValueError(f"Claim {claim_id} not found")
    
    claim = claim_rows[0]
    
    if claim["status"] != "pending":
        raise ValueError(f"Cannot reject claim with status: {claim['status']}")
    
    # Update claim status to rejected
    update_sql = """
        UPDATE authenticated_location_claims
        SET status = 'rejected',
            reviewed_by = $1,
            reviewed_at = now(),
            rejection_reason = $2,
            updated_at = now()
        WHERE id = $3
        RETURNING 
            id, location_id, user_id, status,
            google_business_link, logo_url, logo_storage_path,
            submitted_at, reviewed_by, reviewed_at,
            rejection_reason, created_at, updated_at
    """
    
    update_result = await fetch(update_sql, admin_user_id, rejection_reason, claim_id)
    
    if not update_result:
        raise ValueError(f"Failed to update claim {claim_id} status")
    
    # Cleanup temp logo storage
    if claim.get("logo_storage_path"):
        try:
            await delete_temp_logo(claim["logo_storage_path"])
        except Exception as e:
            logger.warning(
                "temp_logo_cleanup_failed",
                claim_id=claim_id,
                storage_path=claim["logo_storage_path"],
                error=str(e),
            )
            # Continue anyway - cleanup failure is not critical
    
    logger.info(
        "authenticated_location_claim_rejected",
        claim_id=claim_id,
        location_id=update_result[0].get("location_id"),
        user_id=str(update_result[0].get("user_id")),
        admin_user_id=str(admin_user_id),
        rejection_reason=rejection_reason,
    )
    
    # Send rejection email
    try:
        # Get user email
        user_email_sql = """
            SELECT email, raw_user_meta_data->>'name' as user_name
            FROM auth.users WHERE id = $1
        """
        user_rows = await fetch(user_email_sql, claim["user_id"])
        
        if user_rows and user_rows[0].get("email"):
            user_email = user_rows[0]["email"]
            user_name = user_rows[0].get("user_name") or "Gebruiker"
            
            # Get location name
            location_name_sql = """
                SELECT name FROM locations WHERE id = $1
            """
            location_rows = await fetch(location_name_sql, claim["location_id"])
            location_name = location_rows[0]["name"] if location_rows else "Locatie"
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "claim_rejected",
                context={
                    "user_name": user_name,
                    "location_name": location_name,
                    "rejection_reason": rejection_reason,
                },
                language=language,
            )
            
            # Send email
            email_service = EmailService()
            subject = f"Uw claim is afgewezen - {location_name}"
            if language == "tr":
                subject = f"Talebiniz reddedildi - {location_name}"
            elif language == "en":
                subject = f"Your claim has been rejected - {location_name}"
            
            await email_service.send_email(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "claim_rejection_email_sent",
                claim_id=claim_id,
                user_email=user_email,
            )
    except Exception as e:
        # Email failure should not block rejection
        logger.warning(
            "claim_rejection_email_failed",
            claim_id=claim_id,
            error=str(e),
        )
    
    return {
        "claim_id": claim_id,
        "location_id": update_result[0].get("location_id"),
        "user_id": update_result[0].get("user_id"),
        "rejection_reason": rejection_reason,
    }

