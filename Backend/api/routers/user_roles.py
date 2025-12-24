# Backend/api/routers/user_roles.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone
from uuid import UUID

from app.deps.auth import get_current_user, User
from services.db_service import fetchrow, execute
from services.role_service import calculate_user_roles

router = APIRouter(prefix="/users", tags=["user-roles"])


class UserRolesResponse(BaseModel):
    """Response model for user roles."""
    primary_role: str
    secondary_role: Optional[str] = None
    earned_at: datetime
    expires_at: Optional[datetime] = None
    city_key: Optional[str] = None


@router.get("/me/roles", response_model=UserRolesResponse)
async def get_my_roles(
    user: User = Depends(get_current_user),
):
    """
    Get roles for the current authenticated user.
    Requires authentication.
    """
    sql = """
        SELECT 
            primary_role,
            secondary_role,
            earned_at,
            expires_at,
            city_key
        FROM user_roles
        WHERE user_id = $1
    """
    
    row = await fetchrow(sql, user.user_id)
    
    if not row:
        # Return default role for new users
        return UserRolesResponse(
            primary_role="yeni_gelen",
            secondary_role=None,
            earned_at=datetime.now(timezone.utc),
            expires_at=None,
            city_key=None,
        )
    
    try:
        response = UserRolesResponse(
            primary_role=row.get("primary_role"),
            secondary_role=row.get("secondary_role"),
            earned_at=row.get("earned_at"),
            expires_at=row.get("expires_at"),
            city_key=row.get("city_key"),
        )
        return response
    except Exception as e:
        raise


@router.get("/{user_id}/roles", response_model=UserRolesResponse)
async def get_user_roles(
    user_id: str = Path(..., description="User ID (UUID)"),
):
    """
    Get roles for a specific user.
    Public endpoint - anyone can view user roles.
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    sql = """
        SELECT 
            primary_role,
            secondary_role,
            earned_at,
            expires_at,
            city_key
        FROM user_roles
        WHERE user_id = $1
    """
    
    row = await fetchrow(sql, user_uuid)
    
    if not row:
        # Return default role for new users
        return UserRolesResponse(
            primary_role="yeni_gelen",
            secondary_role=None,
            earned_at=datetime.now(timezone.utc),
            expires_at=None,
            city_key=None,
        )
    
    return UserRolesResponse(
        primary_role=row.get("primary_role"),
        secondary_role=row.get("secondary_role"),
        earned_at=row.get("earned_at"),
        expires_at=row.get("expires_at"),
        city_key=row.get("city_key"),
    )


@router.post("/{user_id}/roles/recalculate")
async def recalculate_user_roles(
    user_id: str = Path(..., description="User ID (UUID)"),
    user: User = Depends(get_current_user),
):
    """
    Recalculate roles for a user.
    Requires authentication (user can recalculate their own roles, or admin for any user).
    
    This endpoint triggers a recalculation of roles based on current activity.
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    # Check if user is recalculating their own roles or is admin
    # For now, allow users to recalculate their own roles only
    # TODO: Add admin check if needed
    if user.user_id != user_uuid:
        raise HTTPException(
            status_code=403,
            detail="You can only recalculate your own roles"
        )
    
    # Calculate and update roles
    primary_role, secondary_role = await calculate_user_roles(user_uuid)
    
    return {
        "success": True,
        "primary_role": primary_role,
        "secondary_role": secondary_role,
        "message": "Roles recalculated successfully"
    }

