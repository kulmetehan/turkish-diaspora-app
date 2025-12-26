from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.deps.admin_auth import verify_admin_user, AdminUser
from services.db_service import fetch, fetchrow
from services.outreach_mailer_service import send_queued_emails
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/admin/outreach/emails", tags=["admin-outreach-emails"])


class QueueEmailRequest(BaseModel):
    location_id: int = Field(..., description="Location ID to queue email for")


class QueueEmailResponse(BaseModel):
    success: bool
    message: str
    email_id: Optional[int] = None


@router.post("/queue", response_model=QueueEmailResponse)
async def queue_email_for_location(
    request: QueueEmailRequest,
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Manually queue an outreach email for a specific location (admin only).
    
    This will:
    1. Check if location is eligible (VERIFIED, not claimed, has contact)
    2. Create outreach_emails entry with status 'queued'
    3. Return success or error message
    """
    location_id = request.location_id
    
    # Verify location exists and is eligible
    location_row = await fetchrow(
        """
        SELECT 
            l.id, l.name, l.state,
            oc.id as contact_id, oc.email
        FROM locations l
        INNER JOIN outreach_contacts oc ON l.id = oc.location_id
        LEFT JOIN authenticated_location_claims alc ON l.id = alc.location_id AND alc.status = 'approved'
        LEFT JOIN location_owners lo ON l.id = lo.location_id
        LEFT JOIN outreach_emails oe ON l.id = oe.location_id 
            AND oe.status IN ('sent', 'delivered', 'clicked')
        WHERE l.id = $1
        """,
        location_id,
    )
    
    if not location_row:
        raise HTTPException(
            status_code=404, 
            detail="Location not found or no contact available"
        )
    
    if location_row["state"] != "VERIFIED":
        raise HTTPException(
            status_code=400,
            detail=f"Location is not VERIFIED (current state: {location_row['state']})"
        )
    
    if location_row.get("contact_id") is None:
        raise HTTPException(
            status_code=400,
            detail="Location has no contact information"
        )
    
    # Check if email already sent
    existing_email = await fetchrow(
        """
        SELECT id, status FROM outreach_emails
        WHERE location_id = $1 AND status IN ('sent', 'delivered', 'clicked')
        LIMIT 1
        """,
        location_id,
    )
    
    if existing_email:
        raise HTTPException(
            status_code=409,
            detail=f"Email already sent for this location (status: {existing_email['status']})"
        )
    
    # Check if already queued
    queued_email = await fetchrow(
        """
        SELECT id FROM outreach_emails
        WHERE location_id = $1 AND status = 'queued'
        LIMIT 1
        """,
        location_id,
    )
    
    if queued_email:
        return QueueEmailResponse(
            success=True,
            message="Email already queued for this location",
            email_id=queued_email["id"],
        )
    
    # Create queue entry
    try:
        from services.db_service import execute
        
        result = await fetchrow(
            """
            INSERT INTO outreach_emails (
                location_id,
                contact_id,
                email,
                status
            )
            VALUES ($1, $2, $3, 'queued')
            RETURNING id
            """,
            location_id,
            location_row["contact_id"],
            location_row["email"],
        )
        
        logger.info(
            "admin_email_queued",
            admin_email=admin.email,
            location_id=location_id,
            email_id=result["id"],
        )
        
        return QueueEmailResponse(
            success=True,
            message=f"Email queued successfully for {location_row.get('name', 'location')}",
            email_id=result["id"],
        )
        
    except Exception as e:
        logger.error(
            "admin_email_queue_error",
            admin_email=admin.email,
            location_id=location_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue email: {str(e)}"
        )


@router.post("/send")
async def send_queued_emails_admin(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of emails to send"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Manually trigger sending of queued outreach emails (admin only).
    
    This calls the outreach_mailer_service to send queued emails.
    """
    try:
        result = await send_queued_emails(limit=limit)
        
        logger.info(
            "admin_emails_sent",
            admin_email=admin.email,
            sent=result.get("sent", 0),
            failed=result.get("failed", 0),
        )
        
        return {
            "success": True,
            "sent": result.get("sent", 0),
            "failed": result.get("failed", 0),
            "errors": result.get("errors", []),
        }
        
    except Exception as e:
        logger.error(
            "admin_send_emails_error",
            admin_email=admin.email,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send emails: {str(e)}"
        )


class OutreachEmailResponse(BaseModel):
    id: int
    location_id: int
    location_name: Optional[str]
    email: str
    status: str
    ses_message_id: Optional[str]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    clicked_at: Optional[datetime]
    bounced_at: Optional[datetime]
    bounce_reason: Optional[str]
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=List[OutreachEmailResponse])
async def list_outreach_emails(
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    List outreach emails (admin only).
    """
    conditions = []
    params = []
    param_num = 1
    
    if location_id:
        conditions.append(f"oe.location_id = ${param_num}")
        params.append(location_id)
        param_num += 1
    
    if status:
        conditions.append(f"oe.status = ${param_num}")
        params.append(status)
        param_num += 1
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    params.append(limit)
    params.append(offset)
    
    sql = f"""
        SELECT 
            oe.id, oe.location_id, oe.email, oe.status,
            oe.ses_message_id, oe.sent_at, oe.delivered_at,
            oe.clicked_at, oe.bounced_at, oe.bounce_reason,
            oe.created_at, oe.updated_at,
            l.name as location_name
        FROM outreach_emails oe
        LEFT JOIN locations l ON l.id = oe.location_id
        {where_clause}
        ORDER BY oe.created_at DESC
        LIMIT ${param_num} OFFSET ${param_num + 1}
    """
    
    rows = await fetch(sql, *params)
    
    return [
        OutreachEmailResponse(
            id=row["id"],
            location_id=row["location_id"],
            location_name=row.get("location_name"),
            email=row["email"],
            status=row["status"],
            ses_message_id=row.get("ses_message_id"),
            sent_at=row.get("sent_at"),
            delivered_at=row.get("delivered_at"),
            clicked_at=row.get("clicked_at"),
            bounced_at=row.get("bounced_at"),
            bounce_reason=row.get("bounce_reason"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]

