# Backend/api/routers/profiles.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from starlette.requests import Request
from typing import Optional, List, Literal
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

from app.core.feature_flags import require_feature
from app.core.client_id import get_client_id
from app.deps.auth import get_current_user, get_current_user_optional, User
from services.db_service import fetch, fetchrow, execute
from services.xp_service import award_xp
from services.badge_service import _award_badge
from services.activity_summary_service import update_user_activity_summary
from services.role_service import assign_role, ROLE_YENI_GELEN

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


class ActivitySummaryResponse(BaseModel):
    user_id: str
    last_4_weeks_active_days: int
    last_activity_date: Optional[datetime]
    total_söz_count: int
    total_check_in_count: int
    total_poll_response_count: int
    city_key: Optional[str]
    updated_at: datetime


class WeekFeedbackResponse(BaseModel):
    should_show: bool
    message: str
    week_start: datetime


@router.get("/me", response_model=CurrentUserResponse)
async def get_user_profile(
    request: Request,
    user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get current user profile (name and avatar).
    Returns null values for anonymous users or if no profile exists.
    """
    user_id = user.user_id if user else None
    
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
    # NOTE: We do NOT normalize display_name here (unlike in activity endpoints)
    # because users should see their actual display_name in their profile,
    # even if it's a UUID. The normalization only happens in activity feeds
    # where we want to show "Anonieme gebruiker" instead of UUIDs.
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


@router.get("/me/check-username")
async def check_username_available(
    username: str = Query(..., min_length=2, max_length=50),
    user: User = Depends(get_current_user),
):
    """Check if username is available (case-insensitive, excluding current user)."""
    require_feature("check_ins_enabled")
    
    # Normalize username (trim and lowercase for comparison)
    normalized_username = username.strip().lower()
    
    # Check if username exists for other users
    sql = """
        SELECT id FROM user_profiles 
        WHERE LOWER(TRIM(display_name)) = $1 
        AND id != $2::uuid
    """
    rows = await fetch(sql, normalized_username, user.user_id)
    return {"available": len(rows) == 0}


class UsernameChangeStatusResponse(BaseModel):
    can_change: bool
    last_change: Optional[datetime] = None
    next_change_available: Optional[datetime] = None
    days_remaining: int = 0


@router.get("/me/username-change-status", response_model=UsernameChangeStatusResponse)
async def get_username_change_status(
    user: User = Depends(get_current_user),
):
    """Check if user can change username (1x per month limit)."""
    require_feature("check_ins_enabled")
    
    sql = """
        SELECT display_name, last_username_change
        FROM user_profiles
        WHERE id = $1::uuid
    """
    rows = await fetch(sql, user.user_id)
    
    if not rows:
        return UsernameChangeStatusResponse(
            can_change=True,
            last_change=None,
            next_change_available=None,
            days_remaining=0,
        )
    
    row = rows[0]
    display_name = row.get("display_name")
    last_change = row.get("last_username_change")
    
    # Special case: If display_name equals user_id (UUID), allow change regardless of limit
    # This fixes cases where UUID was accidentally saved as display_name
    current_is_uuid = display_name and display_name.strip() == str(user.user_id)
    
    if current_is_uuid:
        return UsernameChangeStatusResponse(
            can_change=True,
            last_change=last_change,
            next_change_available=None,
            days_remaining=0,
        )
    
    if not last_change:
        return UsernameChangeStatusResponse(
            can_change=True,
            last_change=None,
            next_change_available=None,
            days_remaining=0,
        )
    
    # Parse datetime if it's a string
    if isinstance(last_change, str):
        from dateutil import parser
        last_change = parser.parse(last_change)
    
    # Ensure timezone-aware
    if last_change.tzinfo is None:
        last_change = last_change.replace(tzinfo=timezone.utc)
    else:
        last_change = last_change.astimezone(timezone.utc)
    
    # Calculate days since change
    now = datetime.now(timezone.utc)
    days_since_change = (now - last_change).days
    
    can_change = days_since_change >= 30
    days_remaining = max(0, 30 - days_since_change) if not can_change else 0
    next_change_available = (last_change + timedelta(days=30)) if not can_change else None
    
    return UsernameChangeStatusResponse(
        can_change=can_change,
        last_change=last_change,
        next_change_available=next_change_available,
        days_remaining=days_remaining,
    )


@router.put("/me/profile", response_model=UserProfile)
async def update_user_profile(
    request: Request,
    profile: UserProfileUpdate,
    user: User = Depends(get_current_user),
):
    """Update own user profile. Requires authentication."""
    require_feature("check_ins_enabled")
    
    user_id = user.user_id
    
    # Track if username changed (will be used later to update last_username_change)
    username_changed = False
    
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
        
        # Check username uniqueness (case-insensitive)
        check_sql = """
            SELECT id FROM user_profiles 
            WHERE LOWER(TRIM(display_name)) = LOWER(TRIM($1)) 
            AND id != $2::uuid
        """
        existing = await fetch(check_sql, display_name, user_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Username already taken"
            )
        
        # Check if username actually changed and enforce 1x per month limit
        current_sql = """
            SELECT display_name, last_username_change
            FROM user_profiles
            WHERE id = $1::uuid
        """
        current_rows = await fetch(current_sql, user_id)
        current_display_name = current_rows[0].get("display_name") if current_rows else None
        
        # Check if username actually changed
        if current_display_name and current_display_name.strip().lower() != display_name.lower():
            username_changed = True
            
            # Special case: If current display_name equals user_id (UUID), allow change regardless of limit
            # This fixes cases where UUID was accidentally saved as display_name
            current_is_uuid = current_display_name.strip() == str(user_id)
            
            if not current_is_uuid:
                # Only enforce 30-day limit if current display_name is NOT a UUID
                last_change = current_rows[0].get("last_username_change")
                if last_change:
                    # Parse datetime if it's a string
                    if isinstance(last_change, str):
                        from dateutil import parser
                        last_change = parser.parse(last_change)
                    
                    # Ensure timezone-aware
                    if last_change.tzinfo is None:
                        last_change = last_change.replace(tzinfo=timezone.utc)
                    else:
                        last_change = last_change.astimezone(timezone.utc)
                    
                    # Check if 30 days have passed
                    now = datetime.now(timezone.utc)
                    days_since_change = (now - last_change).days
                    
                    if days_since_change < 30:
                        days_remaining = 30 - days_since_change
                        raise HTTPException(
                            status_code=400,
                            detail=f"Username can only be changed once per month. Next change available in {days_remaining} days."
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
    # Start parameter numbering at 6 because INSERT uses $1-$5
    param_num = 6
    
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
    
    # Add last_username_change if username changed
    if username_changed:
        updates.append("last_username_change = now()")
    
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
    # Parameters: $1-$5 for INSERT, $6+ for UPDATE SET
    all_params = [
        user_id,  # $1
        final_values["display_name"],  # $2
        final_values["avatar_url"],  # $3
        final_values["city_key"],  # $4
        final_values["language_pref"],  # $5
    ] + values  # $6+ for UPDATE SET
    
    result_rows = await fetch(upsert_sql, *all_params)
    
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
    user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get onboarding status for current user.
    Returns first_run=true for anonymous users or if no profile exists.
    """
    user_id = user.user_id if user else None
    
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
    user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Complete onboarding flow.
    Updates user profile (authenticated) or onboarding_responses (anonymous) with onboarding data.
    Awards XP and badge for authenticated users.
    """
    user_id = user.user_id if user else None
    
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
            
            # Assign "yeni_gelen" role (only for authenticated users)
            role_assigned = False
            try:
                await assign_role(
                    user_id=user_id,
                    role=ROLE_YENI_GELEN,
                    city_key=home_city_key,
                    is_primary=True
                )
                # Verify role was assigned successfully
                verify_sql = """
                    SELECT primary_role FROM user_roles WHERE user_id = $1
                """
                verify_row = await fetchrow(verify_sql, user_id)
                if verify_row and verify_row.get("primary_role") == ROLE_YENI_GELEN:
                    role_assigned = True
                    from app.core.logging import get_logger
                    logger = get_logger()
                    logger.info(
                        "onboarding_role_assignment_success",
                        user_id=str(user_id),
                        role=ROLE_YENI_GELEN,
                        city_key=home_city_key
                    )
                else:
                    from app.core.logging import get_logger
                    logger = get_logger()
                    logger.error(
                        "onboarding_role_assignment_verification_failed",
                        user_id=str(user_id),
                        expected_role=ROLE_YENI_GELEN,
                        actual_role=verify_row.get("primary_role") if verify_row else None
                    )
            except Exception as e:
                # Log with full details for debugging
                from app.core.logging import get_logger
                logger = get_logger()
                logger.error(
                    "onboarding_role_assignment_failed",
                    extra={
                        "user_id": str(user_id),
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "home_city_key": home_city_key,
                        "role": ROLE_YENI_GELEN,
                    },
                    exc_info=True
                )
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


@router.get("/me/activity-summary", response_model=ActivitySummaryResponse)
async def get_my_activity_summary(
    request: Request,
    user: User = Depends(get_current_user),
):
    """
    Get activity summary for the current authenticated user.
    Creates summary if it doesn't exist (lazy initialization).
    """
    require_feature("check_ins_enabled")
    
    user_id = user.user_id
    
    # Try to fetch existing summary
    sql = """
        SELECT 
            user_id,
            last_4_weeks_active_days,
            last_activity_date,
            total_söz_count,
            total_check_in_count,
            total_poll_response_count,
            city_key,
            updated_at
        FROM user_activity_summary
        WHERE user_id = $1
    """
    rows = await fetch(sql, user_id)
    
    if not rows:
        # Summary doesn't exist, create it via service (lazy initialization)
        await update_user_activity_summary(user_id=user_id)
        
        # Fetch again after creation
        rows = await fetch(sql, user_id)
        
        if not rows:
            # Still not found after creation, return empty summary
            return ActivitySummaryResponse(
                user_id=str(user_id),
                last_4_weeks_active_days=0,
                last_activity_date=None,
                total_söz_count=0,
                total_check_in_count=0,
                total_poll_response_count=0,
                city_key=None,
                updated_at=datetime.now(),
            )
    
    row = rows[0]
    return ActivitySummaryResponse(
        user_id=str(row["user_id"]),
        last_4_weeks_active_days=int(row.get("last_4_weeks_active_days", 0) or 0),
        last_activity_date=row.get("last_activity_date"),
        total_söz_count=int(row.get("total_söz_count", 0) or 0),
        total_check_in_count=int(row.get("total_check_in_count", 0) or 0),
        total_poll_response_count=int(row.get("total_poll_response_count", 0) or 0),
        city_key=row.get("city_key"),
        updated_at=row.get("updated_at"),
    )


@router.get("/me/week-feedback", response_model=WeekFeedbackResponse)
async def get_week_feedback(
    request: Request,
    user: User = Depends(get_current_user),
):
    """
    Get week-feedback status for the current authenticated user.
    Returns whether to show the week-feedback card in the feed.
    """
    require_feature("check_ins_enabled")
    
    user_id = str(user.user_id)
    
    # Calculate current week start (Monday 00:00:00 UTC)
    now = datetime.now(timezone.utc)
    days_since_monday = now.weekday()  # Monday = 0
    week_start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    
    # Fetch activity summary
    sql = """
        SELECT 
            last_4_weeks_active_days,
            last_activity_date
        FROM user_activity_summary
        WHERE user_id = $1
    """
    rows = await fetch(sql, user_id)
    
    if not rows:
        # No activity summary, user hasn't been active
        return WeekFeedbackResponse(
            should_show=False,
            message="Bu hafta aktiftin. Mahalle seni gördü.",
            week_start=week_start,
        )
    
    row = rows[0]
    last_activity_date = row.get("last_activity_date")
    last_4_weeks_active_days = int(row.get("last_4_weeks_active_days", 0) or 0)
    
    # Normalize last_activity_date to UTC-aware datetime if it exists
    if last_activity_date:
        if isinstance(last_activity_date, datetime):
            # If naive, assume UTC; if aware, convert to UTC
            if last_activity_date.tzinfo is None:
                last_activity_date = last_activity_date.replace(tzinfo=timezone.utc)
            else:
                last_activity_date = last_activity_date.astimezone(timezone.utc)
    
    # Check if user was active this week
    # User is considered active this week if:
    # 1. They have at least 1 active day in last 4 weeks
    # 2. Their last activity was within the current week
    should_show = False
    if last_4_weeks_active_days >= 1 and last_activity_date:
        # Check if last activity was within current week
        if last_activity_date >= week_start:
            should_show = True
    
    return WeekFeedbackResponse(
        should_show=should_show,
        message="Bu hafta aktiftin. Mahalle seni gördü.",
        week_start=week_start,
    )


class NoteSummary(BaseModel):
    id: int
    location_id: int
    location_name: str
    content_preview: str
    created_at: datetime


class CheckInSummary(BaseModel):
    id: int
    location_id: int
    location_name: str
    created_at: datetime


class ContributionsResponse(BaseModel):
    last_notes: List[NoteSummary]
    last_check_ins: List[CheckInSummary]
    poll_response_count: int


@router.get("/me/contributions", response_model=ContributionsResponse)
async def get_my_contributions(
    request: Request,
    user: User = Depends(get_current_user),
):
    """
    Get recent contributions for the current authenticated user.
    Returns last 3 notes, last 3 check-ins, and poll response count.
    """
    require_feature("check_ins_enabled")
    
    user_id = user.user_id
    
    # Fetch last 3 notes
    notes_sql = """
        SELECT 
            ln.id,
            ln.location_id,
            l.name as location_name,
            LEFT(ln.content, 50) as content_preview,
            ln.created_at
        FROM location_notes ln
        JOIN locations l ON ln.location_id = l.id
        WHERE ln.user_id = $1
        ORDER BY ln.created_at DESC
        LIMIT 3
    """
    notes_rows = await fetch(notes_sql, user_id)
    last_notes = [
        NoteSummary(
            id=row["id"],
            location_id=row["location_id"],
            location_name=row.get("location_name", "Unknown"),
            content_preview=row.get("content_preview", ""),
            created_at=row["created_at"],
        )
        for row in notes_rows
    ]
    
    # Fetch last 3 check-ins
    check_ins_sql = """
        SELECT 
            ci.id,
            ci.location_id,
            l.name as location_name,
            ci.created_at
        FROM check_ins ci
        JOIN locations l ON ci.location_id = l.id
        WHERE ci.user_id = $1
        ORDER BY ci.created_at DESC
        LIMIT 3
    """
    check_ins_rows = await fetch(check_ins_sql, user_id)
    last_check_ins = [
        CheckInSummary(
            id=row["id"],
            location_id=row["location_id"],
            location_name=row.get("location_name", "Unknown"),
            created_at=row["created_at"],
        )
        for row in check_ins_rows
    ]
    
    # Count poll responses
    poll_sql = """
        SELECT COUNT(*) as count
        FROM activity_stream
        WHERE actor_id = $1
        AND actor_type = 'user'
        AND activity_type = 'poll_response'
    """
    poll_rows = await fetch(poll_sql, user_id)
    poll_response_count = int(poll_rows[0].get("count", 0) or 0) if poll_rows else 0
    
    return ContributionsResponse(
        last_notes=last_notes,
        last_check_ins=last_check_ins,
        poll_response_count=poll_response_count,
    )


class RecognitionEntry(BaseModel):
    category: str
    title: str
    period: str
    rank: int
    context: Optional[str] = None


class RecognitionResponse(BaseModel):
    recognitions: List[RecognitionEntry]


def _get_category_title(category: str) -> str:
    """Get display title for a leaderboard category."""
    titles = {
        "soz_hafta": "Bu Haftanın Sözü",
        "mahalle_gururu": "Mahallenin Gururu",
        "sessiz_guç": "Sessiz Güç",
        "diaspora_nabzı": "Diaspora Nabzı",
    }
    return titles.get(category, category)


def _determine_period(period_start: datetime, period_end: datetime) -> str:
    """Determine period string from period bounds."""
    now = datetime.now(timezone.utc)
    
    # Calculate time differences
    time_since_start = now - period_start
    time_until_end = period_end - now
    
    # If period started today, it's "today"
    if time_since_start.days == 0:
        return "today"
    # If period started within last 7 days, it's "week"
    elif time_since_start.days < 7:
        return "week"
    # Otherwise, it's "month"
    else:
        return "month"


@router.get("/me/recognition", response_model=RecognitionResponse)
async def get_my_recognition(
    request: Request,
    user: User = Depends(get_current_user),
):
    """
    Get active recognitions for the current authenticated user.
    Returns leaderboard entries where the user is currently ranked.
    """
    require_feature("check_ins_enabled")
    
    user_id = user.user_id
    
    # Query active leaderboard entries for this user
    sql = """
        SELECT 
            le.category,
            le.rank,
            le.period_start,
            le.period_end,
            le.context_data
        FROM leaderboard_entries le
        WHERE le.user_id = $1
        AND le.period_start <= NOW()
        AND le.period_end >= NOW()
        AND le.rank IS NOT NULL
        ORDER BY le.period_start DESC
    """
    
    rows = await fetch(sql, user_id)
    
    recognitions: List[RecognitionEntry] = []
    for row in rows:
        category = row.get("category")
        rank = row.get("rank")
        period_start = row.get("period_start")
        period_end = row.get("period_end")
        context_data = row.get("context_data") or {}
        
        # Determine period string
        period = _determine_period(period_start, period_end)
        
        # Get display title
        title = _get_category_title(category)
        
        # Extract context from context_data
        context = None
        if isinstance(context_data, dict):
            if context_data.get("location_id"):
                # Try to get location name
                loc_sql = "SELECT name FROM locations WHERE id = $1"
                loc_rows = await fetch(loc_sql, context_data.get("location_id"))
                if loc_rows:
                    context = loc_rows[0].get("name")
            elif context_data.get("note_id"):
                context = f"Söz #{context_data.get('note_id')}"
            elif context_data.get("poll_id"):
                context = f"Poll #{context_data.get('poll_id')}"
        
        recognitions.append(
            RecognitionEntry(
                category=category,
                title=title,
                period=period,
                rank=rank,
                context=context,
            )
        )
    
    return RecognitionResponse(recognitions=recognitions)





















