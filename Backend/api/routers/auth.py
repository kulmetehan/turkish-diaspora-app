# Backend/api/routers/auth.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel, EmailStr
from uuid import UUID

from app.deps.auth import get_current_user, User
from services.db_service import fetch, execute
from app.core.logging import get_logger

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

