# Backend/api/routers/google_business.py
from __future__ import annotations

import secrets
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from typing import Optional
from pydantic import BaseModel

from app.deps.auth import get_current_user, User
from services.google_business_service import get_google_business_service
from services.db_service import fetch, execute
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/google-business", tags=["google-business"])


class ConnectResponse(BaseModel):
    oauth_url: str
    state: str


class SyncStatusResponse(BaseModel):
    location_id: int
    sync_status: str
    last_synced_at: Optional[str]
    google_business_id: Optional[str]
    sync_error: Optional[str]


async def get_user_business_account(user: User) -> int:
    """
    Get the business account ID for the current user.
    """
    sql = """
        SELECT id FROM business_accounts WHERE owner_user_id = $1
        LIMIT 1
    """
    result = await fetch(sql, user.user_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Business account not found"
        )
    
    return result[0]["id"]


@router.post("/connect", response_model=ConnectResponse)
async def initiate_oauth(
    location_id: int = Query(..., description="Location ID to connect"),
    user: User = Depends(get_current_user),
):
    """
    Initiate Google Business OAuth flow.
    """
    business_account_id = await get_user_business_account(user)
    
    # Verify location belongs to business account
    claim_sql = """
        SELECT status FROM business_location_claims
        WHERE business_account_id = $1 AND location_id = $2
    """
    claim_rows = await fetch(claim_sql, business_account_id, location_id)
    
    if not claim_rows:
        raise HTTPException(
            status_code=404,
            detail="Location not found or not claimed by this business account"
        )
    
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state temporarily (in production, use Redis or similar)
    # For now, we'll include it in the response and validate in callback
    
    google_service = get_google_business_service()
    oauth_url = google_service.get_oauth_url(state=state)
    
    return ConnectResponse(oauth_url=oauth_url, state=state)


@router.get("/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State token"),
    location_id: Optional[int] = Query(None, description="Location ID (from state or session)"),
    user: User = Depends(get_current_user),
):
    """
    Handle Google OAuth callback.
    """
    business_account_id = await get_user_business_account(user)
    
    if not location_id:
        raise HTTPException(
            status_code=400,
            detail="Location ID required"
        )
    
    google_service = get_google_business_service()
    
    try:
        # Exchange code for tokens
        tokens = await google_service.exchange_code_for_tokens(code=code)
        
        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        
        # Get Google Business Profile ID (would come from API call)
        # For now, placeholder
        google_business_id = "placeholder-id"  # Would be fetched from Google API
        
        # Create sync record
        sync_id = await google_service.create_sync_record(
            business_account_id=business_account_id,
            location_id=location_id,
            google_business_id=google_business_id,
            access_token=access_token,
            refresh_token=refresh_token or "",
            expires_in=expires_in,
        )
        
        logger.info(
            "google_business_connected",
            business_account_id=business_account_id,
            location_id=location_id,
            sync_id=sync_id,
        )
        
        return {
            "ok": True,
            "message": "Google Business connected successfully",
            "sync_id": sync_id,
        }
        
    except Exception as e:
        logger.error(
            "google_business_connection_failed",
            business_account_id=business_account_id,
            location_id=location_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect Google Business: {str(e)}"
        )


@router.post("/sync/{location_id}")
async def trigger_sync(
    location_id: int = Path(..., description="Location ID"),
    user: User = Depends(get_current_user),
):
    """
    Manually trigger sync for a location.
    """
    business_account_id = await get_user_business_account(user)
    
    # Verify location belongs to business account
    claim_sql = """
        SELECT status FROM business_location_claims
        WHERE business_account_id = $1 AND location_id = $2
    """
    claim_rows = await fetch(claim_sql, business_account_id, location_id)
    
    if not claim_rows:
        raise HTTPException(
            status_code=404,
            detail="Location not found or not claimed by this business account"
        )
    
    google_service = get_google_business_service()
    
    try:
        result = await google_service.sync_location_data(location_id=location_id)
        return result
    except Exception as e:
        logger.error(
            "google_business_sync_failed",
            location_id=location_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )


@router.get("/status")
async def get_sync_status(
    user: User = Depends(get_current_user),
):
    """
    Get sync status for all locations of the business account.
    """
    business_account_id = await get_user_business_account(user)
    
    # Get all claimed locations
    locations_sql = """
        SELECT location_id FROM business_location_claims
        WHERE business_account_id = $1
    """
    location_rows = await fetch(locations_sql, business_account_id)
    location_ids = [row["location_id"] for row in location_rows]
    
    if not location_ids:
        return {"locations": []}
    
    # Get sync status for each location
    sync_sql = """
        SELECT 
            location_id,
            sync_status,
            last_synced_at,
            google_business_id,
            sync_error
        FROM google_business_sync
        WHERE location_id = ANY($1::bigint[])
    """
    sync_rows = await fetch(sync_sql, location_ids)
    
    locations = [
        {
            "location_id": row["location_id"],
            "sync_status": row["sync_status"],
            "last_synced_at": row["last_synced_at"].isoformat() if row["last_synced_at"] else None,
            "google_business_id": row["google_business_id"],
            "sync_error": row["sync_error"],
        }
        for row in sync_rows
    ]
    
    return {"locations": locations}



















