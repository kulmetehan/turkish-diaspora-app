from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from app.deps.auth import get_current_user, User
from app.deps.admin_auth import verify_admin_user, AdminUser
from app.core.feature_flags import require_feature
from services.db_service import fetch, execute
from services.email_service import EmailService
from services.email_template_service import get_email_template_service
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/business/locations", tags=["location-claims"])


class LocationClaimCreate(BaseModel):
    verification_notes: Optional[str] = Field(None, max_length=2000, description="Optional notes or verification documents")


class LocationClaimResponse(BaseModel):
    id: int
    location_id: int
    location_name: Optional[str]
    business_account_id: int
    business_account_name: Optional[str]
    status: str  # 'pending', 'approved', 'rejected', 'revoked'
    verification_notes: Optional[str]
    verified_by: Optional[UUID]
    verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class LocationClaimUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|approved|rejected|revoked)$")
    verification_notes: Optional[str] = Field(None, max_length=2000)


@router.post("/{location_id}/claim", response_model=LocationClaimResponse, status_code=201)
async def submit_location_claim(
    location_id: int = Path(..., description="Location ID to claim"),
    claim: LocationClaimCreate = ...,
    user: User = Depends(get_current_user),
):
    """
    Submit a claim request for a location.
    Requires the user to have a business account.
    """
    require_feature("business_accounts_enabled")
    
    # Get user's business account
    account_sql = """
        SELECT id, company_name FROM business_accounts WHERE owner_user_id = $1
    """
    account_rows = await fetch(account_sql, user.user_id)
    
    if not account_rows:
        raise HTTPException(
            status_code=404,
            detail="Business account not found. Please create a business account first."
        )
    
    business_account = account_rows[0]
    business_account_id = business_account["id"]
    
    # Verify location exists
    location_sql = """
        SELECT id, name FROM locations WHERE id = $1
    """
    location_rows = await fetch(location_sql, location_id)
    
    if not location_rows:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Check if location is already claimed
    existing_sql = """
        SELECT id, status FROM business_location_claims WHERE location_id = $1
    """
    existing_rows = await fetch(existing_sql, location_id)
    
    if existing_rows:
        existing_claim = existing_rows[0]
        if existing_claim["status"] in ("pending", "approved"):
            raise HTTPException(
                status_code=409,
                detail=f"Location is already claimed (status: {existing_claim['status']})"
            )
        # If rejected or revoked, allow new claim
        if existing_claim["status"] in ("rejected", "revoked"):
            # Delete old claim to allow new one
            delete_sql = "DELETE FROM business_location_claims WHERE location_id = $1"
            await execute(delete_sql, location_id)
    
    # Check if this business account already has a claim for this location
    duplicate_sql = """
        SELECT id FROM business_location_claims
        WHERE location_id = $1 AND business_account_id = $2
    """
    duplicate_rows = await fetch(duplicate_sql, location_id, business_account_id)
    
    if duplicate_rows:
        raise HTTPException(
            status_code=409,
            detail="You already have a claim for this location"
        )
    
    # Create claim
    insert_sql = """
        INSERT INTO business_location_claims (
            location_id, business_account_id, status, verification_notes,
            created_at, updated_at
        )
        VALUES ($1, $2, 'pending', $3, now(), now())
        RETURNING 
            id, location_id, business_account_id, status, verification_notes,
            verified_by, verified_at, created_at, updated_at
    """
    
    result = await fetch(
        insert_sql,
        location_id,
        business_account_id,
        claim.verification_notes,
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create location claim")
    
    row = result[0]
    
    logger.info(
        "location_claim_submitted",
        claim_id=row["id"],
        location_id=location_id,
        business_account_id=business_account_id,
        user_id=str(user.user_id),
    )
    
    return LocationClaimResponse(
        id=row["id"],
        location_id=row["location_id"],
        location_name=location_rows[0]["name"],
        business_account_id=row["business_account_id"],
        business_account_name=business_account["company_name"],
        status=row["status"],
        verification_notes=row.get("verification_notes"),
        verified_by=row.get("verified_by"),
        verified_at=row.get("verified_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/claims", response_model=List[LocationClaimResponse])
async def list_my_claims(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected|revoked)$"),
    user: User = Depends(get_current_user),
):
    """
    List all location claims for the authenticated user's business account(s).
    """
    require_feature("business_accounts_enabled")
    
    # Get user's business account
    account_sql = """
        SELECT id FROM business_accounts WHERE owner_user_id = $1
    """
    account_rows = await fetch(account_sql, user.user_id)
    
    if not account_rows:
        return []  # No business account = no claims
    
    business_account_id = account_rows[0]["id"]
    
    # Build query with optional status filter
    conditions = ["blc.business_account_id = $1"]
    params = [business_account_id]
    
    if status:
        conditions.append("blc.status = $2")
        params.append(status)
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            blc.id, blc.location_id, blc.business_account_id,
            blc.status, blc.verification_notes,
            blc.verified_by, blc.verified_at,
            blc.created_at, blc.updated_at,
            l.name as location_name,
            ba.company_name as business_account_name
        FROM business_location_claims blc
        JOIN locations l ON l.id = blc.location_id
        JOIN business_accounts ba ON ba.id = blc.business_account_id
        WHERE {where_clause}
        ORDER BY blc.created_at DESC
    """
    
    rows = await fetch(sql, *params)
    
    return [
        LocationClaimResponse(
            id=row["id"],
            location_id=row["location_id"],
            location_name=row.get("location_name"),
            business_account_id=row["business_account_id"],
            business_account_name=row.get("business_account_name"),
            status=row["status"],
            verification_notes=row.get("verification_notes"),
            verified_by=row.get("verified_by"),
            verified_at=row.get("verified_at"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


# Admin endpoints for managing claims
claims_admin_router = APIRouter(prefix="/admin/claims", tags=["admin-location-claims"])


@claims_admin_router.get("", response_model=List[LocationClaimResponse])
async def list_all_claims(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected|revoked)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    List all location claims (admin only).
    """
    require_feature("business_accounts_enabled")
    
    conditions = []
    params = []
    param_num = 1
    
    if status:
        conditions.append(f"blc.status = ${param_num}")
        params.append(status)
        param_num += 1
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    params.append(limit)
    params.append(offset)
    
    sql = f"""
        SELECT 
            blc.id, blc.location_id, blc.business_account_id,
            blc.status, blc.verification_notes,
            blc.verified_by, blc.verified_at,
            blc.created_at, blc.updated_at,
            l.name as location_name,
            ba.company_name as business_account_name
        FROM business_location_claims blc
        JOIN locations l ON l.id = blc.location_id
        JOIN business_accounts ba ON ba.id = blc.business_account_id
        {where_clause}
        ORDER BY blc.created_at DESC
        LIMIT ${param_num} OFFSET ${param_num + 1}
    """
    
    rows = await fetch(sql, *params)
    
    return [
        LocationClaimResponse(
            id=row["id"],
            location_id=row["location_id"],
            location_name=row.get("location_name"),
            business_account_id=row["business_account_id"],
            business_account_name=row.get("business_account_name"),
            status=row["status"],
            verification_notes=row.get("verification_notes"),
            verified_by=row.get("verified_by"),
            verified_at=row.get("verified_at"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@claims_admin_router.put("/{claim_id}", response_model=LocationClaimResponse)
async def update_claim_status(
    claim_id: int = Path(..., description="Claim ID"),
    update: LocationClaimUpdate = ...,
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Update location claim status (approve/reject) - admin only.
    """
    require_feature("business_accounts_enabled")
    
    # Get admin user_id from email
    admin_user_sql = """
        SELECT id FROM auth.users WHERE email = $1 LIMIT 1
    """
    admin_user_rows = await fetch(admin_user_sql, admin.email)
    
    if not admin_user_rows:
        raise HTTPException(status_code=500, detail="Admin user not found")
    
    admin_user_id = admin_user_rows[0]["id"]
    
    # Update claim
    update_sql = """
        UPDATE business_location_claims
        SET status = $1,
            verification_notes = CASE 
                WHEN $2 IS NOT NULL THEN $2 
                ELSE verification_notes 
            END,
            verified_by = CASE 
                WHEN $1 != 'pending' THEN $3 
                ELSE verified_by 
            END,
            verified_at = CASE 
                WHEN $1 != 'pending' THEN now() 
                ELSE verified_at 
            END,
            updated_at = now()
        WHERE id = $4
        RETURNING 
            id, location_id, business_account_id, status, verification_notes,
            verified_by, verified_at, created_at, updated_at
    """
    
    result = await fetch(
        update_sql,
        update.status,
        update.verification_notes,
        admin_user_id,
        claim_id,
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Location claim not found")
    
    row = result[0]
    
    # Get location and business account names for response
    details_sql = """
        SELECT 
            l.name as location_name, 
            ba.company_name as business_account_name,
            ba.owner_user_id
        FROM business_location_claims blc
        JOIN locations l ON l.id = blc.location_id
        JOIN business_accounts ba ON ba.id = blc.business_account_id
        WHERE blc.id = $1
    """
    details_rows = await fetch(details_sql, claim_id)
    details = details_rows[0] if details_rows else {}
    location_name = details.get("location_name", "Locatie")
    
    logger.info(
        "location_claim_updated",
        claim_id=claim_id,
        new_status=update.status,
        admin_email=admin.email,
        location_id=row["location_id"],
    )
    
    # Send email notification if status changed to approved or rejected
    if update.status in ("approved", "rejected"):
        try:
            # Get owner email from business account
            owner_user_id = details.get("owner_user_id")
            logger.info(
                "business_claim_email_attempt",
                claim_id=claim_id,
                status=update.status,
                owner_user_id=str(owner_user_id) if owner_user_id else None,
            )
            if owner_user_id:
                owner_email_sql = """
                    SELECT email, raw_user_meta_data->>'name' as user_name
                    FROM auth.users WHERE id = $1
                """
                owner_rows = await fetch(owner_email_sql, owner_user_id)
                
                if owner_rows and owner_rows[0].get("email"):
                    owner_email = owner_rows[0]["email"]
                    owner_name = owner_rows[0].get("user_name") or "Gebruiker"
                    
                    # Determine language (default to NL)
                    language = "nl"  # TODO: Get from user preferences
                    
                    # Render email template
                    template_service = get_email_template_service()
                    
                    if update.status == "approved":
                        html_body, text_body = template_service.render_template(
                            "claim_approved",
                            context={
                                "user_name": owner_name,
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
                        
                        success = await email_service.send_email(
                            to_email=owner_email,
                            subject=subject,
                            html_body=html_body,
                            text_body=text_body,
                        )
                        
                        if success:
                            logger.info(
                                "business_claim_approval_email_sent",
                                claim_id=claim_id,
                                owner_email=owner_email,
                            )
                        else:
                            logger.warning(
                                "business_claim_approval_email_failed",
                                claim_id=claim_id,
                                owner_email=owner_email,
                                reason="email_service_returned_false",
                                provider=getattr(email_service, '_provider_name', 'unknown'),
                                is_configured=email_service.is_configured,
                            )
                    
                    elif update.status == "rejected":
                        html_body, text_body = template_service.render_template(
                            "claim_rejected",
                            context={
                                "user_name": owner_name,
                                "location_name": location_name,
                                "rejection_reason": update.verification_notes,
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
                        
                        success = await email_service.send_email(
                            to_email=owner_email,
                            subject=subject,
                            html_body=html_body,
                            text_body=text_body,
                        )
                        
                        if success:
                            logger.info(
                                "business_claim_rejection_email_sent",
                                claim_id=claim_id,
                                owner_email=owner_email,
                            )
                        else:
                            logger.warning(
                                "business_claim_rejection_email_failed",
                                claim_id=claim_id,
                                owner_email=owner_email,
                                reason="email_service_returned_false",
                                provider=getattr(email_service, '_provider_name', 'unknown'),
                                is_configured=email_service.is_configured,
                            )
        except Exception as e:
            # Email failure should not block claim update
            logger.error(
                "business_claim_email_failed",
                claim_id=claim_id,
                status=update.status,
                error=str(e),
                exc_info=True,  # Include full traceback
            )
    
    return LocationClaimResponse(
        id=row["id"],
        location_id=row["location_id"],
        location_name=location_name,
        business_account_id=row["business_account_id"],
        business_account_name=details.get("business_account_name"),
        status=row["status"],
        verification_notes=row.get("verification_notes"),
        verified_by=row.get("verified_by"),
        verified_at=row.get("verified_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@claims_admin_router.get("/{claim_id}", response_model=LocationClaimResponse)
async def get_claim(
    claim_id: int = Path(..., description="Claim ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Get a specific location claim by ID (admin only).
    """
    require_feature("business_accounts_enabled")
    
    sql = """
        SELECT 
            blc.id, blc.location_id, blc.business_account_id,
            blc.status, blc.verification_notes,
            blc.verified_by, blc.verified_at,
            blc.created_at, blc.updated_at,
            l.name as location_name,
            ba.company_name as business_account_name
        FROM business_location_claims blc
        JOIN locations l ON l.id = blc.location_id
        JOIN business_accounts ba ON ba.id = blc.business_account_id
        WHERE blc.id = $1
    """
    
    rows = await fetch(sql, claim_id)
    
    if not rows:
        raise HTTPException(status_code=404, detail="Location claim not found")
    
    row = rows[0]
    
    return LocationClaimResponse(
        id=row["id"],
        location_id=row["location_id"],
        location_name=row.get("location_name"),
        business_account_id=row["business_account_id"],
        business_account_name=row.get("business_account_name"),
        status=row["status"],
        verification_notes=row.get("verification_notes"),
        verified_by=row.get("verified_by"),
        verified_at=row.get("verified_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )

