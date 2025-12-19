# Backend/api/routers/business_analytics.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Optional
from pydantic import BaseModel

from app.deps.auth import get_current_user, User
from services.business_analytics_service import get_business_analytics_service
from services.db_service import fetch
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/business/analytics", tags=["business-analytics"])


class AnalyticsOverviewResponse(BaseModel):
    total_locations: int
    approved_locations: int
    total_views: int
    total_check_ins: int
    total_reactions: int
    total_notes: int
    total_favorites: int
    trending_locations: int
    period_days: int


class LocationAnalyticsResponse(BaseModel):
    location_id: int
    views: int
    check_ins: int
    reactions: int
    notes: int
    favorites: int
    trending_score: Optional[float]
    is_trending: bool
    period_days: int


async def verify_business_account_access(
    business_account_id: int,
    user: User,
) -> None:
    """
    Verify that the user has access to the business account.
    """
    sql = """
        SELECT owner_user_id FROM business_accounts WHERE id = $1
        UNION ALL
        SELECT user_id FROM business_members
        WHERE business_account_id = $1 AND user_id = $2
        LIMIT 1
    """
    result = await fetch(sql, business_account_id, user.user_id)
    
    if not result:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You must be the owner or a member of this business account."
        )


async def get_user_business_account(user: User) -> int:
    """
    Get the business account ID for the current user.
    """
    sql = """
        SELECT id FROM business_accounts WHERE owner_user_id = $1
        LIMIT 1
    """
    result = await fetch(sql, user.user_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Business account not found"
        )
    
    return result[0]["id"]


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    period_days: int = Query(default=7, ge=1, le=365),
    user: User = Depends(get_current_user),
):
    """
    Get overview analytics for the authenticated user's business account.
    """
    business_account_id = await get_user_business_account(user)
    
    analytics_service = get_business_analytics_service()
    overview = await analytics_service.get_overview(
        business_account_id=business_account_id,
        period_days=period_days,
    )
    
    return AnalyticsOverviewResponse(**overview)


@router.get("/locations/{location_id}", response_model=LocationAnalyticsResponse)
async def get_location_analytics(
    location_id: int = Path(..., description="Location ID"),
    period_days: int = Query(default=7, ge=1, le=365),
    user: User = Depends(get_current_user),
):
    """
    Get detailed analytics for a specific location.
    """
    business_account_id = await get_user_business_account(user)
    
    analytics_service = get_business_analytics_service()
    
    try:
        analytics = await analytics_service.get_location_analytics(
            business_account_id=business_account_id,
            location_id=location_id,
            period_days=period_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return LocationAnalyticsResponse(**analytics)


@router.get("/engagement")
async def get_engagement_metrics(
    period_days: int = Query(default=7, ge=1, le=365),
    user: User = Depends(get_current_user),
):
    """
    Get engagement metrics across all locations.
    """
    business_account_id = await get_user_business_account(user)
    
    analytics_service = get_business_analytics_service()
    engagement = await analytics_service.get_engagement_metrics(
        business_account_id=business_account_id,
        period_days=period_days,
    )
    
    return engagement


@router.get("/trending")
async def get_trending_metrics(
    user: User = Depends(get_current_user),
):
    """
    Get trending statistics for claimed locations.
    """
    business_account_id = await get_user_business_account(user)
    
    analytics_service = get_business_analytics_service()
    trending = await analytics_service.get_trending_metrics(
        business_account_id=business_account_id,
    )
    
    return trending




















