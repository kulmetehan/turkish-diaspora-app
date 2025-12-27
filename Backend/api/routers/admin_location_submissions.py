"""
Admin endpoints for location submissions.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from typing import List, Optional
from uuid import UUID

from app.deps.admin_auth import verify_admin_user, AdminUser
from app.models.location_submission import LocationSubmissionResponse
from services.db_service import fetch, fetchrow
from services.location_submission_approval_service import (
    approve_submission,
    reject_submission,
)
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/admin/location-submissions", tags=["admin-location-submissions"])


@router.get("", response_model=List[LocationSubmissionResponse])
async def list_submissions(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$", description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    List all location submissions (admin only).
    """
    conditions = []
    params = []
    param_num = 1
    
    if status:
        conditions.append(f"status = ${param_num}")
        params.append(status)
        param_num += 1
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # Add limit and offset parameters
    limit_param = param_num
    offset_param = param_num + 1
    params.append(limit)
    params.append(offset)
    
    sql = f"""
        SELECT 
            id, name, address, lat, lng, category, user_id, is_owner,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_location_id, created_at, updated_at
        FROM user_submitted_locations
        {where_clause}
        ORDER BY submitted_at DESC
        LIMIT ${limit_param} OFFSET ${offset_param}
    """
    
    rows = await fetch(sql, *params)
    
    return [
        LocationSubmissionResponse(
            id=row["id"],
            name=row["name"],
            address=row.get("address"),
            lat=float(row["lat"]),
            lng=float(row["lng"]),
            category=row["category"],
            user_id=row["user_id"],
            is_owner=row["is_owner"],
            status=row["status"],
            submitted_at=row["submitted_at"],
            reviewed_by=row.get("reviewed_by"),
            reviewed_at=row.get("reviewed_at"),
            rejection_reason=row.get("rejection_reason"),
            created_location_id=row.get("created_location_id"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.get("/{submission_id}", response_model=LocationSubmissionResponse)
async def get_submission(
    submission_id: int = Path(..., description="Submission ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Get submission details (admin only).
    """
    sql = """
        SELECT 
            id, name, address, lat, lng, category, user_id, is_owner,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_location_id, created_at, updated_at
        FROM user_submitted_locations
        WHERE id = $1
    """
    
    row = await fetchrow(sql, submission_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return LocationSubmissionResponse(
        id=row["id"],
        name=row["name"],
        address=row.get("address"),
        lat=float(row["lat"]),
        lng=float(row["lng"]),
        category=row["category"],
        user_id=row["user_id"],
        is_owner=row["is_owner"],
        status=row["status"],
        submitted_at=row["submitted_at"],
        reviewed_by=row.get("reviewed_by"),
        reviewed_at=row.get("reviewed_at"),
        rejection_reason=row.get("rejection_reason"),
        created_location_id=row.get("created_location_id"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/{submission_id}/approve")
async def approve_submission_endpoint(
    submission_id: int = Path(..., description="Submission ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Approve submission and create location (admin only).
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
        result = await approve_submission(
            submission_id=submission_id,
            admin_user_id=admin_user_id,
        )
        
        logger.info(
            "admin_approved_location_submission",
            submission_id=submission_id,
            admin_email=admin.email,
            location_id=result.get("location_id"),
        )
        
        return {
            "ok": True,
            "message": "Submission approved and location created",
            "submission_id": submission_id,
            "location_id": result.get("location_id"),
            "is_owner": result.get("is_owner"),
            "owner_entry_created": result.get("owner_entry_created"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "admin_approve_submission_failed",
            submission_id=submission_id,
            admin_email=admin.email,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to approve submission: {str(e)}")


@router.post("/{submission_id}/reject")
async def reject_submission_endpoint(
    submission_id: int = Path(..., description="Submission ID"),
    rejection_reason: Optional[str] = Body(None, embed=True, description="Optional reason for rejection"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Reject submission (admin only).
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
        result = await reject_submission(
            submission_id=submission_id,
            admin_user_id=admin_user_id,
            rejection_reason=rejection_reason,
        )
        
        logger.info(
            "admin_rejected_location_submission",
            submission_id=submission_id,
            admin_email=admin.email,
            rejection_reason=rejection_reason,
        )
        
        return {
            "ok": True,
            "message": "Submission rejected",
            "submission_id": submission_id,
            "rejection_reason": rejection_reason,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "admin_reject_submission_failed",
            submission_id=submission_id,
            admin_email=admin.email,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to reject submission: {str(e)}")

