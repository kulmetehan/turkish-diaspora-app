# Backend/api/routers/outreach_claims.py
"""
Token-based Claim API Endpoints

Endpoints for token-based location claims (no authentication required).
Used as fallback for non-authenticated users via outreach emails.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime, timedelta

from services.db_service import fetch, fetchrow, execute
from services.claim_token_service import validate_token, generate_token, TokenClaimInfo
from services.email_service import EmailService
from services.email_template_service import get_email_template_service
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/claims", tags=["outreach-claims"])


# Request/Response Models
class ClaimRequest(BaseModel):
    """Request model for claiming a location via token."""
    email: EmailStr = Field(..., description="Email address of the person claiming the location")
    description: Optional[str] = Field(None, max_length=2000, description="Optional description or notes")
    # Logo upload will be handled separately if needed (similar to authenticated claims)


class RemoveRequest(BaseModel):
    """Request model for removing a location claim."""
    reason: Optional[str] = Field(None, max_length=500, description="Optional reason for removal")


class CorrectRequest(BaseModel):
    """Request model for submitting a correction."""
    correction_details: str = Field(..., min_length=3, max_length=2000, description="Correction details")


class TokenClaimResponse(BaseModel):
    """Response model for token claim information."""
    location_id: int
    location_name: Optional[str]
    location_address: Optional[str]
    location_category: Optional[str]
    claim_token: str
    claim_status: str
    claimed_by_email: Optional[str] = None
    claimed_at: Optional[datetime] = None
    free_until: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    removal_reason: Optional[str] = None


class ClaimActionResponse(BaseModel):
    """Response model for claim actions (claim, remove, correct)."""
    success: bool
    message: str
    claim_info: Optional[TokenClaimInfo] = None


@router.get("/{token}", response_model=TokenClaimResponse)
async def get_claim_info(
    token: str = Path(..., description="Claim token"),
):
    """
    Get claim information for a token.
    Returns location details and claim status.
    """
    try:
        claim_info = await validate_token(token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not claim_info:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    # Fetch location details
    location_sql = """
        SELECT id, name, address, category
        FROM locations
        WHERE id = $1
    """
    location_row = await fetchrow(location_sql, claim_info.location_id)
    
    if not location_row:
        raise HTTPException(status_code=404, detail="Location not found")
    
    return TokenClaimResponse(
        location_id=claim_info.location_id,
        location_name=location_row.get("name"),
        location_address=location_row.get("address"),
        location_category=location_row.get("category"),
        claim_token=claim_info.claim_token,
        claim_status=claim_info.claim_status,
        claimed_by_email=claim_info.claimed_by_email,
        claimed_at=claim_info.claimed_at,
        free_until=claim_info.free_until,
        removed_at=claim_info.removed_at,
        removal_reason=claim_info.removal_reason,
    )


@router.post("/{token}/claim", response_model=ClaimActionResponse, status_code=201)
async def claim_location(
    token: str = Path(..., description="Claim token"),
    request: ClaimRequest = ...,
):
    """
    Claim a location using a token.
    No authentication required - token provides authorization.
    """
    try:
        claim_info = await validate_token(token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not claim_info:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    # Check if already claimed
    if claim_info.claim_status != "unclaimed":
        raise HTTPException(
            status_code=409,
            detail=f"Location is already {claim_info.claim_status}"
        )
    
    # Calculate free_until date (e.g., 30 days from now)
    # This can be made configurable via env var
    free_period_days = 30
    free_until = datetime.now() + timedelta(days=free_period_days)
    
    # Update claim status
    update_sql = """
        UPDATE token_location_claims
        SET 
            claim_status = 'claimed_free',
            claimed_by_email = $1,
            claimed_at = now(),
            free_until = $2,
            updated_at = now()
        WHERE claim_token = $3
        RETURNING 
            location_id, claim_token, claim_status,
            claimed_by_email, claimed_at, free_until,
            removed_at, removal_reason
    """
    
    result = await fetchrow(
        update_sql,
        request.email,
        free_until,
        token,
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update claim")
    
    updated_claim = TokenClaimInfo(
        location_id=result["location_id"],
        claim_token=result["claim_token"],
        claim_status=result["claim_status"],
        claimed_by_email=result.get("claimed_by_email"),
        claimed_at=result.get("claimed_at"),
        free_until=result.get("free_until"),
        removed_at=result.get("removed_at"),
        removal_reason=result.get("removal_reason"),
    )
    
    logger.info(
        "token_location_claimed",
        location_id=claim_info.location_id,
        email=request.email,
        free_until=free_until.isoformat(),
    )
    
    return ClaimActionResponse(
        success=True,
        message="Location claimed successfully",
        claim_info=updated_claim,
    )


@router.post("/{token}/remove", response_model=ClaimActionResponse)
async def remove_location(
    token: str = Path(..., description="Claim token"),
    request: RemoveRequest = ...,
):
    """
    Remove a location claim using a token.
    Only works if location is currently claimed.
    """
    try:
        claim_info = await validate_token(token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not claim_info:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    # Check if location is claimed (can only remove if claimed)
    if claim_info.claim_status not in ("claimed_free", "expired"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot remove location with status: {claim_info.claim_status}"
        )
    
    # Update claim status to removed
    update_sql = """
        UPDATE token_location_claims
        SET 
            claim_status = 'removed',
            removed_at = now(),
            removal_reason = $1,
            updated_at = now()
        WHERE claim_token = $2
        RETURNING 
            location_id, claim_token, claim_status,
            claimed_by_email, claimed_at, free_until,
            removed_at, removal_reason
    """
    
    result = await fetchrow(
        update_sql,
        request.reason,
        token,
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update claim")
    
    updated_claim = TokenClaimInfo(
        location_id=result["location_id"],
        claim_token=result["claim_token"],
        claim_status=result["claim_status"],
        claimed_by_email=result.get("claimed_by_email"),
        claimed_at=result.get("claimed_at"),
        free_until=result.get("free_until"),
        removed_at=result.get("removed_at"),
        removal_reason=result.get("removal_reason"),
    )
    
    logger.info(
        "token_location_removed",
        location_id=claim_info.location_id,
        email=claim_info.claimed_by_email,
        reason=request.reason,
    )
    
    # Send removal confirmation email
    if claim_info.claimed_by_email:
        try:
            # Get location name
            location_name_sql = """
                SELECT name FROM locations WHERE id = $1
            """
            location_row = await fetchrow(location_name_sql, claim_info.location_id)
            location_name = location_row.get("name") if location_row else "Locatie"
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences or email domain
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "removal_confirmation",
                context={
                    "location_name": location_name,
                    "removal_reason": request.reason,
                },
                language=language,
            )
            
            # Send email
            email_service = EmailService()
            subject = f"Uw locatie wordt verwijderd - {location_name}"
            if language == "tr":
                subject = f"Konumunuz kaldırılıyor - {location_name}"
            elif language == "en":
                subject = f"Your location is being removed - {location_name}"
            
            await email_service.send_email(
                to_email=claim_info.claimed_by_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "removal_confirmation_email_sent",
                location_id=claim_info.location_id,
                email=claim_info.claimed_by_email,
            )
        except Exception as e:
            # Email failure should not block removal
            logger.warning(
                "removal_confirmation_email_failed",
                location_id=claim_info.location_id,
                email=claim_info.claimed_by_email,
                error=str(e),
            )
    
    return ClaimActionResponse(
        success=True,
        message="Location removed successfully",
        claim_info=updated_claim,
    )


@router.post("/{token}/correct", response_model=ClaimActionResponse)
async def submit_correction(
    token: str = Path(..., description="Claim token"),
    request: CorrectRequest = ...,
):
    """
    Submit a correction for a location using a token.
    This is a placeholder - actual correction processing will be implemented later.
    """
    try:
        claim_info = await validate_token(token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not claim_info:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    
    # For now, just log the correction
    # Actual correction processing will be implemented in the outreach plan
    logger.info(
        "token_location_correction_submitted",
        location_id=claim_info.location_id,
        email=claim_info.claimed_by_email,
        correction_length=len(request.correction_details),
    )
    
    # Send correction confirmation email
    # Use claimed_by_email if available, otherwise we can't send email
    recipient_email = claim_info.claimed_by_email
    if not recipient_email:
        # Try to get email from token if it's a claim token
        # For now, we'll skip email if no email is available
        logger.warning(
            "correction_email_skipped_no_email",
            location_id=claim_info.location_id,
        )
    else:
        try:
            # Get location name
            location_name_sql = """
                SELECT name FROM locations WHERE id = $1
            """
            location_row = await fetchrow(location_name_sql, claim_info.location_id)
            location_name = location_row.get("name") if location_row else "Locatie"
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences or email domain
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "correction_confirmation",
                context={
                    "location_name": location_name,
                },
                language=language,
            )
            
            # Send email
            email_service = EmailService()
            subject = f"Bedankt voor uw correctie - {location_name}"
            if language == "tr":
                subject = f"Düzeltmeniz için teşekkürler - {location_name}"
            elif language == "en":
                subject = f"Thank you for your correction - {location_name}"
            
            await email_service.send_email(
                to_email=recipient_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "correction_confirmation_email_sent",
                location_id=claim_info.location_id,
                email=recipient_email,
            )
        except Exception as e:
            # Email failure should not block correction submission
            logger.warning(
                "correction_confirmation_email_failed",
                location_id=claim_info.location_id,
                email=recipient_email,
                error=str(e),
            )
    
    return ClaimActionResponse(
        success=True,
        message="Correction submitted successfully. We will process this as soon as possible.",
        claim_info=claim_info,
    )

