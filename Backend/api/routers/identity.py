# Backend/api/routers/identity.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from typing import Optional
from pydantic import BaseModel

from app.core.client_id import get_client_id
from app.core.feature_flags import FEATURE_FLAGS

router = APIRouter(prefix="/identity", tags=["identity"])


class IdentityResponse(BaseModel):
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    has_account: bool
    xp: Optional[int] = None
    current_streak_days: Optional[int] = None
    display_name: Optional[str] = None


@router.get("/me", response_model=IdentityResponse)
async def get_identity(
    request: Request,
    client_id: Optional[str] = Depends(get_client_id),
):
    """
    Get current identity (user_id if authenticated, client_id if anonymous).
    Includes basic gamification stats if available.
    """
    # TODO: Check Supabase auth session for user_id
    # For now, we only support client_id (soft identity)
    # In Fase 2, we'll add Supabase Auth integration
    
    # TODO: Fetch XP/streaks from user_streaks if user_id exists
    # For now, return None for gamification stats
    
    return IdentityResponse(
        user_id=None,  # TODO: from auth session
        client_id=client_id,
        has_account=False,  # TODO: check auth
        xp=None,
        current_streak_days=None,
        display_name=None,
    )










