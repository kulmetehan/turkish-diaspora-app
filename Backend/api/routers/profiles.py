# Backend/api/routers/profiles.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from starlette.requests import Request
from typing import Optional, List, Literal
from pydantic import BaseModel
from datetime import datetime

from app.core.feature_flags import require_feature
from app.core.client_id import get_client_id
from services.db_service import fetch, execute
from services.xp_service import award_xp
from services.badge_service import _award_badge

router = APIRouter(prefix="/users", tags=["profiles"])


class UserProfile(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    city_key: Optional[str] = None
    language_pref: str = "nl"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    city_key: Optional[str] = None
    language_pref: Optional[str] = None
    home_city: Optional[str] = None
    home_region: Optional[str] = None
    memleket: Optional[List[str]] = None
    gender: Optional[Literal["male", "female", "prefer_not_to_say"]] = None


class CurrentUserResponse(BaseModel):
    """Response model for /users/me endpoint (matches frontend CurrentUser interface)."""
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class OnboardingStatusResponse(BaseModel):
    first_run: bool
    onboarding_completed: bool
    onboarding_version: Optional[str] = None


class OnboardingCompleteRequest(BaseModel):
    home_city: str
    home_region: Optional[str] = None
    home_city_key: Optional[str] = None  # CityKey for news preferences
    memleket: Optional[List[str]] = None
    gender: Optional[Literal["male", "female", "prefer_not_to_say"]] = None


class OnboardingCompleteResponse(BaseModel):
    success: bool
    xp_awarded: int
    badge_earned: Optional[str] = None


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    request: Request,
    # TODO: user_id: UUID = Depends(get_current_user_required),
):
    """
    Get current user profile (name and avatar).
    Returns null values for anonymous users or if no profile exists.
    """
    # TODO: Extract user_id from auth session when available
    user_id = None
    
    if not user_id:
        # Return null values for anonymous users
        return CurrentUserResponse(name=None, avatar_url=None)
    
    # Fetch user profile
    sql = """
        SELECT display_name, avatar_url
        FROM user_profiles
        WHERE id = $1::uuid
    """
    rows = await fetch(sql, user_id)
    
    if not rows:
        return CurrentUserResponse(name=None, avatar_url=None)
    
    row = rows[0]
    return CurrentUserResponse(
        name=row.get("display_name"),
        avatar_url=row.get("avatar_url"),
    )


@router.get("/{user_id}/profile", response_model=UserProfile)
async def get_user_profile(
    user_id: str = Path(..., description="User ID (UUID)"),
):
    """Get user profile by user ID."""
    require_feature("check_ins_enabled")  # Or create separate flag
    
    sql = """
        SELECT 
            id as user_id,
            display_name,
            avatar_url,
            city_key,
            language_pref,
            created_at,
            updated_at
        FROM user_profiles
        WHERE id = $1::uuid
    """
    
    rows = await fetch(sql, user_id)
    
    if not rows:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    row = rows[0]
    return UserProfile(
        user_id=str(row["user_id"]),
        display_name=row.get("display_name"),
        avatar_url=row.get("avatar_url"),
        city_key=row.get("city_key"),
        language_pref=row.get("language_pref", "nl") or "nl",
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.put("/me/profile", response_model=UserProfile)
async def update_user_profile(
    request: Request,
    profile: UserProfileUpdate,
    # TODO: user_id: UUID = Depends(get_current_user_required),
):
    """Update own user profile. Requires authentication."""
    require_feature("check_ins_enabled")
    
    user_id = None  # TODO: Extract from auth session when available
    
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required to update profile"
        )
    
    # Validate display_name if provided
    if profile.display_name is not None:
        display_name = profile.display_name.strip()
        if len(display_name) < 2:
            raise HTTPException(
                status_code=400,
                detail="Display name must be at least 2 characters"
            )
        if len(display_name) > 50:
            raise HTTPException(
                status_code=400,
                detail="Display name must be at most 50 characters"
            )
    
    # Validate language_pref if provided
    if profile.language_pref is not None:
        if profile.language_pref not in ("nl", "tr", "en"):
            raise HTTPException(
                status_code=400,
                detail="language_pref must be one of: nl, tr, en"
            )
    
    # Build update SQL dynamically
    updates = []
    values = []
    param_num = 1
    
    if profile.display_name is not None:
        updates.append(f"display_name = ${param_num}")
        values.append(profile.display_name.strip())
        param_num += 1
    
    if profile.avatar_url is not None:
        updates.append(f"avatar_url = ${param_num}")
        values.append(profile.avatar_url.strip() if profile.avatar_url else None)
        param_num += 1
    
    if profile.city_key is not None:
        updates.append(f"city_key = ${param_num}")
        values.append(profile.city_key.strip() if profile.city_key else None)
        param_num += 1
    
    if profile.language_pref is not None:
        updates.append(f"language_pref = ${param_num}")
        values.append(profile.language_pref)
        param_num += 1
    
    if profile.home_city is not None:
        updates.append(f"home_city = ${param_num}")
        values.append(profile.home_city.strip() if profile.home_city else None)
        param_num += 1
    
    if profile.home_region is not None:
        updates.append(f"home_region = ${param_num}")
        values.append(profile.home_region.strip() if profile.home_region else None)
        param_num += 1
    
    if profile.memleket is not None:
        updates.append(f"memleket = ${param_num}")
        values.append(profile.memleket if profile.memleket else None)
        param_num += 1
    
    if profile.gender is not None:
        if profile.gender not in ("male", "female", "prefer_not_to_say"):
            raise HTTPException(
                status_code=400,
                detail="gender must be one of: male, female, prefer_not_to_say"
            )
        updates.append(f"gender = ${param_num}")
        values.append(profile.gender)
        param_num += 1
    
    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No profile fields provided to update"
        )
    
    # Add updated_at
    updates.append("updated_at = now()")
    
    updates_str = ", ".join(updates)
    
    # Upsert profile
    upsert_sql = f"""
        INSERT INTO user_profiles (id, display_name, avatar_url, city_key, language_pref, created_at, updated_at)
        VALUES ($1::uuid, $2, $3, $4, $5, now(), now())
        ON CONFLICT (id)
        DO UPDATE SET {updates_str}
        RETURNING id as user_id, display_name, avatar_url, city_key, language_pref, created_at, updated_at
    """
    
    # Get current values for missing fields
    get_sql = """
        SELECT display_name, avatar_url, city_key, language_pref
        FROM user_profiles
        WHERE id = $1::uuid
    """
    current_rows = await fetch(get_sql, user_id)
    
    # Build full values for INSERT
    current = {
        "display_name": None,
        "avatar_url": None,
        "city_key": None,
        "language_pref": "nl",
    }
    if current_rows:
        row = current_rows[0]
        current["display_name"] = row.get("display_name")
        current["avatar_url"] = row.get("avatar_url")
        current["city_key"] = row.get("city_key")
        current["language_pref"] = row.get("language_pref", "nl") or "nl"
    
    # Merge provided values with current
    final_values = {
        "display_name": profile.display_name.strip() if profile.display_name is not None else current["display_name"],
        "avatar_url": profile.avatar_url.strip() if profile.avatar_url is not None else current["avatar_url"],
        "city_key": profile.city_key.strip() if profile.city_key is not None else current["city_key"],
        "language_pref": profile.language_pref if profile.language_pref is not None else current["language_pref"],
    }
    
    # Execute upsert
    result_rows = await fetch(
        upsert_sql,
        user_id,
        final_values["display_name"],
        final_values["avatar_url"],
        final_values["city_key"],
        final_values["language_pref"],
    )
    
    if not result_rows:
        raise HTTPException(status_code=500, detail="Failed to update profile")
    
    row = result_rows[0]
    return UserProfile(
        user_id=str(row["user_id"]),
        display_name=row.get("display_name"),
        avatar_url=row.get("avatar_url"),
        city_key=row.get("city_key"),
        language_pref=row.get("language_pref", "nl") or "nl",
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.get("/me/onboarding-status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    request: Request,
    client_id: Optional[str] = Depends(get_client_id),
):
    """
    Get onboarding status for current user.
    Returns first_run=true for anonymous users or if no profile exists.
    """
    # TODO: Extract user_id from auth session when available
    user_id = None
    
    if not user_id:
        # Anonymous users or no profile: return first_run=true
        return OnboardingStatusResponse(
            first_run=True,
            onboarding_completed=False,
            onboarding_version=None,
        )
    
    # Fetch onboarding status from user_profiles
    sql = """
        SELECT first_run, onboarding_completed, onboarding_version
        FROM user_profiles
        WHERE id = $1::uuid
    """
    rows = await fetch(sql, user_id)
    
    if not rows:
        # No profile exists: treat as first run
        return OnboardingStatusResponse(
            first_run=True,
            onboarding_completed=False,
            onboarding_version=None,
        )
    
    row = rows[0]
    return OnboardingStatusResponse(
        first_run=row.get("first_run", True) if row.get("first_run") is not None else True,
        onboarding_completed=row.get("onboarding_completed", False) if row.get("onboarding_completed") is not None else False,
        onboarding_version=row.get("onboarding_version"),
    )


@router.post("/me/onboarding/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(
    request: Request,
    data: OnboardingCompleteRequest,
    client_id: Optional[str] = Depends(get_client_id),
):
    """
    Complete onboarding flow.
    Updates user profile (authenticated) or onboarding_responses (anonymous) with onboarding data.
    Awards XP and badge for authenticated users.
    """
    # TODO: Extract user_id from auth session when available
    user_id = None
    
    # Require either user_id (authenticated) or client_id (anonymous)
    if not user_id and not client_id:
        raise HTTPException(
            status_code=400,
            detail="Either authentication or X-Client-Id header is required"
        )
    
    # Validate home_city (required)
    if not data.home_city or not data.home_city.strip():
        raise HTTPException(
            status_code=400,
            detail="home_city is required"
        )
    
    # Validate gender if provided
    if data.gender is not None and data.gender not in ("male", "female", "prefer_not_to_say"):
        raise HTTPException(
            status_code=400,
            detail="gender must be one of: male, female, prefer_not_to_say"
        )
    
    try:
        # Normalize memleket array
        memleket_array = data.memleket if data.memleket else None
        # Normalize home_city_key (lowercase)
        home_city_key = data.home_city_key.lower().strip() if data.home_city_key and data.home_city_key.strip() else None
        
        if user_id:
            # Authenticated user: update user_profiles
            update_sql = """
                UPDATE user_profiles
                SET 
                    home_city = $1,
                    home_region = $2,
                    memleket = $3,
                    gender = $4,
                    onboarding_completed = true,
                    first_run = false,
                    onboarding_completed_at = now(),
                    updated_at = now()
                WHERE id = $5::uuid
                RETURNING id
            """
            
            result_rows = await fetch(
                update_sql,
                data.home_city.strip(),
                data.home_region.strip() if data.home_region else None,
                memleket_array,
                data.gender,
                user_id,
            )
            
            if not result_rows:
                raise HTTPException(
                    status_code=404,
                    detail="User profile not found"
                )
            
            # Award 10 XP for onboarding completion (only for authenticated users)
            xp_awarded = 0
            try:
                xp_success = await award_xp(
                    user_id=user_id,
                    client_id=client_id,
                    source="onboarding",
                    amount=10,
                )
                if xp_success:
                    xp_awarded = 10
            except Exception as e:
                # Log but don't fail the request if XP award fails
                from app.core.logging import get_logger
                logger = get_logger()
                logger.warning("onboarding_xp_award_failed", user_id=user_id, error=str(e))
            
            # Award "nieuwkomer" badge (only for authenticated users)
            badge_earned = None
            try:
                badge_success = await _award_badge(user_id, "nieuwkomer", None)
                if badge_success:
                    badge_earned = "nieuwkomer"
            except Exception as e:
                # Log but don't fail the request if badge award fails
                from app.core.logging import get_logger
                logger = get_logger()
                logger.warning("onboarding_badge_award_failed", user_id=user_id, error=str(e))
        else:
            # Anonymous user: upsert onboarding_responses
            upsert_sql = """
                INSERT INTO onboarding_responses (
                    client_id, home_city, home_region, home_city_key, 
                    memleket, gender, onboarding_version, completed_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, now(), now())
                ON CONFLICT (client_id)
                DO UPDATE SET
                    home_city = EXCLUDED.home_city,
                    home_region = EXCLUDED.home_region,
                    home_city_key = EXCLUDED.home_city_key,
                    memleket = EXCLUDED.memleket,
                    gender = EXCLUDED.gender,
                    onboarding_version = EXCLUDED.onboarding_version,
                    completed_at = EXCLUDED.completed_at,
                    updated_at = now()
                RETURNING id
            """
            
            result_rows = await fetch(
                upsert_sql,
                client_id,
                data.home_city.strip(),
                data.home_region.strip() if data.home_region else None,
                home_city_key,
                memleket_array,
                data.gender,
                "v1.0",
            )
            
            if not result_rows:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to save onboarding response"
                )
            
            # No XP or badges for anonymous users
            xp_awarded = 0
            badge_earned = None
        
        return OnboardingCompleteResponse(
            success=True,
            xp_awarded=xp_awarded,
            badge_earned=badge_earned,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete onboarding: {str(e)}"
        )




















