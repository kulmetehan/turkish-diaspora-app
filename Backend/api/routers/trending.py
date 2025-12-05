# Backend/api/routers/trending.py
from __future__ import annotations

from fastapi import APIRouter, Query, Path, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.core.feature_flags import require_feature
from services.db_service import fetch

router = APIRouter(prefix="/locations", tags=["trending"])

# Additional router for /trending/locations endpoint
trending_alt_router = APIRouter(prefix="/trending", tags=["trending"])


class TrendingLocation(BaseModel):
    location_id: int
    name: str
    city_key: str
    category_key: Optional[str]
    score: float
    rank: int
    check_ins_count: int
    reactions_count: int
    notes_count: int
    has_verified_badge: bool = False
    is_promoted: bool = False


@router.get("/trending", response_model=List[TrendingLocation])
async def get_trending_locations(
    city_key: Optional[str] = Query(None, description="Filter by city"),
    category_key: Optional[str] = Query(None, description="Filter by category"),
    window: str = Query("24h", description="Time window: 5m, 1h, 24h, 7d"),
    limit: int = Query(20, le=100),
):
    """Get trending locations."""
    require_feature("trending_enabled")
    
    if window not in ('5m', '1h', '24h', '7d'):
        raise HTTPException(
            status_code=400,
            detail="window must be one of: 5m, 1h, 24h, 7d"
        )
    
    sql = """
        SELECT 
            tl.location_id,
            l.name,
            tl.city_key,
            tl.category_key,
            tl.score,
            tl.rank,
            tl.check_ins_count,
            tl.reactions_count,
            tl.notes_count,
            COALESCE(blc.status::text, NULL) as claim_status,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                THEN true 
                ELSE false 
            END as is_promoted,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                THEN tl.score * 1.5 
                ELSE tl.score 
            END as boosted_score
        FROM trending_locations tl
        JOIN locations l ON tl.location_id = l.id
        LEFT JOIN business_location_claims blc ON l.id = blc.location_id
        LEFT JOIN promoted_locations pl ON pl.location_id = tl.location_id 
            AND pl.status = 'active'
            AND pl.promotion_type IN ('trending', 'both')
            AND pl.starts_at <= now()
            AND pl.ends_at > now()
        WHERE tl.window = $1
          AND ($2::text IS NULL OR tl.city_key = $2)
          AND ($3::text IS NULL OR tl.category_key = $3)
        ORDER BY is_promoted DESC, boosted_score DESC, tl.rank ASC
        LIMIT $4
    """
    
    rows = await fetch(sql, window, city_key, category_key, limit)
    
    return [
        TrendingLocation(
            location_id=row["location_id"],
            name=row["name"],
            city_key=row["city_key"],
            category_key=row.get("category_key"),
            score=float(row["boosted_score"]),
            rank=row["rank"],
            check_ins_count=row.get("check_ins_count", 0) or 0,
            reactions_count=row.get("reactions_count", 0) or 0,
            notes_count=row.get("notes_count", 0) or 0,
            has_verified_badge=(row.get("claim_status") == "approved"),
            is_promoted=row.get("is_promoted", False),
        )
        for row in rows
    ]


@router.get("/cities/{city_key}/trending", response_model=List[TrendingLocation])
async def get_city_trending(
    city_key: str = Path(..., description="City key"),
    category_key: Optional[str] = Query(None, description="Filter by category"),
    window: str = Query("24h", description="Time window"),
    limit: int = Query(20, le=100),
):
    """Get trending locations for a specific city."""
    require_feature("trending_enabled")
    
    if window not in ('5m', '1h', '24h', '7d'):
        raise HTTPException(
            status_code=400,
            detail="window must be one of: 5m, 1h, 24h, 7d"
        )
    
    sql = """
        SELECT 
            tl.location_id,
            l.name,
            tl.city_key,
            tl.category_key,
            tl.score,
            tl.rank,
            tl.check_ins_count,
            tl.reactions_count,
            tl.notes_count,
            COALESCE(blc.status::text, NULL) as claim_status,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                THEN true 
                ELSE false 
            END as is_promoted,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                THEN tl.score * 1.5 
                ELSE tl.score 
            END as boosted_score
        FROM trending_locations tl
        JOIN locations l ON tl.location_id = l.id
        LEFT JOIN business_location_claims blc ON l.id = blc.location_id
        LEFT JOIN promoted_locations pl ON pl.location_id = tl.location_id 
            AND pl.status = 'active'
            AND pl.promotion_type IN ('trending', 'both')
            AND pl.starts_at <= now()
            AND pl.ends_at > now()
        WHERE tl.window = $1
          AND tl.city_key = $2
          AND ($3::text IS NULL OR tl.category_key = $3)
        ORDER BY is_promoted DESC, boosted_score DESC, tl.rank ASC
        LIMIT $4
    """
    
    rows = await fetch(sql, window, city_key, category_key, limit)
    
    return [
        TrendingLocation(
            location_id=row["location_id"],
            name=row["name"],
            city_key=row["city_key"],
            category_key=row.get("category_key"),
            score=float(row["boosted_score"]),
            rank=row["rank"],
            check_ins_count=row.get("check_ins_count", 0) or 0,
            reactions_count=row.get("reactions_count", 0) or 0,
            notes_count=row.get("notes_count", 0) or 0,
            has_verified_badge=(row.get("claim_status") == "approved"),
            is_promoted=row.get("is_promoted", False),
        )
        for row in rows
    ]


@trending_alt_router.get("/locations", response_model=List[TrendingLocation])
async def get_trending_locations_alt(
    city_key: Optional[str] = Query(None, description="Filter by city"),
    category_key: Optional[str] = Query(None, description="Filter by category"),
    window: str = Query("24h", description="Time window: 5m, 1h, 24h, 7d"),
    limit: int = Query(20, le=100),
):
    """Get trending locations (alternative endpoint at /trending/locations)."""
    require_feature("trending_enabled")
    
    if window not in ('5m', '1h', '24h', '7d'):
        raise HTTPException(
            status_code=400,
            detail="window must be one of: 5m, 1h, 24h, 7d"
        )
    
    sql = """
        SELECT 
            tl.location_id,
            l.name,
            tl.city_key,
            tl.category_key,
            tl.score,
            tl.rank,
            tl.check_ins_count,
            tl.reactions_count,
            tl.notes_count,
            COALESCE(blc.status::text, NULL) as claim_status,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                THEN true 
                ELSE false 
            END as is_promoted,
            CASE 
                WHEN pl.id IS NOT NULL AND pl.status = 'active' 
                THEN tl.score * 1.5 
                ELSE tl.score 
            END as boosted_score
        FROM trending_locations tl
        JOIN locations l ON tl.location_id = l.id
        LEFT JOIN business_location_claims blc ON l.id = blc.location_id
        LEFT JOIN promoted_locations pl ON pl.location_id = tl.location_id 
            AND pl.status = 'active'
            AND pl.promotion_type IN ('trending', 'both')
            AND pl.starts_at <= now()
            AND pl.ends_at > now()
        WHERE tl.window = $1
          AND ($2::text IS NULL OR tl.city_key = $2)
          AND ($3::text IS NULL OR tl.category_key = $3)
        ORDER BY is_promoted DESC, boosted_score DESC, tl.rank ASC
        LIMIT $4
    """
    
    rows = await fetch(sql, window, city_key, category_key, limit)
    
    return [
        TrendingLocation(
            location_id=row["location_id"],
            name=row["name"],
            city_key=row["city_key"],
            category_key=row.get("category_key"),
            score=float(row["boosted_score"]),
            rank=row["rank"],
            check_ins_count=row.get("check_ins_count", 0) or 0,
            reactions_count=row.get("reactions_count", 0) or 0,
            notes_count=row.get("notes_count", 0) or 0,
            has_verified_badge=(row.get("claim_status") == "approved"),
            is_promoted=row.get("is_promoted", False),
        )
        for row in rows
    ]

