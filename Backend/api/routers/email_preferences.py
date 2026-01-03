# Backend/api/routers/email_preferences.py
from __future__ import annotations

from datetime import datetime
from typing import Optional
import secrets
import hashlib

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, EmailStr
from starlette.responses import RedirectResponse

from app.deps.auth import get_current_user_optional, User
from app.core.logging import logger
from services.db_service import fetchrow, execute, fetch
import os

router = APIRouter(prefix="/email", tags=["email"])


class EmailPreferencesResponse(BaseModel):
    weekly_digest: bool
    outreach_emails: bool
    transactional_emails: bool
    unsubscribed_at: Optional[datetime] = None


class EmailPreferencesUpdate(BaseModel):
    weekly_digest: Optional[bool] = None
    outreach_emails: Optional[bool] = None
    transactional_emails: Optional[bool] = None


def generate_unsubscribe_token(email: str, user_id: Optional[str] = None) -> str:
    """Generate a secure unsubscribe token."""
    secret_key = os.getenv("UNSUBSCRIBE_SECRET_KEY", "change-me-in-production")
    data = f"{email}:{user_id or ''}:{secret_key}"
    token = hashlib.sha256(data.encode()).hexdigest()
    return token


def verify_unsubscribe_token(token: str, email: str, user_id: Optional[str] = None) -> bool:
    """Verify an unsubscribe token."""
    expected_token = generate_unsubscribe_token(email, user_id)
    return secrets.compare_digest(token, expected_token)


@router.get("/unsubscribe")
async def unsubscribe_via_token(
    token: str = Query(..., description="Unsubscribe token"),
    email: Optional[str] = Query(None, description="Email address"),
    user_id: Optional[str] = Query(None, description="User ID (UUID)"),
):
    """Unsubscribe via token from email link. Redirects to frontend confirmation page."""
    
    if not email and not user_id:
        raise HTTPException(status_code=400, detail="Email of user_id is verplicht")
    
    # Verify token
    if not verify_unsubscribe_token(token, email or "", user_id):
        raise HTTPException(status_code=400, detail="Ongeldige unsubscribe token")
    
    try:
        # Update preferences
        if user_id:
            # Update by user_id
            update_sql = """
                UPDATE email_preferences
                SET unsubscribed_at = now(),
                    weekly_digest = false,
                    outreach_emails = false,
                    transactional_emails = false,
                    updated_at = now()
                WHERE user_id = $1::uuid
            """
            await execute(update_sql, user_id)
        else:
            # Update by email
            update_sql = """
                UPDATE email_preferences
                SET unsubscribed_at = now(),
                    weekly_digest = false,
                    outreach_emails = false,
                    transactional_emails = false,
                    updated_at = now()
                WHERE email = $1
            """
            await execute(update_sql, email)
        
        logger.info(
            "email_unsubscribed_via_token",
            email=email,
            user_id=user_id,
        )
        
        # Redirect to frontend confirmation page
        frontend_url = os.getenv("FRONTEND_URL", "https://turkspot.app")
        return RedirectResponse(
            url=f"{frontend_url}/#/email-preferences?unsubscribed=true",
            status_code=302
        )
        
    except Exception as e:
        logger.error(
            "email_unsubscribe_failed",
            email=email,
            user_id=user_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Kon niet uitschrijven. Probeer het later opnieuw."
        )


@router.post("/unsubscribe")
async def unsubscribe_direct(
    email: Optional[EmailStr] = None,
    user_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Unsubscribe directly (for authenticated users or with email)."""
    
    # Use current user if authenticated
    if current_user:
        user_id = current_user.user_id
    
    if not email and not user_id:
        raise HTTPException(
            status_code=400,
            detail="Email of user_id is verplicht"
        )
    
    try:
        if user_id:
            update_sql = """
                UPDATE email_preferences
                SET unsubscribed_at = now(),
                    weekly_digest = false,
                    outreach_emails = false,
                    transactional_emails = false,
                    updated_at = now()
                WHERE user_id = $1::uuid
            """
            await execute(update_sql, user_id)
        else:
            update_sql = """
                UPDATE email_preferences
                SET unsubscribed_at = now(),
                    weekly_digest = false,
                    outreach_emails = false,
                    transactional_emails = false,
                    updated_at = now()
                WHERE email = $1
            """
            await execute(update_sql, email)
        
        logger.info(
            "email_unsubscribed_direct",
            email=email,
            user_id=user_id,
        )
        
        return {"ok": True, "message": "Uitgeschreven voor alle emails"}
        
    except Exception as e:
        logger.error(
            "email_unsubscribe_failed",
            email=email,
            user_id=user_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Kon niet uitschrijven. Probeer het later opnieuw."
        )


@router.get("/preferences", response_model=EmailPreferencesResponse)
async def get_email_preferences(
    current_user: User = Depends(get_current_user_optional),
):
    """Get email preferences for current user."""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    sql = """
        SELECT weekly_digest, outreach_emails, transactional_emails, unsubscribed_at
        FROM email_preferences
        WHERE user_id = $1::uuid
    """
    
    rows = await fetch(sql, current_user.user_id)
    
    if not rows:
        # Return defaults if no preferences exist
        return EmailPreferencesResponse(
            weekly_digest=True,
            outreach_emails=True,
            transactional_emails=True,
            unsubscribed_at=None,
        )
    
    row = rows[0]
    return EmailPreferencesResponse(
        weekly_digest=row.get("weekly_digest", True),
        outreach_emails=row.get("outreach_emails", True),
        transactional_emails=row.get("transactional_emails", True),
        unsubscribed_at=row.get("unsubscribed_at"),
    )


@router.put("/preferences", response_model=EmailPreferencesResponse)
async def update_email_preferences(
    preferences: EmailPreferencesUpdate,
    current_user: User = Depends(get_current_user_optional),
):
    """Update email preferences for current user."""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if preferences exist
    check_sql = "SELECT user_id FROM email_preferences WHERE user_id = $1::uuid"
    existing = await fetch(check_sql, current_user.user_id)
    
    updates = []
    values = []
    param_num = 1
    
    if preferences.weekly_digest is not None:
        updates.append(f"weekly_digest = ${param_num}")
        values.append(preferences.weekly_digest)
        param_num += 1
    
    if preferences.outreach_emails is not None:
        updates.append(f"outreach_emails = ${param_num}")
        values.append(preferences.outreach_emails)
        param_num += 1
    
    if preferences.transactional_emails is not None:
        updates.append(f"transactional_emails = ${param_num}")
        values.append(preferences.transactional_emails)
        param_num += 1
    
    if not updates:
        # No changes, return current preferences
        return await get_email_preferences(current_user)
    
    if existing:
        # Update existing preferences
        updates_str = ", ".join(updates)
        updates_str += f", updated_at = now()"
        update_sql = f"""
            UPDATE email_preferences
            SET {updates_str}
            WHERE user_id = ${param_num}::uuid
        """
        values.append(current_user.user_id)
        await execute(update_sql, *values)
    else:
        # Create new preferences
        insert_sql = """
            INSERT INTO email_preferences (
                user_id, email, weekly_digest, outreach_emails, transactional_emails, created_at, updated_at
            ) VALUES (
                $1::uuid, $2, $3, $4, $5, now(), now()
            )
        """
        # Get email from user
        user_email = current_user.email or ""
        await execute(
            insert_sql,
            current_user.user_id,
            user_email,
            preferences.weekly_digest if preferences.weekly_digest is not None else True,
            preferences.outreach_emails if preferences.outreach_emails is not None else True,
            preferences.transactional_emails if preferences.transactional_emails is not None else True,
        )
    
    return await get_email_preferences(current_user)







