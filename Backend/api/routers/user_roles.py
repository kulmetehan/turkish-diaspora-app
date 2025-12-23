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
    # #region agent log
    import json
    with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,B,C,E", "location": "user_roles.py:71", "message": "get_my_roles: function entry", "data": {"user_id": str(user.user_id), "user_type": type(user).__name__}, "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)}) + "\n")
    # #endregion
    
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
    
    # #region agent log
    import json
    with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
        # Convert datetime objects to strings for JSON serialization
        row_dict = {}
        if row:
            for key, value in dict(row).items():
                if isinstance(value, datetime):
                    row_dict[key] = value.isoformat()
                else:
                    row_dict[key] = value
        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "user_roles.py:90", "message": "get_my_roles: row from DB", "data": {"row": row_dict if row else None, "user_id": str(user.user_id)}, "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)}) + "\n")
    # #endregion
    
    if not row:
        # #region agent log
        with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "user_roles.py:93", "message": "get_my_roles: no row found, returning default", "data": {}, "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)}) + "\n")
        # #endregion
        # Return default role for new users
        return UserRolesResponse(
            primary_role="yeni_gelen",
            secondary_role=None,
            earned_at=datetime.now(timezone.utc),
            expires_at=None,
            city_key=None,
        )
    
    # #region agent log
    with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
        row_dict = dict(row) if row else {}
        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,B,E", "location": "user_roles.py:102", "message": "get_my_roles: before UserRolesResponse creation", "data": {"primary_role": row_dict.get("primary_role"), "primary_role_type": type(row_dict.get("primary_role")).__name__, "earned_at": str(row_dict.get("earned_at")) if row_dict.get("earned_at") else None, "earned_at_type": type(row_dict.get("earned_at")).__name__ if row_dict.get("earned_at") else None, "expires_at": str(row_dict.get("expires_at")) if row_dict.get("expires_at") else None}, "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)}) + "\n")
    # #endregion
    
    try:
        response = UserRolesResponse(
            primary_role=row.get("primary_role"),
            secondary_role=row.get("secondary_role"),
            earned_at=row.get("earned_at"),
            expires_at=row.get("expires_at"),
            city_key=row.get("city_key"),
        )
        # #region agent log
        with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,B,E", "location": "user_roles.py:108", "message": "get_my_roles: UserRolesResponse created successfully", "data": {}, "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)}) + "\n")
        # #endregion
        return response
    except Exception as e:
        # #region agent log
        with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,B,E", "location": "user_roles.py:110", "message": "get_my_roles: UserRolesResponse creation failed", "data": {"error": str(e), "error_type": type(e).__name__}, "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)}) + "\n")
        # #endregion
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

