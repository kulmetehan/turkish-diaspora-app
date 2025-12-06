# Backend/api/routers/profiles.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from starlette.requests import Request
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.feature_flags import require_feature
from services.db_service import fetch, execute

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



