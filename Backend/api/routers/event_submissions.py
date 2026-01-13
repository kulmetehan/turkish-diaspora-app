"""
Event submission endpoints for authenticated users.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.deps.auth import get_current_user, User
from app.models.event_submission import (
    EventSubmissionCreate,
    EventSubmissionResponse,
)
from app.models.location_submission import GeocodeResponse
from services.db_service import fetch, execute, fetchrow
from services.nominatim_service import NominatimService
from services.email_service import EmailService
from services.email_template_service import get_email_template_service
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/events", tags=["event-submissions"])


@router.post("/submit/geocode", response_model=GeocodeResponse)
async def geocode_address(
    address: str = Body(..., embed=True, description="Address to geocode"),
    user: User = Depends(get_current_user),
):
    """
    Geocode address to lat/lng using NominatimService.
    Requires authentication.
    """
    if not address or not address.strip():
        raise HTTPException(status_code=400, detail="Address is required")
    
    try:
        async with NominatimService() as geocoder:
            result = await geocoder.geocode(
                location_text=address.strip(),
                country_codes=["nl", "be", "de"],  # Focus on Netherlands, Belgium, Germany
            )
            
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail="Could not geocode address. Please try a more specific address or select location on map."
                )
            
            lat, lng, country = result
            
            # Get display_name by doing a reverse geocode (optional, but helpful)
            # For now, just return the geocoded coordinates
            # NominatimService doesn't return display_name in geocode(), so we'll use the address as display_name
            display_name = address.strip()
            
            logger.info(
                "event_geocoded",
                user_id=str(user.user_id),
                address=address[:100],  # Truncate for logging
                lat=lat,
                lng=lng,
            )
            
            return GeocodeResponse(
                lat=lat,
                lng=lng,
                display_name=display_name,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "geocoding_failed",
            user_id=str(user.user_id),
            address=address[:100],
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Geocoding failed: {str(e)}"
        )


@router.post("/submit", response_model=EventSubmissionResponse, status_code=201)
async def submit_event(
    submission: EventSubmissionCreate,
    user: User = Depends(get_current_user),
):
    """
    Submit new event for review.
    Requires authentication.
    """
    # Basic validation
    if not submission.title or not submission.title.strip():
        raise HTTPException(status_code=400, detail="Event title is required")
    
    # Validate start_time is in the future
    now_utc = datetime.now(timezone.utc)
    if submission.start_time_utc <= now_utc:
        raise HTTPException(
            status_code=400,
            detail="Event start time must be in the future"
        )
    
    # Check for potential duplicates (title + start_time within 1 hour)
    duplicate_check_sql = """
        SELECT id, title, start_time_utc
        FROM events_candidate
        WHERE title ILIKE $1
          AND ABS(EXTRACT(EPOCH FROM (start_time_utc - $2))) < 3600  -- Within 1 hour
        LIMIT 1
    """
    duplicate_rows = await fetch(
        duplicate_check_sql,
        f"%{submission.title.strip()}%",
        submission.start_time_utc,
    )
    
    if duplicate_rows:
        existing = duplicate_rows[0]
        raise HTTPException(
            status_code=409,
            detail=f"A similar event already exists: {existing['title']}"
        )
    
    # Check for duplicate submissions from same user
    user_duplicate_sql = """
        SELECT id, title, status
        FROM user_submitted_events
        WHERE user_id = $1
          AND title ILIKE $2
          AND ABS(EXTRACT(EPOCH FROM (start_time_utc - $3))) < 3600  -- Within 1 hour
          AND status = 'pending'
        LIMIT 1
    """
    user_duplicate_rows = await fetch(
        user_duplicate_sql,
        user.user_id,
        f"%{submission.title.strip()}%",
        submission.start_time_utc,
    )
    
    if user_duplicate_rows:
        raise HTTPException(
            status_code=409,
            detail="You already have a pending submission for a similar event"
        )
    
    # Insert submission
    insert_sql = """
        INSERT INTO user_submitted_events (
            title, description, start_time_utc, end_time_utc, location_text,
            lat, lng, url, category_key, user_id,
            status, submitted_at, created_at, updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'pending', now(), now(), now())
        RETURNING 
            id, title, description, start_time_utc, end_time_utc, location_text,
            lat, lng, url, category_key, user_id,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_event_id, created_at, updated_at
    """
    
    result = await fetch(
        insert_sql,
        submission.title.strip(),
        submission.description.strip() if submission.description else None,
        submission.start_time_utc,
        submission.end_time_utc,
        submission.location_text.strip() if submission.location_text else None,
        float(submission.lat) if submission.lat is not None else None,
        float(submission.lng) if submission.lng is not None else None,
        submission.url,
        submission.category_key.strip() if submission.category_key else None,
        user.user_id,
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create event submission")
    
    row = result[0]
    
    logger.info(
        "event_submission_created",
        submission_id=row["id"],
        user_id=str(user.user_id),
        event_title=submission.title[:100],
    )
    
    # Send confirmation email
    try:
        user_email_sql = """
            SELECT email, raw_user_meta_data->>'name' as user_name
            FROM auth.users WHERE id = $1
        """
        user_rows = await fetch(user_email_sql, user.user_id)
        
        if user_rows and user_rows[0].get("email"):
            user_email = user_rows[0]["email"]
            user_name = user_rows[0].get("user_name") or "Gebruiker"
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "event_submission_received",
                context={
                    "user_name": user_name,
                    "event_title": submission.title,
                },
                language=language,
            )
            
            # Send email
            email_service = EmailService()
            subject = f"Uw event is ingediend - {submission.title}"
            if language == "tr":
                subject = f"Etkinliğiniz gönderildi - {submission.title}"
            elif language == "en":
                subject = f"Your event has been submitted - {submission.title}"
            
            await email_service.send_email(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "event_submission_email_sent",
                submission_id=row["id"],
                user_email=user_email,
            )
    except Exception as e:
        # Email failure should not block submission
        logger.warning(
            "event_submission_email_failed",
            submission_id=row["id"],
            error=str(e),
        )
    
    # Send admin notification (non-blocking)
    try:
        from services.admin_notification_service import send_admin_notification
        
        await send_admin_notification(
            action_type="event_submitted",
            context={
                "user_email": user_email if user_rows and user_rows[0].get("email") else None,
                "user_id": str(user.user_id),
                "user_name": user_name if user_rows and user_rows[0].get("email") else None,
                "event_title": submission.title,
                "event_description": submission.description,
                "event_start_time": submission.start_time_utc.isoformat() if hasattr(submission.start_time_utc, "isoformat") else str(submission.start_time_utc),
                "event_location": submission.location_text,
                "category_key": submission.category_key,
                "submission_id": row["id"],
                "submitted_at": row["submitted_at"].isoformat() if hasattr(row["submitted_at"], "isoformat") else str(row["submitted_at"]),
            },
            language="nl",
        )
    except Exception as e:
        logger.warning(
            "admin_notification_event_submitted_failed",
            submission_id=row["id"],
            error=str(e),
        )
    
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


@router.get("/my-submissions", response_model=List[EventSubmissionResponse])
async def list_my_submissions(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$", description="Filter by status"),
    user: User = Depends(get_current_user),
):
    """
    List user's own event submissions.
    """
    conditions = ["user_id = $1"]
    params = [user.user_id]
    
    if status:
        conditions.append("status = $2")
        params.append(status)
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            id, title, description, start_time_utc, end_time_utc, location_text,
            lat, lng, url, category_key, user_id,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_event_id, created_at, updated_at
        FROM user_submitted_events
        WHERE {where_clause}
        ORDER BY created_at DESC
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

