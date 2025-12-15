# Backend/api/routers/stats.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Optional
from pydantic import BaseModel

from app.core.feature_flags import require_feature
from services.stats_service import get_city_stats, get_category_stats

router = APIRouter(prefix="/stats", tags=["stats"])


class CityStats(BaseModel):
    city_key: str
    check_ins_count: int
    reactions_count: int
    notes_count: int
    favorites_count: int
    poll_responses_count: int
    trending_locations_count: int
    unique_locations_count: int
    total_activity: int
    window_days: int


class CategoryStats(BaseModel):
    category_key: str
    city_key: Optional[str] = None
    check_ins_count: int
    reactions_count: int
    notes_count: int
    favorites_count: int
    poll_responses_count: int
    unique_locations_count: int
    total_activity: int
    window_days: int


@router.get("/cities/{city_key}", response_model=CityStats)
async def get_city_statistics(
    city_key: str = Path(..., description="City key (e.g., 'rotterdam', 'amsterdam')"),
    window_days: int = Query(7, ge=1, le=365, description="Time window in days (default: 7)"),
):
    """Get statistics for a specific city."""
    require_feature("check_ins_enabled")
    
    try:
        stats = await get_city_stats(city_key, window_days)
        return CityStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get city stats: {str(e)}")


@router.get("/categories/{category_key}", response_model=CategoryStats)
async def get_category_statistics(
    category_key: str = Path(..., description="Category key (e.g., 'restaurant', 'bakery')"),
    city_key: Optional[str] = Query(None, description="Optional city key to filter by"),
    window_days: int = Query(7, ge=1, le=365, description="Time window in days (default: 7)"),
):
    """Get statistics for a specific category (optionally filtered by city)."""
    require_feature("check_ins_enabled")
    
    try:
        stats = await get_category_stats(category_key, city_key, window_days)
        return CategoryStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get category stats: {str(e)}")













