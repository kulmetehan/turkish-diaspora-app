from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from app.deps.admin_auth import verify_admin_user, AdminUser
from services.db_service import fetch, execute
from services.claim_approval_service import approve_claim, reject_claim
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/admin/authenticated-claims", tags=["admin-authenticated-claims"])


class AuthenticatedClaimResponse(BaseModel):
    id: int
    location_id: int
    location_name: Optional[str]
    user_id: UUID
    user_name: Optional[str]
    user_email: Optional[str]
    status: str  # 'pending', 'approved', 'rejected'
    google_business_link: Optional[str]
    logo_url: Optional[str]
    logo_storage_path: Optional[str]
    submitted_at: datetime
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime


class ClaimApproveRequest(BaseModel):
    pass  # No additional fields needed for approval


class ClaimRejectRequest(BaseModel):
    rejection_reason: Optional[str] = Field(None, description="Optional reason for rejection")


@router.get("", response_model=List[AuthenticatedClaimResponse])
async def list_all_authenticated_claims(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$", description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    List all authenticated location claims (admin only).
    """
    conditions = []
    params = []
    param_num = 1
    
    if status:
        conditions.append(f"alc.status = ${param_num}")
        params.append(status)
        param_num += 1
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    params.append(limit)
    params.append(offset)
    
    sql = f"""
        SELECT 
            alc.id, alc.location_id, alc.user_id, alc.status,
            alc.google_business_link, alc.logo_url, alc.logo_storage_path,
            alc.submitted_at, alc.reviewed_by, alc.reviewed_at,
            alc.rejection_reason, alc.created_at, alc.updated_at,
            l.name as location_name,
            u.raw_user_meta_data->>'name' as user_name,
            u.email as user_email
        FROM authenticated_location_claims alc
        JOIN locations l ON l.id = alc.location_id
        LEFT JOIN auth.users u ON u.id = alc.user_id
        {where_clause}
        ORDER BY alc.created_at DESC
        LIMIT ${param_num} OFFSET ${param_num + 1}
    """
    
    rows = await fetch(sql, *params)
    
    return [
        AuthenticatedClaimResponse(
            id=row["id"],
            location_id=row["location_id"],
            location_name=row.get("location_name"),
            user_id=row["user_id"],
            user_name=row.get("user_name"),
            user_email=row.get("user_email"),
            status=row["status"],
            google_business_link=row.get("google_business_link"),
            logo_url=row.get("logo_url"),
            logo_storage_path=row.get("logo_storage_path"),
            submitted_at=row["submitted_at"],
            reviewed_by=row.get("reviewed_by"),
            reviewed_at=row.get("reviewed_at"),
            rejection_reason=row.get("rejection_reason"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.get("/{claim_id}", response_model=AuthenticatedClaimResponse)
async def get_authenticated_claim(
    claim_id: int = Path(..., description="Claim ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Get a specific authenticated location claim by ID (admin only).
    """
    sql = """
        SELECT 
            alc.id, alc.location_id, alc.user_id, alc.status,
            alc.google_business_link, alc.logo_url, alc.logo_storage_path,
            alc.submitted_at, alc.reviewed_by, alc.reviewed_at,
            alc.rejection_reason, alc.created_at, alc.updated_at,
            l.name as location_name,
            u.raw_user_meta_data->>'name' as user_name,
            u.email as user_email
        FROM authenticated_location_claims alc
        JOIN locations l ON l.id = alc.location_id
        LEFT JOIN auth.users u ON u.id = alc.user_id
        WHERE alc.id = $1
    """
    
    rows = await fetch(sql, claim_id)
    
    if not rows:
        raise HTTPException(status_code=404, detail="Authenticated location claim not found")
    
    row = rows[0]
    
    return AuthenticatedClaimResponse(
        id=row["id"],
        location_id=row["location_id"],
        location_name=row.get("location_name"),
        user_id=row["user_id"],
        user_name=row.get("user_name"),
        user_email=row.get("user_email"),
        status=row["status"],
        google_business_link=row.get("google_business_link"),
        logo_url=row.get("logo_url"),
        logo_storage_path=row.get("logo_storage_path"),
        submitted_at=row["submitted_at"],
        reviewed_by=row.get("reviewed_by"),
        reviewed_at=row.get("reviewed_at"),
        rejection_reason=row.get("rejection_reason"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.put("/{claim_id}/approve", response_model=AuthenticatedClaimResponse)
async def approve_authenticated_claim(
    claim_id: int = Path(..., description="Claim ID"),
    request: ClaimApproveRequest = ...,
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Approve an authenticated location claim (admin only).
    This will:
    1. Update claim status to 'approved'
    2. Create entry in location_owners table
    3. Copy google_business_link and logo_storage_path to location_owners
    4. Update user role to location_owner (if role system exists)
    """
    # Get admin user_id from email
    admin_user_sql = """
        SELECT id FROM auth.users WHERE email = $1 LIMIT 1
    """
    admin_user_rows = await fetch(admin_user_sql, admin.email)
    
    if not admin_user_rows:
        raise HTTPException(status_code=500, detail="Admin user not found")
    
    admin_user_id = admin_user_rows[0]["id"]
    
    try:
        # Use approval service
        result = await approve_claim(claim_id, admin_user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "claim_approval_failed",
            claim_id=claim_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to approve claim: {str(e)}")
    
    # Get full claim details for response
    full_claim_sql = """
        SELECT 
            alc.id, alc.location_id, alc.user_id, alc.status,
            alc.google_business_link, alc.logo_url, alc.logo_storage_path,
            alc.submitted_at, alc.reviewed_by, alc.reviewed_at,
            alc.rejection_reason, alc.created_at, alc.updated_at,
            l.name as location_name,
            u.raw_user_meta_data->>'name' as user_name,
            u.email as user_email
        FROM authenticated_location_claims alc
        JOIN locations l ON l.id = alc.location_id
        LEFT JOIN auth.users u ON u.id = alc.user_id
        WHERE alc.id = $1
    """
    
    full_rows = await fetch(full_claim_sql, claim_id)
    full_row = full_rows[0] if full_rows else {}
    
    return AuthenticatedClaimResponse(
        id=full_row["id"],
        location_id=full_row["location_id"],
        location_name=full_row.get("location_name"),
        user_id=full_row["user_id"],
        user_name=full_row.get("user_name"),
        user_email=full_row.get("user_email"),
        status=full_row["status"],
        google_business_link=full_row.get("google_business_link"),
        logo_url=full_row.get("logo_url"),
        logo_storage_path=full_row.get("logo_storage_path"),
        submitted_at=full_row["submitted_at"],
        reviewed_by=full_row.get("reviewed_by"),
        reviewed_at=full_row.get("reviewed_at"),
        rejection_reason=full_row.get("rejection_reason"),
        created_at=full_row["created_at"],
        updated_at=full_row["updated_at"],
    )


@router.put("/{claim_id}/reject", response_model=AuthenticatedClaimResponse)
async def reject_authenticated_claim(
    claim_id: int = Path(..., description="Claim ID"),
    request: ClaimRejectRequest = ...,
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Reject an authenticated location claim (admin only).
    """
    # Get admin user_id from email
    admin_user_sql = """
        SELECT id FROM auth.users WHERE email = $1 LIMIT 1
    """
    admin_user_rows = await fetch(admin_user_sql, admin.email)
    
    if not admin_user_rows:
        raise HTTPException(status_code=500, detail="Admin user not found")
    
    admin_user_id = admin_user_rows[0]["id"]
    
    try:
        # Use rejection service
        result = await reject_claim(claim_id, admin_user_id, request.rejection_reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "claim_rejection_failed",
            claim_id=claim_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to reject claim: {str(e)}")
    
    # Get full claim details for response
    full_claim_sql = """
        SELECT 
            alc.id, alc.location_id, alc.user_id, alc.status,
            alc.google_business_link, alc.logo_url, alc.logo_storage_path,
            alc.submitted_at, alc.reviewed_by, alc.reviewed_at,
            alc.rejection_reason, alc.created_at, alc.updated_at,
            l.name as location_name,
            u.raw_user_meta_data->>'name' as user_name,
            u.email as user_email
        FROM authenticated_location_claims alc
        JOIN locations l ON l.id = alc.location_id
        LEFT JOIN auth.users u ON u.id = alc.user_id
        WHERE alc.id = $1
    """
    
    full_rows = await fetch(full_claim_sql, claim_id)
    full_row = full_rows[0] if full_rows else {}
    
    return AuthenticatedClaimResponse(
        id=full_row["id"],
        location_id=full_row["location_id"],
        location_name=full_row.get("location_name"),
        user_id=full_row["user_id"],
        user_name=full_row.get("user_name"),
        user_email=full_row.get("user_email"),
        status=full_row["status"],
        google_business_link=full_row.get("google_business_link"),
        logo_url=full_row.get("logo_url"),
        logo_storage_path=full_row.get("logo_storage_path"),
        submitted_at=full_row["submitted_at"],
        reviewed_by=full_row.get("reviewed_by"),
        reviewed_at=full_row.get("reviewed_at"),
        rejection_reason=full_row.get("rejection_reason"),
        created_at=full_row["created_at"],
        updated_at=full_row["updated_at"],
    )

