"""
Location submission endpoints for authenticated users.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from typing import List, Optional
from uuid import UUID

from app.deps.auth import get_current_user, User
from app.models.location_submission import (
    LocationSubmissionCreate,
    LocationSubmissionResponse,
    GeocodeResponse,
)
from services.db_service import fetch, execute, fetchrow
from services.nominatim_service import NominatimService
from services.email_service import EmailService
from services.email_template_service import get_email_template_service
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/locations", tags=["location-submissions"])


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
                "location_geocoded",
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


@router.post("/submit", response_model=LocationSubmissionResponse, status_code=201)
async def submit_location(
    submission: LocationSubmissionCreate,
    user: User = Depends(get_current_user),
):
    """
    Submit new location for review.
    Requires authentication.
    """
    # Basic validation
    if not submission.name or not submission.name.strip():
        raise HTTPException(status_code=400, detail="Location name is required")
    
    if not submission.category or not submission.category.strip():
        raise HTTPException(status_code=400, detail="Category is required")
    
    # Check for potential duplicates (fuzzy match on name + coordinates within 100m)
    # This is a simple check - can be improved later
    duplicate_check_sql = """
        SELECT id, name, lat, lng
        FROM locations
        WHERE name ILIKE $1
          AND ABS(lat - $2) < 0.001  -- ~100m
          AND ABS(lng - $3) < 0.001  -- ~100m
        LIMIT 1
    """
    duplicate_rows = await fetch(
        duplicate_check_sql,
        f"%{submission.name.strip()}%",
        float(submission.lat),
        float(submission.lng),
    )
    
    if duplicate_rows:
        existing = duplicate_rows[0]
        raise HTTPException(
            status_code=409,
            detail=f"A similar location already exists: {existing['name']}"
        )
    
    # Check for duplicate submissions from same user
    user_duplicate_sql = """
        SELECT id, name, status
        FROM user_submitted_locations
        WHERE user_id = $1
          AND name ILIKE $2
          AND ABS(lat - $3) < 0.001
          AND ABS(lng - $4) < 0.001
          AND status = 'pending'
        LIMIT 1
    """
    user_duplicate_rows = await fetch(
        user_duplicate_sql,
        user.user_id,
        f"%{submission.name.strip()}%",
        float(submission.lat),
        float(submission.lng),
    )
    
    if user_duplicate_rows:
        raise HTTPException(
            status_code=409,
            detail="You already have a pending submission for a similar location"
        )
    
    # Insert submission
    insert_sql = """
        INSERT INTO user_submitted_locations (
            name, address, lat, lng, category, user_id, is_owner,
            status, submitted_at, created_at, updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', now(), now(), now())
        RETURNING 
            id, name, address, lat, lng, category, user_id, is_owner,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_location_id, created_at, updated_at
    """
    
    result = await fetch(
        insert_sql,
        submission.name.strip(),
        submission.address.strip() if submission.address else None,
        float(submission.lat),
        float(submission.lng),
        submission.category.strip(),
        user.user_id,
        submission.is_owner,
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create location submission")
    
    row = result[0]
    
    logger.info(
        "location_submission_created",
        submission_id=row["id"],
        user_id=str(user.user_id),
        location_name=submission.name[:100],
        is_owner=submission.is_owner,
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
                "location_submission_received",
                context={
                    "user_name": user_name,
                    "location_name": submission.name,
                },
                language=language,
            )
            
            # Send email
            email_service = EmailService()
            subject = f"Uw locatie is ingediend - {submission.name}"
            if language == "tr":
                subject = f"Konumunuz gönderildi - {submission.name}"
            elif language == "en":
                subject = f"Your location has been submitted - {submission.name}"
            
            await email_service.send_email(
                to_email=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "location_submission_email_sent",
                submission_id=row["id"],
                user_email=user_email,
            )
    except Exception as e:
        # Email failure should not block submission
        logger.warning(
            "location_submission_email_failed",
            submission_id=row["id"],
            error=str(e),
        )
    
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


@router.get("/my-submissions", response_model=List[LocationSubmissionResponse])
async def list_my_submissions(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$", description="Filter by status"),
    user: User = Depends(get_current_user),
):
    """
    List user's own location submissions.
    """
    conditions = ["user_id = $1"]
    params = [user.user_id]
    
    if status:
        conditions.append("status = $2")
        params.append(status)
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            id, name, address, lat, lng, category, user_id, is_owner,
            status, submitted_at, reviewed_by, reviewed_at, rejection_reason,
            created_location_id, created_at, updated_at
        FROM user_submitted_locations
        WHERE {where_clause}
        ORDER BY created_at DESC
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









