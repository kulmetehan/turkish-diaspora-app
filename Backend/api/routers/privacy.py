# Backend/api/routers/privacy.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.client_id import get_client_id
from app.deps.auth import get_current_user, get_current_user_optional, User
from services.db_service import fetch

router = APIRouter(prefix="/privacy", tags=["privacy"])


class PrivacySettings(BaseModel):
    allow_location_tracking: bool = True
    allow_push_notifications: bool = False
    allow_email_digest: bool = False
    data_retention_consent: bool = True
    updated_at: Optional[datetime] = None


class PrivacySettingsUpdate(BaseModel):
    allow_location_tracking: Optional[bool] = None
    allow_push_notifications: Optional[bool] = None
    allow_email_digest: Optional[bool] = None
    data_retention_consent: Optional[bool] = None


@router.get("/settings", response_model=PrivacySettings)
async def get_privacy_settings(
    request: Request,
    client_id: Optional[str] = Depends(get_client_id),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get privacy settings for current user (authenticated) or client_id (anonymous).
    
    For now, only authenticated users have privacy settings stored.
    Anonymous users get default settings.
    """
    user_id = user.user_id if user else None
    
    if user_id:
        # Fetch from privacy_settings table for authenticated users
        sql = """
            SELECT allow_location_tracking, allow_push_notifications, 
                   allow_email_digest, data_retention_consent, updated_at
            FROM privacy_settings
            WHERE user_id = $1
        """
        rows = await fetch(sql, user_id)
        
        if rows:
            row = rows[0]
            return PrivacySettings(
                allow_location_tracking=row.get("allow_location_tracking", True),
                allow_push_notifications=row.get("allow_push_notifications", False),
                allow_email_digest=row.get("allow_email_digest", False),
                data_retention_consent=row.get("data_retention_consent", True),
                updated_at=row.get("updated_at"),
            )
    
    # Return default settings for anonymous users or users without settings
    return PrivacySettings()


@router.put("/settings", response_model=PrivacySettings)
async def update_privacy_settings(
    request: Request,
    settings: PrivacySettingsUpdate,
    client_id: Optional[str] = Depends(get_client_id),
    user: User = Depends(get_current_user),
):
    """
    Update privacy settings. Requires authentication.
    """
    user_id = user.user_id
    
    # Get current settings first
    get_sql = """
        SELECT allow_location_tracking, allow_push_notifications, 
               allow_email_digest, data_retention_consent
        FROM privacy_settings
        WHERE user_id = $1
    """
    current_rows = await fetch(get_sql, user_id)
    
    # Build final settings with defaults
    if current_rows:
        current = current_rows[0]
        final_settings = {
            "allow_location_tracking": settings.allow_location_tracking if settings.allow_location_tracking is not None else current.get("allow_location_tracking", True),
            "allow_push_notifications": settings.allow_push_notifications if settings.allow_push_notifications is not None else current.get("allow_push_notifications", False),
            "allow_email_digest": settings.allow_email_digest if settings.allow_email_digest is not None else current.get("allow_email_digest", False),
            "data_retention_consent": settings.data_retention_consent if settings.data_retention_consent is not None else current.get("data_retention_consent", True),
        }
    else:
        # Use provided settings or defaults
        final_settings = {
            "allow_location_tracking": settings.allow_location_tracking if settings.allow_location_tracking is not None else True,
            "allow_push_notifications": settings.allow_push_notifications if settings.allow_push_notifications is not None else False,
            "allow_email_digest": settings.allow_email_digest if settings.allow_email_digest is not None else False,
            "data_retention_consent": settings.data_retention_consent if settings.data_retention_consent is not None else True,
        }
    
    # Upsert privacy settings
    upsert_sql = """
        INSERT INTO privacy_settings (
            user_id, allow_location_tracking, allow_push_notifications, 
            allow_email_digest, data_retention_consent, updated_at
        )
        VALUES ($1, $2, $3, $4, $5, now())
        ON CONFLICT (user_id)
        DO UPDATE SET
            allow_location_tracking = EXCLUDED.allow_location_tracking,
            allow_push_notifications = EXCLUDED.allow_push_notifications,
            allow_email_digest = EXCLUDED.allow_email_digest,
            data_retention_consent = EXCLUDED.data_retention_consent,
            updated_at = now()
        RETURNING allow_location_tracking, allow_push_notifications, 
                  allow_email_digest, data_retention_consent, updated_at
    """
    
    result_rows = await fetch(
        upsert_sql,
        user_id,
        final_settings["allow_location_tracking"],
        final_settings["allow_push_notifications"],
        final_settings["allow_email_digest"],
        final_settings["data_retention_consent"],
    )
    
    if not result_rows:
        raise HTTPException(status_code=500, detail="Failed to update privacy settings")
    
    row = result_rows[0]
    return PrivacySettings(
        allow_location_tracking=row.get("allow_location_tracking", True),
        allow_push_notifications=row.get("allow_push_notifications", False),
        allow_email_digest=row.get("allow_email_digest", False),
        data_retention_consent=row.get("data_retention_consent", True),
        updated_at=row.get("updated_at"),
    )
