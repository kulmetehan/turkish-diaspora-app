# Backend/api/routers/gamification.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.feature_flags import require_feature
from fastapi import HTTPException
from services.db_service import fetch

router = APIRouter(prefix="/users", tags=["gamification"])


class UserProfile(BaseModel):
    user_id: str
    display_name: Optional[str]
    xp: int
    current_streak_days: int
    longest_streak_days: int
    badges_count: int


class Badge(BaseModel):
    id: int
    badge_type: str
    city_key: Optional[str]
    earned_at: datetime


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    display_name: Optional[str]
    xp: int
    current_streak_days: int
    is_incognito: bool


@router.get("/{user_id}/profile", response_model=UserProfile)
async def get_user_profile(
    user_id: str = Path(..., description="User ID"),
):
    """Get user profile with XP and streaks."""
    require_feature("gamification_enabled")
    
    # Get user profile and streaks
    sql = """
        SELECT 
            us.user_id,
            up.display_name,
            us.total_xp as xp,
            us.current_streak_days,
            us.longest_streak_days,
            (SELECT COUNT(*) FROM user_badges WHERE user_id = us.user_id) as badges_count
        FROM user_streaks us
        LEFT JOIN user_profiles up ON us.user_id = up.id
        WHERE us.user_id = $1::uuid
    """
    
    rows = await fetch(sql, user_id)
    
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")
    
    row = rows[0]
    return UserProfile(
        user_id=str(row["user_id"]),
        display_name=row.get("display_name"),
        xp=row.get("xp", 0) or 0,
        current_streak_days=row.get("current_streak_days", 0) or 0,
        longest_streak_days=row.get("longest_streak_days", 0) or 0,
        badges_count=row.get("badges_count", 0) or 0,
    )


@router.get("/{user_id}/badges", response_model=List[Badge])
async def get_user_badges(
    user_id: str = Path(..., description="User ID"),
):
    """Get user badges."""
    require_feature("gamification_enabled")
    
    sql = """
        SELECT id, badge_type, city_key, earned_at
        FROM user_badges
        WHERE user_id = $1::uuid
        ORDER BY earned_at DESC
    """
    
    rows = await fetch(sql, user_id)
    
    return [
        Badge(
            id=row["id"],
            badge_type=row["badge_type"],
            city_key=row.get("city_key"),
            earned_at=row["earned_at"],
        )
        for row in rows
    ]


@router.get("/leaderboards/{city_key}", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    city_key: str = Path(..., description="City key"),
    limit: int = Query(100, le=200),
):
    """Get leaderboard for a city."""
    require_feature("gamification_enabled")
    
    sql = """
        SELECT 
            ROW_NUMBER() OVER (ORDER BY us.total_xp DESC, us.current_streak_days DESC) as rank,
            us.user_id,
            up.display_name,
            up.privacy_hide_from_leaderboards as is_incognito,
            us.total_xp as xp,
            us.current_streak_days
        FROM user_streaks us
        LEFT JOIN user_profiles up ON us.user_id = up.id
        WHERE (up.city_key = $1 OR up.city_key IS NULL)
          AND (up.privacy_hide_from_leaderboards = false OR up.privacy_hide_from_leaderboards IS NULL)
        ORDER BY us.total_xp DESC, us.current_streak_days DESC
        LIMIT $2
    """
    
    rows = await fetch(sql, city_key, limit)
    
    return [
        LeaderboardEntry(
            rank=row["rank"],
            user_id=str(row["user_id"]),
            display_name=row.get("display_name"),
            xp=row.get("xp", 0) or 0,
            current_streak_days=row.get("current_streak_days", 0) or 0,
            is_incognito=row.get("is_incognito", False) or False,
        )
        for row in rows
    ]

