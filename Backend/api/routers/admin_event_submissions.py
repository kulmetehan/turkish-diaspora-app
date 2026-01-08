"""
Admin endpoints for event submissions.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from typing import List, Optional
from uuid import UUID

from app.deps.admin_auth import verify_admin_user, AdminUser
from app.models.event_submission import EventSubmissionResponse
from services.db_service import fetch, fetchrow
from services.event_submission_approval_service import (
    approve_submission,
    reject_submission,
    unpublish_submission,
)
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/admin/event-submissions", tags=["admin-event-submissions"])


@router.get("", response_model=List[EventSubmissionResponse])
async def list_submissions(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$", description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    List all event submissions (admin only).
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
            id, title, description, start_time_utc, end_time_utc, location_text,
            lat, lng, url, category_key, user_id,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_event_id, created_at, updated_at
        FROM user_submitted_events
        {where_clause}
        ORDER BY submitted_at DESC
        LIMIT ${limit_param} OFFSET ${offset_param}
    """
    
    rows = await fetch(sql, *params)
    
    return [
        EventSubmissionResponse(
            id=row["id"],
            title=row["title"],
            description=row.get("description"),
            start_time_utc=row["start_time_utc"],
            end_time_utc=row.get("end_time_utc"),
            location_text=row.get("location_text"),
            lat=float(row["lat"]) if row.get("lat") is not None else None,
            lng=float(row["lng"]) if row.get("lng") is not None else None,
            url=row.get("url"),
            category_key=row.get("category_key"),
            user_id=row["user_id"],
            status=row["status"],
            submitted_at=row["submitted_at"],
            reviewed_by=row.get("reviewed_by"),
            reviewed_at=row.get("reviewed_at"),
            rejection_reason=row.get("rejection_reason"),
            created_event_id=row.get("created_event_id"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.get("/{submission_id}", response_model=EventSubmissionResponse)
async def get_submission(
    submission_id: int = Path(..., description="Submission ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Get submission details (admin only).
    """
    sql = """
        SELECT 
            id, title, description, start_time_utc, end_time_utc, location_text,
            lat, lng, url, category_key, user_id,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_event_id, created_at, updated_at
        FROM user_submitted_events
        WHERE id = $1
    """
    
    row = await fetchrow(sql, submission_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return EventSubmissionResponse(
        id=row["id"],
        title=row["title"],
        description=row.get("description"),
        start_time_utc=row["start_time_utc"],
        end_time_utc=row.get("end_time_utc"),
        location_text=row.get("location_text"),
        lat=float(row["lat"]) if row.get("lat") is not None else None,
        lng=float(row["lng"]) if row.get("lng") is not None else None,
        url=row.get("url"),
        category_key=row.get("category_key"),
        user_id=row["user_id"],
        status=row["status"],
        submitted_at=row["submitted_at"],
        reviewed_by=row.get("reviewed_by"),
        reviewed_at=row.get("reviewed_at"),
        rejection_reason=row.get("rejection_reason"),
        created_event_id=row.get("created_event_id"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/{submission_id}/approve")
async def approve_submission_endpoint(
    submission_id: int = Path(..., description="Submission ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Approve submission and create event via event_raw pipeline (admin only).
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
            "admin_approved_event_submission",
            submission_id=submission_id,
            admin_email=admin.email,
            event_raw_id=result.get("event_raw_id"),
        )
        
        return {
            "ok": True,
            "message": "Submission approved and event_raw created",
            "submission_id": submission_id,
            "event_raw_id": result.get("event_raw_id"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "admin_approve_event_submission_failed",
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
            "admin_rejected_event_submission",
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
            "admin_reject_event_submission_failed",
            submission_id=submission_id,
            admin_email=admin.email,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to reject submission: {str(e)}")


@router.post("/{submission_id}/unpublish")
async def unpublish_submission_endpoint(
    submission_id: int = Path(..., description="Submission ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Unpublish/remove an approved event submission (admin only).
    This sets the event_candidate state to 'rejected' so it no longer appears on the frontend.
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
        result = await unpublish_submission(
            submission_id=submission_id,
            admin_user_id=admin_user_id,
        )
        
        logger.info(
            "admin_unpublished_event_submission",
            submission_id=submission_id,
            admin_email=admin.email,
            event_candidate_id=result.get("event_candidate_id"),
        )
        
        return {
            "ok": True,
            "message": "Event unpublished and removed from frontend",
            "submission_id": submission_id,
            "event_candidate_id": result.get("event_candidate_id"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "admin_unpublish_event_submission_failed",
            submission_id=submission_id,
            admin_email=admin.email,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to unpublish submission: {str(e)}")

