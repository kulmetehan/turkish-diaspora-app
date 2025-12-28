from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from app.core.client_id import get_client_id
from app.deps.auth import get_current_user_optional, User
from app.deps.admin_auth import verify_admin_user, AdminUser
from services.db_service import fetch, execute, update_location_classification
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportCreate(BaseModel):
    report_type: str = Field(..., pattern="^(location|note|reaction|user|check_in|prikbord_post|poll)$")
    target_id: int = Field(..., gt=0)
    reason: str = Field(..., min_length=3, max_length=100)
    details: Optional[str] = Field(None, max_length=1000)


class ReportResponse(BaseModel):
    id: int
    report_type: str
    target_id: int
    reason: str
    details: Optional[str]
    status: str
    created_at: datetime
    location_name: Optional[str] = None  # Only populated for location reports


class ReportUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|resolved|dismissed)$")
    resolution_notes: Optional[str] = Field(None, max_length=1000)


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(
    request: Request,
    report: ReportCreate,
    user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Submit a report on content or a user.
    Requires either authenticated user or client_id header.
    """
    # Get client_id from header if not authenticated
    if not user:
        client_id = await get_client_id(request)
        if not client_id:
            raise HTTPException(
                status_code=400,
                detail="Either authentication or X-Client-Id header is required"
            )
    
    # Validate report_type
    if report.report_type not in ("location", "note", "reaction", "user", "check_in", "prikbord_post", "poll"):
        raise HTTPException(
            status_code=400,
            detail="report_type must be one of: location, note, reaction, user, check_in, prikbord_post, poll"
        )
    
    # Check if duplicate report exists (same reporter, type, target in last 24h)
    duplicate_sql = """
        SELECT id FROM reports
        WHERE report_type = $1 
          AND target_id = $2
          AND status = 'pending'
          AND (
            ($3::uuid IS NOT NULL AND reported_by_user_id = $3) OR
            ($4::text IS NOT NULL AND reported_by_client_id = $4)
          )
          AND created_at > now() - INTERVAL '24 hours'
        LIMIT 1
    """
    duplicate_rows = await fetch(
        duplicate_sql,
        report.report_type,
        report.target_id,
        user.user_id if user else None,
        client_id,
    )
    
    if duplicate_rows:
        raise HTTPException(
            status_code=409,
            detail="A similar report was already submitted recently"
        )
    
    # Insert report
    insert_sql = """
        INSERT INTO reports (
            reported_by_user_id,
            reported_by_client_id,
            report_type,
            target_id,
            reason,
            details,
            status,
            created_at,
            updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, 'pending', now(), now())
        RETURNING id, report_type, target_id, reason, details, status, created_at
    """
    result = await fetch(
        insert_sql,
        user.user_id if user else None,
        client_id,
        report.report_type,
        report.target_id,
        report.reason,
        report.details,
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create report")
    
    row = result[0]
    logger.info(
        "report_created",
        report_id=row["id"],
        report_type=report.report_type,
        target_id=report.target_id,
        user_id=str(user.user_id) if user else None,
        client_id=client_id,
    )
    
    return ReportResponse(**row)


@router.get("/admin", response_model=List[ReportResponse])
async def list_reports(
    status: Optional[str] = Query(None, pattern="^(pending|resolved|dismissed)$"),
    report_type: Optional[str] = Query(None, pattern="^(location|note|reaction|user)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    List all reports (admin only).
    Can filter by status and report_type.
    """
    conditions = []
    params = []
    param_num = 1
    
    if status:
        conditions.append(f"status = ${param_num}")
        params.append(status)
        param_num += 1
    
    if report_type:
        conditions.append(f"report_type = ${param_num}")
        params.append(report_type)
        param_num += 1
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    params.append(limit)
    params.append(offset)
    
    sql = f"""
        SELECT 
            r.id, 
            r.report_type, 
            r.target_id, 
            r.reason, 
            r.details, 
            r.status, 
            r.created_at,
            l.name AS location_name
        FROM reports r
        LEFT JOIN locations l ON r.report_type = 'location' AND r.target_id = l.id
        {where_clause}
        ORDER BY r.created_at DESC
        LIMIT ${param_num} OFFSET ${param_num + 1}
    """
    
    rows = await fetch(sql, *params)
    return [ReportResponse(**row) for row in rows]


@router.put("/admin/{report_id}", response_model=ReportResponse)
async def update_report_status(
    report_id: int = Path(..., description="Report ID"),
    update: ReportUpdate = ...,
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Update report status (admin only).
    """
    # Get admin user_id (for now using email, need to get user_id from auth.users)
    # TODO: Enhance AdminUser to include user_id when available
    
    # Update report
    update_sql = """
        UPDATE reports
        SET status = $1::report_status,
            resolution_notes = $2,
            resolved_by = (SELECT id FROM auth.users WHERE email = $3 LIMIT 1),
            resolved_at = CASE WHEN $1::report_status != 'pending' THEN now() ELSE resolved_at END,
            updated_at = now()
        WHERE id = $4
        RETURNING 
            id, 
            report_type, 
            target_id, 
            reason, 
            details, 
            status, 
            created_at,
            (SELECT name FROM locations WHERE id = reports.target_id AND reports.report_type = 'location') AS location_name
    """
    
    result = await fetch(
        update_sql,
        update.status,
        update.resolution_notes,
        admin.email,
        report_id,
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    
    row = result[0]
    logger.info(
        "report_updated",
        report_id=report_id,
        new_status=update.status,
        admin_email=admin.email,
    )
    
    return ReportResponse(**row)


@router.post("/admin/{report_id}/remove-content")
async def remove_reported_content(
    report_id: int = Path(..., description="Report ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Remove the content that was reported (admin moderation action).
    Works for notes, reactions, check-ins, polls, and prikbord posts.
    After removal, marks report as resolved.
    """
    # Get report details
    report_sql = """
        SELECT report_type, target_id, status
        FROM reports
        WHERE id = $1
    """
    report_rows = await fetch(report_sql, report_id)
    
    if not report_rows:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = report_rows[0]
    report_type = report["report_type"]
    target_id = report["target_id"]
    
    if report_type not in ("note", "reaction", "check_in", "poll", "prikbord_post"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot remove content for report_type: {report_type}. Supported types: note, reaction, check_in, poll, prikbord_post"
        )
    
    removed = False
    
    if report_type == "note":
        # Delete note by ID (target_id should be note_id from activity_stream or location_notes.id)
        delete_sql = """
            DELETE FROM location_notes
            WHERE id = $1
            RETURNING id
        """
        result = await fetch(delete_sql, target_id)
        removed = len(result) > 0
        
    elif report_type == "reaction":
        # For reactions, target_id might be activity_stream.id
        # We need to map back to location_reactions.id
        # For now, we'll try direct lookup - this might need improvement
        # TODO: Improve this mapping when we store reaction_id in activity_stream payload
        delete_sql = """
            DELETE FROM location_reactions
            WHERE id = $1
            RETURNING id
        """
        result = await fetch(delete_sql, target_id)
        removed = len(result) > 0
        
        if not removed:
            logger.warning(
                "reaction_removal_failed",
                report_id=report_id,
                target_id=target_id,
                message="Could not find reaction with this ID. May need activity_stream mapping."
            )
    
    elif report_type == "check_in":
        # Delete check-in by ID
        delete_sql = """
            DELETE FROM check_ins
            WHERE id = $1
            RETURNING id
        """
        result = await fetch(delete_sql, target_id)
        removed = len(result) > 0
        
    elif report_type == "poll":
        # Soft delete poll by setting status to 'removed'
        delete_sql = """
            UPDATE polls
            SET status = 'removed', updated_at = now()
            WHERE id = $1
            RETURNING id
        """
        result = await fetch(delete_sql, target_id)
        removed = len(result) > 0
        
    elif report_type == "prikbord_post":
        # Soft delete shared link by setting status to 'removed'
        delete_sql = """
            UPDATE shared_links
            SET status = 'removed', updated_at = now()
            WHERE id = $1
            RETURNING id
        """
        result = await fetch(delete_sql, target_id)
        removed = len(result) > 0
    
    if removed:
        # Mark report as resolved
        update_sql = """
            UPDATE reports
            SET status = 'resolved',
                resolution_notes = 'Content removed by admin moderation',
                resolved_by = (SELECT id FROM auth.users WHERE email = $1 LIMIT 1),
                resolved_at = now(),
                updated_at = now()
            WHERE id = $2
            RETURNING id, report_type, target_id, reason, details, status, created_at
        """
        result = await fetch(update_sql, admin.email, report_id)
        
        logger.info(
            "content_removed_by_moderation",
            report_id=report_id,
            report_type=report_type,
            target_id=target_id,
            admin_email=admin.email,
        )
        
        if result:
            return {
                "ok": True,
                "removed": True,
                "report": ReportResponse(**result[0])
            }
    else:
        logger.warning(
            "content_removal_failed",
            report_id=report_id,
            report_type=report_type,
            target_id=target_id,
        )
        raise HTTPException(
            status_code=404,
            detail=f"Could not find {report_type} with id {target_id} to remove"
        )
    
    raise HTTPException(status_code=500, detail="Failed to remove content")


@router.post("/admin/{report_id}/retire-location")
async def retire_reported_location(
    report_id: int = Path(..., description="Report ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Retire the location that was reported (admin moderation action).
    Works for location reports only.
    Sets location state to RETIRED and marks report as resolved.
    """
    # Get report details
    report_sql = """
        SELECT report_type, target_id, status, reason, details
        FROM reports
        WHERE id = $1
    """
    report_rows = await fetch(report_sql, report_id)
    
    if not report_rows:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = report_rows[0]
    report_type = report["report_type"]
    target_id = report["target_id"]
    
    if report_type != "location":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retire content for report_type: {report_type}. Only 'location' is supported."
        )
    
    # Check if location exists
    location_sql = """
        SELECT id, state, name
        FROM locations
        WHERE id = $1
    """
    location_rows = await fetch(location_sql, target_id)
    
    if not location_rows:
        raise HTTPException(
            status_code=404,
            detail=f"Location with id {target_id} not found"
        )
    
    location = location_rows[0]
    current_state = location.get("state", "").upper()
    
    # Build reason text for notes
    reason_text = f"Retired via report #{report_id}: {report.get('reason', 'N/A')}"
    if report.get("details"):
        reason_text += f" - {report['details']}"
    
    # Retire the location directly (bypass no-downgrade rule for admin actions)
    # For VERIFIED locations, we need to force retirement by directly updating state
    try:
        if current_state == "VERIFIED":
            # Direct state update for VERIFIED locations (admin override)
            await execute(
                """
                UPDATE locations
                SET state = 'RETIRED',
                    is_retired = true,
                    last_verified_at = NOW(),
                    notes = COALESCE(notes, '') || CASE WHEN notes IS NULL OR notes = '' THEN '' ELSE E'\\n' END || $1
                WHERE id = $2
                """,
                reason_text,
                target_id,
            )
        else:
            # Use canonical function for non-VERIFIED locations
            await update_location_classification(
                id=target_id,
                action="ignore",  # This will set state to RETIRED
                category=None,  # Preserve existing category
                confidence_score=0.0,  # Not relevant for retirement
                reason=reason_text,
                allow_resurrection=False,
            )
        
        # Mark report as resolved
        update_sql = """
            UPDATE reports
            SET status = 'resolved',
                resolution_notes = 'Location retired by admin moderation',
                resolved_by = (SELECT id FROM auth.users WHERE email = $1 LIMIT 1),
                resolved_at = now(),
                updated_at = now()
            WHERE id = $2
            RETURNING id, report_type, target_id, reason, details, status, created_at
        """
        result = await fetch(update_sql, admin.email, report_id)
        
        logger.info(
            "location_retired_by_moderation",
            report_id=report_id,
            location_id=target_id,
            location_name=location.get("name"),
            previous_state=current_state,
            admin_email=admin.email,
        )
        
        if result:
            return {
                "ok": True,
                "retired": True,
                "report": ReportResponse(**result[0])
            }
    except Exception as e:
        logger.error(
            "location_retirement_failed",
            report_id=report_id,
            location_id=target_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retire location: {str(e)}"
        )
    
    raise HTTPException(status_code=500, detail="Failed to retire location")

