from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from uuid import UUID

from app.deps.auth import get_current_user, User
from services.db_service import fetch, execute
from services.storage_service import upload_logo_to_temp, get_public_url
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/locations", tags=["authenticated-claims"])


class AuthenticatedClaimCreate(BaseModel):
    google_business_link: Optional[str] = Field(None, description="Optional Google Business profile link")
    # Logo upload will be handled separately later (Stap 3.9)


class AuthenticatedClaimResponse(BaseModel):
    id: int
    location_id: int
    location_name: Optional[str]
    user_id: UUID
    status: str  # 'pending', 'approved', 'rejected'
    google_business_link: Optional[str]
    logo_url: Optional[str]
    submitted_at: datetime
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime


class ClaimStatusResponse(BaseModel):
    claim: Optional[AuthenticatedClaimResponse]
    is_claimed: bool
    can_claim: bool  # True if user can claim this location


@router.post("/{location_id}/claim", response_model=AuthenticatedClaimResponse, status_code=201)
async def submit_authenticated_claim(
    location_id: int = Path(..., description="Location ID to claim"),
    claim: AuthenticatedClaimCreate = ...,
    user: User = Depends(get_current_user),
):
    """
    Submit a claim request for a location (authenticated users, no business account required).
    Requires at least one field: google_business_link or logo (logo upload coming in Stap 3.9).
    """
    # Validate that at least one field is provided
    if not claim.google_business_link:
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided: google_business_link or logo"
        )
    
    # Validate Google Business link format if provided
    if claim.google_business_link:
        try:
            # Basic URL validation
            if not (claim.google_business_link.startswith("http://") or 
                    claim.google_business_link.startswith("https://")):
                raise HTTPException(
                    status_code=400,
                    detail="Google Business link must be a valid URL starting with http:// or https://"
                )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid Google Business link format"
            )
    
    # Verify location exists
    location_sql = """
        SELECT id, name FROM locations WHERE id = $1
    """
    location_rows = await fetch(location_sql, location_id)
    
    if not location_rows:
        raise HTTPException(status_code=404, detail="Location not found")
    
    location_name = location_rows[0]["name"]
    
    # Check if location is already claimed via authenticated_location_claims
    existing_claim_sql = """
        SELECT id, status, user_id FROM authenticated_location_claims WHERE location_id = $1
    """
    existing_claim_rows = await fetch(existing_claim_sql, location_id)
    
    if existing_claim_rows:
        existing_claim = existing_claim_rows[0]
        if existing_claim["status"] in ("pending", "approved"):
            raise HTTPException(
                status_code=409,
                detail=f"Location is already claimed (status: {existing_claim['status']})"
            )
        # If rejected, allow new claim (delete old one)
        if existing_claim["status"] == "rejected":
            delete_sql = "DELETE FROM authenticated_location_claims WHERE location_id = $1"
            await execute(delete_sql, location_id)
    
    # Check if location is already owned (via location_owners)
    existing_owner_sql = """
        SELECT id FROM location_owners WHERE location_id = $1
    """
    existing_owner_rows = await fetch(existing_owner_sql, location_id)
    
    if existing_owner_rows:
        raise HTTPException(
            status_code=409,
            detail="Location is already owned by another user"
        )
    
    # Check if this user already has a claim for this location
    duplicate_sql = """
        SELECT id FROM authenticated_location_claims
        WHERE location_id = $1 AND user_id = $2
    """
    duplicate_rows = await fetch(duplicate_sql, location_id, user.user_id)
    
    if duplicate_rows:
        raise HTTPException(
            status_code=409,
            detail="You already have a claim request for this location"
        )
    
    # Create claim
    insert_sql = """
        INSERT INTO authenticated_location_claims (
            location_id, user_id, status, google_business_link,
            submitted_at, created_at, updated_at
        )
        VALUES ($1, $2, 'pending', $3, now(), now(), now())
        RETURNING 
            id, location_id, user_id, status, google_business_link,
            logo_url, submitted_at, reviewed_by, reviewed_at,
            rejection_reason, created_at, updated_at
    """
    
    result = await fetch(
        insert_sql,
        location_id,
        user.user_id,
        claim.google_business_link,
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create location claim")
    
    row = result[0]
    
    logger.info(
        "authenticated_location_claim_submitted",
        claim_id=row["id"],
        location_id=location_id,
        user_id=str(user.user_id),
    )
    
    return AuthenticatedClaimResponse(
        id=row["id"],
        location_id=row["location_id"],
        location_name=location_name,
        user_id=row["user_id"],
        status=row["status"],
        google_business_link=row.get("google_business_link"),
        logo_url=row.get("logo_url"),
        submitted_at=row["submitted_at"],
        reviewed_by=row.get("reviewed_by"),
        reviewed_at=row.get("reviewed_at"),
        rejection_reason=row.get("rejection_reason"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/{location_id}/claim-status", response_model=ClaimStatusResponse)
async def get_claim_status(
    location_id: int = Path(..., description="Location ID"),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Check claim status for a specific location.
    Returns claim info if exists, null otherwise.
    Also indicates if the current user can claim this location.
    """
    # Verify location exists
    location_sql = """
        SELECT id FROM locations WHERE id = $1
    """
    location_rows = await fetch(location_sql, location_id)
    
    if not location_rows:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Check for existing authenticated claim
    claim_sql = """
        SELECT 
            alc.id, alc.location_id, alc.user_id, alc.status,
            alc.google_business_link, alc.logo_url, alc.submitted_at,
            alc.reviewed_by, alc.reviewed_at, alc.rejection_reason,
            alc.created_at, alc.updated_at,
            l.name as location_name
        FROM authenticated_location_claims alc
        JOIN locations l ON l.id = alc.location_id
        WHERE alc.location_id = $1
        ORDER BY alc.created_at DESC
        LIMIT 1
    """
    claim_rows = await fetch(claim_sql, location_id)
    
    # Check for existing owner
    owner_sql = """
        SELECT id FROM location_owners WHERE location_id = $1
    """
    owner_rows = await fetch(owner_sql, location_id)
    
    is_claimed = bool(claim_rows and claim_rows[0]["status"] in ("pending", "approved")) or bool(owner_rows)
    
    # Determine if current user can claim
    can_claim = False
    if user:
        # Can claim if:
        # 1. No existing claim/owner, OR
        # 2. Existing claim is rejected and user is the one who made it
        if not is_claimed:
            can_claim = True
        elif claim_rows and claim_rows[0]["status"] == "rejected" and claim_rows[0]["user_id"] == user.user_id:
            can_claim = True
    
    if claim_rows:
        claim_row = claim_rows[0]
        claim = AuthenticatedClaimResponse(
            id=claim_row["id"],
            location_id=claim_row["location_id"],
            location_name=claim_row.get("location_name"),
            user_id=claim_row["user_id"],
            status=claim_row["status"],
            google_business_link=claim_row.get("google_business_link"),
            logo_url=claim_row.get("logo_url"),
            submitted_at=claim_row["submitted_at"],
            reviewed_by=claim_row.get("reviewed_by"),
            reviewed_at=claim_row.get("reviewed_at"),
            rejection_reason=claim_row.get("rejection_reason"),
            created_at=claim_row["created_at"],
            updated_at=claim_row["updated_at"],
        )
    else:
        claim = None
    
    return ClaimStatusResponse(
        claim=claim,
        is_claimed=is_claimed,
        can_claim=can_claim,
    )


@router.get("/my-claims", response_model=List[AuthenticatedClaimResponse])
async def list_my_claims(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$", description="Filter by status"),
    user: User = Depends(get_current_user),
):
    """
    List all location claims for the authenticated user.
    """
    # Build query with optional status filter
    conditions = ["alc.user_id = $1"]
    params = [user.user_id]
    
    if status:
        conditions.append("alc.status = $2")
        params.append(status)
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            alc.id, alc.location_id, alc.user_id, alc.status,
            alc.google_business_link, alc.logo_url, alc.submitted_at,
            alc.reviewed_by, alc.reviewed_at, alc.rejection_reason,
            alc.created_at, alc.updated_at,
            l.name as location_name
        FROM authenticated_location_claims alc
        JOIN locations l ON l.id = alc.location_id
        WHERE {where_clause}
        ORDER BY alc.created_at DESC
    """
    
    rows = await fetch(sql, *params)
    
    return [
        AuthenticatedClaimResponse(
            id=row["id"],
            location_id=row["location_id"],
            location_name=row.get("location_name"),
            user_id=row["user_id"],
            status=row["status"],
            google_business_link=row.get("google_business_link"),
            logo_url=row.get("logo_url"),
            submitted_at=row["submitted_at"],
            reviewed_by=row.get("reviewed_by"),
            reviewed_at=row.get("reviewed_at"),
            rejection_reason=row.get("rejection_reason"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.get("/my-locations", response_model=List[dict])
async def list_my_locations(
    user: User = Depends(get_current_user),
):
    """
    List all locations owned by the authenticated user (from location_owners table).
    Returns location details including name, category, and claim date.
    """
    sql = """
        SELECT 
            lo.location_id,
            lo.claimed_at,
            lo.google_business_link,
            lo.logo_url,
            l.name as location_name,
            l.category,
            l.address,
            l.lat,
            l.lng
        FROM location_owners lo
        JOIN locations l ON l.id = lo.location_id
        WHERE lo.user_id = $1
        ORDER BY lo.claimed_at DESC
    """
    
    rows = await fetch(sql, user.user_id)
    
    return [
        {
            "location_id": row["location_id"],
            "location_name": row.get("location_name"),
            "category": row.get("category"),
            "address": row.get("address"),
            "lat": float(row["lat"]) if row.get("lat") else None,
            "lng": float(row["lng"]) if row.get("lng") else None,
            "claimed_at": row["claimed_at"].isoformat() if row.get("claimed_at") else None,
            "google_business_link": row.get("google_business_link"),
            "logo_url": row.get("logo_url"),
        }
        for row in rows
    ]


@router.post("/{location_id}/claim/logo", response_model=dict)
async def upload_claim_logo(
    location_id: int = Path(..., description="Location ID to claim"),
    logo: UploadFile = File(..., description="Logo image file"),
    user: User = Depends(get_current_user),
):
    """
    Upload a logo for a location claim.
    The logo is stored temporarily until the claim is approved/rejected.
    
    Returns:
        dict with logo_url and storage_path
    """
    # Verify location exists
    location_sql = """
        SELECT id, name FROM locations WHERE id = $1
    """
    location_rows = await fetch(location_sql, location_id)
    
    if not location_rows:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Check if user has a pending claim for this location
    claim_sql = """
        SELECT id, status FROM authenticated_location_claims
        WHERE location_id = $1 AND user_id = $2
        ORDER BY created_at DESC
        LIMIT 1
    """
    claim_rows = await fetch(claim_sql, location_id, user.user_id)
    
    if not claim_rows:
        raise HTTPException(
            status_code=404,
            detail="No claim found for this location. Please submit a claim first."
        )
    
    claim = claim_rows[0]
    
    if claim["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot upload logo for claim with status: {claim['status']}"
        )
    
    # Read file content
    try:
        file_content = await logo.read()
    except Exception as e:
        logger.error("logo_upload_read_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to read uploaded file")
    
    # Upload to temp storage
    try:
        storage_path = await upload_logo_to_temp(
            claim_id=claim["id"],
            file_content=file_content,
            filename=logo.filename or "logo",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("logo_upload_failed", error=str(e), claim_id=claim["id"])
        raise HTTPException(status_code=500, detail="Failed to upload logo")
    
    # Generate public URL
    logo_url = get_public_url(storage_path)
    
    # Update claim with logo storage path and URL
    update_sql = """
        UPDATE authenticated_location_claims
        SET logo_storage_path = $1,
            logo_url = $2,
            updated_at = now()
        WHERE id = $3
        RETURNING id, logo_url, logo_storage_path
    """
    
    update_result = await fetch(update_sql, storage_path, logo_url, claim["id"])
    
    if not update_result:
        raise HTTPException(status_code=500, detail="Failed to update claim with logo")
    
    logger.info(
        "claim_logo_uploaded",
        claim_id=claim["id"],
        location_id=location_id,
        user_id=str(user.user_id),
        storage_path=storage_path,
    )
    
    return {
        "logo_url": logo_url,
        "storage_path": storage_path,
        "claim_id": claim["id"],
    }

