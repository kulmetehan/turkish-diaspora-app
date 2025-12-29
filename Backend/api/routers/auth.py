# Backend/api/routers/auth.py
from __future__ import annotations

import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel, EmailStr
from uuid import UUID

from app.deps.auth import get_current_user, User
from services.db_service import fetch, execute
from app.core.logging import get_logger
from services.email_service import get_email_service

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])


class UserInfo(BaseModel):
    user_id: str
    email: Optional[str] = None
    has_profile: bool = False
    display_name: Optional[str] = None


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RecaptchaVerifyRequest(BaseModel):
    token: str
    action: str


class RecaptchaVerifyResponse(BaseModel):
    ok: bool
    score: float
    action: str
    threshold: float


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    user: User = Depends(get_current_user),
):
    """Get current authenticated user info."""
    
    # Ensure user profile exists (auto-create if missing)
    ensure_profile_sql = """
        INSERT INTO user_profiles (id, created_at, updated_at)
        VALUES ($1::uuid, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """
    await execute(ensure_profile_sql, user.user_id)
    
    # Check if user has profile
    profile_sql = """
        SELECT display_name
        FROM user_profiles
        WHERE id = $1::uuid
    """
    profile_rows = await fetch(profile_sql, user.user_id)
    has_profile = len(profile_rows) > 0
    display_name = profile_rows[0].get("display_name") if profile_rows else None
    
    return UserInfo(
        user_id=str(user.user_id),
        email=user.email,
        has_profile=has_profile,
        display_name=display_name,
    )


@router.post("/signup")
async def signup(
    request: SignupRequest,
):
    """
    User signup endpoint.
    
    Note: Actual user creation happens in Supabase Auth.
    This endpoint is for creating the user profile after Supabase signup.
    The frontend should call Supabase auth.signUp() first, then call this endpoint.
    """
    # This endpoint is informational - actual signup should use Supabase client directly
    # We can add profile creation logic here if needed
    return {
        "message": "Use Supabase client auth.signUp() in the frontend to create users.",
        "note": "After signup, call /api/v1/auth/migrate-client-id to migrate anonymous activity."
    }


class MigrateClientIdRequest(BaseModel):
    client_id: str


@router.post("/migrate-client-id")
async def migrate_client_id(
    request: MigrateClientIdRequest,
    user: User = Depends(get_current_user),
):
    """
    Migrate anonymous client_id activity to authenticated user_id.
    
    This should be called once after user signs up/logs in to transfer
    all their anonymous activity (check-ins, reactions, notes, etc.) to their user account.
    Also ensures user profile exists.
    """
    try:
        # Ensure user profile exists (auto-create if missing)
        ensure_profile_sql = """
            INSERT INTO user_profiles (id, created_at, updated_at)
            VALUES ($1::uuid, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """
        await execute(ensure_profile_sql, user.user_id)
        
        client_id = request.client_id
        
        # Migrate check-ins
        migrate_check_ins_sql = """
            UPDATE check_ins
            SET user_id = $1::uuid
            WHERE client_id = $2 AND user_id IS NULL
        """
        await execute(migrate_check_ins_sql, user.user_id, client_id)
        
        # Migrate reactions
        migrate_reactions_sql = """
            UPDATE location_reactions
            SET user_id = $1::uuid
            WHERE client_id = $2 AND user_id IS NULL
        """
        await execute(migrate_reactions_sql, user.user_id, client_id)
        
        # Migrate notes
        migrate_notes_sql = """
            UPDATE location_notes
            SET user_id = $1::uuid
            WHERE client_id = $2 AND user_id IS NULL
        """
        await execute(migrate_notes_sql, user.user_id, client_id)
        
        # Migrate favorites
        migrate_favorites_sql = """
            UPDATE favorites
            SET user_id = $1::uuid
            WHERE client_id = $2 AND user_id IS NULL
        """
        await execute(migrate_favorites_sql, user.user_id, client_id)
        
        # Migrate poll responses (client_id is stored as UUID in poll_responses)
        # Try to convert client_id to UUID if it's a valid UUID string
        try:
            client_uuid = UUID(client_id) if len(client_id) == 36 else None
            if client_uuid:
                migrate_polls_sql = """
                    UPDATE poll_responses
                    SET user_id = $1::uuid
                    WHERE client_id = $2::uuid AND user_id IS NULL
                """
                await execute(migrate_polls_sql, user.user_id, client_uuid)
        except (ValueError, TypeError):
            logger.debug("client_id_not_uuid_for_polls", client_id=client_id)
        
        logger.info("client_id_migrated", user_id=str(user.user_id), client_id=client_id)
        
        return {"ok": True, "message": "Client ID activity migrated successfully"}
        
    except Exception as e:
        logger.error("client_id_migration_failed", user_id=str(user.user_id), client_id=request.client_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to migrate client ID: {str(e)}")


@router.post("/send-welcome-email")
async def send_welcome_email(
    user: User = Depends(get_current_user),
    language: str = "nl",
):
    """
    Send welcome email to newly registered user.
    
    This endpoint should be called after successful signup to send a welcome email.
    The email failure does not block the signup process (non-blocking).
    
    Args:
        user: Authenticated user (from token)
        language: Language code (nl, tr, en). Defaults to 'nl'.
    """
    if not user.email:
        logger.warning(
            "welcome_email_no_email",
            user_id=str(user.user_id),
        )
        return {
            "ok": False,
            "message": "User email not available",
        }
    
    try:
        # Get user display name from profile if available
        profile_sql = """
            SELECT display_name
            FROM user_profiles
            WHERE id = $1::uuid
        """
        profile_rows = await fetch(profile_sql, user.user_id)
        display_name = profile_rows[0].get("display_name") if profile_rows else None
        
        # Use display_name or email as user_name
        user_name = display_name or user.email.split("@")[0] or "Gebruiker"
        
        # Normalize language code
        language = language.lower()[:2]
        if language not in ["nl", "tr", "en"]:
            language = "nl"
        
        # Prepare template context
        context = {
            "user_name": user_name,
        }
        
        # Determine subject based on language
        if language == "tr":
            subject = "Turkspot'a Hoş Geldiniz!"
        elif language == "en":
            subject = "Welcome to Turkspot!"
        else:
            subject = "Welkom bij Turkspot!"
        
        # Render and send email
        email_service = get_email_service()
        html_body, text_body = email_service.render_template(
            template_name="welcome_email",
            context=context,
            language=language,
        )
        
        # Send email (non-blocking - don't fail if email fails)
        email_sent = await email_service.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
        
        if email_sent:
            logger.info(
                "welcome_email_sent",
                user_id=str(user.user_id),
                email=user.email,
                language=language,
            )
            return {
                "ok": True,
                "message": "Welcome email sent successfully",
            }
        else:
            logger.warning(
                "welcome_email_failed",
                user_id=str(user.user_id),
                email=user.email,
                language=language,
            )
            return {
                "ok": False,
                "message": "Failed to send welcome email (email service not configured)",
            }
            
    except Exception as e:
        # Log error but don't fail the request
        logger.error(
            "welcome_email_error",
            user_id=str(user.user_id),
            email=user.email,
            language=language,
            error=str(e),
            exc_info=True,
        )
        return {
            "ok": False,
            "message": f"Error sending welcome email: {str(e)}",
        }


@router.post("/verify-recaptcha", response_model=RecaptchaVerifyResponse)
async def verify_recaptcha(request: RecaptchaVerifyRequest):
    """
    Verify reCAPTCHA Enterprise v3 token.
    
    This endpoint verifies a reCAPTCHA token with Google's API and returns
    the score and verification result. Used for bot protection on forms.
    
    Args:
        request: Request containing reCAPTCHA token and action name
        
    Returns:
        Verification result with score, action, and threshold
        
    Raises:
        HTTPException: If verification fails or score is too low
    """
    secret_key = os.getenv("RECAPTCHA_SECRET_KEY")
    
    # Development mode: if secret key not configured, return success
    if not secret_key:
        logger.debug(
            "recaptcha_verification_dev_mode",
            action=request.action,
            message="RECAPTCHA_SECRET_KEY not set, returning development mode response",
        )
        return RecaptchaVerifyResponse(
            ok=True,
            score=0.9,
            action=request.action,
            threshold=0.5 if request.action == "SIGNUP" else 0.3,
        )
    
    try:
        # Verify token with Google reCAPTCHA API
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": secret_key,
                    "response": request.token,
                },
            )
            response.raise_for_status()
            result = response.json()
            
            # Check if verification was successful
            if not result.get("success", False):
                error_codes = result.get("error-codes", [])
                logger.warning(
                    "recaptcha_verification_failed",
                    action=request.action,
                    error_codes=error_codes,
                    message="reCAPTCHA verification failed, but allowing request to proceed",
                )
                # Return a low score response instead of raising an error
                # This allows the frontend to decide whether to block the action
                return RecaptchaVerifyResponse(
                    ok=False,
                    score=0.0,
                    action=request.action,
                    threshold=0.5 if request.action == "SIGNUP" else 0.3,
                )
            
            # Extract score and action from response
            score = result.get("score", 0.0)
            action = result.get("action", request.action)
            
            # Determine threshold based on action
            threshold = 0.5 if request.action == "SIGNUP" else 0.3
            
            # Check if score meets threshold
            if score < threshold:
                logger.warning(
                    "recaptcha_score_too_low",
                    action=request.action,
                    score=score,
                    threshold=threshold,
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"reCAPTCHA score {score} is below threshold {threshold} for action {request.action}",
                )
            
            # Log successful verification
            logger.info(
                "recaptcha_verification_success",
                action=request.action,
                score=score,
                threshold=threshold,
            )
            
            return RecaptchaVerifyResponse(
                ok=True,
                score=score,
                action=action,
                threshold=threshold,
            )
            
    except httpx.RequestError as e:
        logger.error(
            "recaptcha_verification_network_error",
            action=request.action,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="reCAPTCHA verification service unavailable",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "recaptcha_verification_error",
            action=request.action,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"reCAPTCHA verification failed: {str(e)}",
        )


@router.post("/logout")
async def logout():
    """
    Logout endpoint.
    
    Note: Actual logout happens client-side by clearing the Supabase session.
    This endpoint is informational.
    """
    return {
        "message": "Logout by calling supabase.auth.signOut() in the frontend."
    }


class CheckAccountMergeResponse(BaseModel):
    merged: bool
    message: str
    existing_account_email: Optional[str] = None


@router.post("/check-account-merge", response_model=CheckAccountMergeResponse)
async def check_account_merge(
    user: User = Depends(get_current_user),
):
    """
    Check if the current OAuth user's account should be merged with an existing email/password account.
    
    This endpoint checks if there's an existing account with the same email address.
    If Supabase Account Linking is enabled in the dashboard, Supabase will automatically
    link accounts with the same verified email address.
    
    This endpoint provides information about whether a merge occurred or is needed.
    
    Note: Actual account linking is handled by Supabase if Account Linking is enabled.
    This endpoint just provides status information.
    """
    if not user.email:
        return CheckAccountMergeResponse(
            merged=False,
            message="No email address found for current user",
        )
    
    try:
        # Check if there are multiple identities for this user (indicating merge happened)
        # We can't directly query Supabase auth.users table, but we can check if
        # the user has multiple auth methods by checking the user's identities
        
        # For now, we'll just return that Supabase handles merging automatically
        # if Account Linking is enabled in the dashboard
        
        # Check if user profile exists (indicates this might be a new OAuth account)
        profile_sql = """
            SELECT id, created_at
            FROM user_profiles
            WHERE id = $1::uuid
        """
        profile_rows = await fetch(profile_sql, user.user_id)
        
        if profile_rows:
            # Profile exists - account is set up
            # Supabase will automatically link accounts if Account Linking is enabled
            # and both accounts have the same verified email
            return CheckAccountMergeResponse(
                merged=True,
                message="Account is set up. If Account Linking is enabled in Supabase, accounts with the same email are automatically linked.",
                existing_account_email=user.email,
            )
        else:
            # No profile yet - this is a new account
            return CheckAccountMergeResponse(
                merged=False,
                message="New account created. Profile will be created automatically.",
            )
            
    except Exception as e:
        logger.error(
            "account_merge_check_failed",
            user_id=str(user.user_id),
            email=user.email,
            error=str(e),
            exc_info=True,
        )
        return CheckAccountMergeResponse(
            merged=False,
            message=f"Error checking account merge status: {str(e)}",
        )

