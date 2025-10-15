# api/routers/locations.py
from __future__ import annotations

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Gebruik jouw async engine uit app/db.py
from app.db import engine  # type: ignore

# Async session factory
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


# ---------- Response schema ----------

class LocationOut(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    lat: float
    lng: float
    category: Optional[str] = None
    business_status: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    state: Optional[str] = None


# ---------- Health ----------

@router.get("/ping")
async def locations_ping() -> Dict[str, Any]:
    """Rooktest: bewijst dat de router geladen is, zonder DB-aanraking."""
    return {"ok": True, "router": "locations", "message": "loaded"}


# ---------- List endpoint ----------

@router.get("/", response_model=List[LocationOut])
async def list_locations(
    db: AsyncSession = Depends(get_db),
    # Geo
    lat: Optional[float] = Query(None, description="User latitude (optional)"),
    lng: Optional[float] = Query(None, description="User longitude (optional)"),
    radius: Optional[int] = Query(None, gt=0, le=200_000, description="Meters (optional)"),
    # Filters
    category: Optional[List[str]] = Query(None, description="Filter categories (repeatable)"),
    state: Optional[List[str]] = Query(None, description="Filter by states (default VERIFIED)"),
    only_turkish: bool = Query(False, description="Filter to AI-identified Turkish diaspora"),
    min_confidence: float = Query(0.8, ge=0.0, le=1.0, description="Confidence threshold for only_turkish"),
    # Pagination
    limit: int = Query(200, gt=1, le=1000),
):
    """
    Returns locations (default: VERIFIED) with robust casting for lat/lng/rating etc.
    - Works if columns are TEXT (with quotes/empty) or NUMERIC.
    - Filters out rows where lat/lng can't be parsed.
    - When only_turkish=true: requires AI evidence (confidence_score >= min_confidence OR notes contains Turkish signal).
    """
    if db is None:
        raise HTTPException(status_code=500, detail="DB session is None.")

    # Default states
    states = state or ["VERIFIED"]

    # Regex voor type-checks
    num_regex = r'^-?[0-9]+(\.[0-9]+)?$'        # float-like
    int_regex = r'^[0-9]+$'                     # integer-like

    # Basis CTE die velden schoon cast
    base_sql = f"""
        WITH cleaned AS (
            SELECT
                id,
                name,
                address,

                -- Always cast to text for checks; trim; regex; then cast to numeric.
                CASE
                  WHEN TRIM((lat)::text) ~ E'{num_regex}'
                  THEN (TRIM((lat)::text))::double precision
                  ELSE NULL
                END AS lat,

                CASE
                  WHEN TRIM((lng)::text) ~ E'{num_regex}'
                  THEN (TRIM((lng)::text))::double precision
                  ELSE NULL
                END AS lng,

                category,
                business_status,

                CASE
                  WHEN TRIM((rating)::text) ~ E'{num_regex}'
                  THEN (TRIM((rating)::text))::double precision
                  ELSE NULL
                END AS rating,

                CASE
                  WHEN TRIM((user_ratings_total)::text) ~ E'{int_regex}'
                  THEN (TRIM((user_ratings_total)::text))::int
                  ELSE NULL
                END AS user_ratings_total,

                state,

                -- AI velden alleen intern voor filtering (niet in response)
                CASE
                  WHEN TRIM((confidence_score)::text) ~ E'{num_regex}'
                  THEN (TRIM((confidence_score)::text))::double precision
                  ELSE NULL
                END AS confidence_score,

                NULLIF(TRIM((notes)::text), '') AS notes
            FROM locations
            WHERE state = ANY(:states)
        )

        SELECT
            id, name, address, lat, lng, category, business_status,
            rating, user_ratings_total, state
        FROM cleaned
        WHERE lat IS NOT NULL AND lng IS NOT NULL
    """

    params: dict = {"states": states}

    # Categoriefilter
    if category:
        base_sql += " AND category = ANY(:cats)"
        params["cats"] = category

    # Geo-radius (haversine, meters)
    if lat is not None and lng is not None and radius is not None:
        base_sql += """
        AND (
            6371000 * 2 * ASIN(
                SQRT(
                    POWER(SIN(RADIANS(lat - :lat) / 2), 2) +
                    COS(RADIANS(:lat)) * COS(RADIANS(lat)) *
                    POWER(SIN(RADIANS(lng - :lng) / 2), 2)
                )
            )
        ) <= :radius
        """
        params.update({"lat": lat, "lng": lng, "radius": radius})

    # AI-gedreven Turkse filter
    if only_turkish:
        base_sql += """
        AND (
            (EXISTS (
                SELECT 1
                FROM cleaned c2
                WHERE c2.id = cleaned.id
                  AND c2.confidence_score IS NOT NULL
                  AND c2.confidence_score >= :min_confidence
            ))
            OR
            (notes ILIKE :tr1 OR notes ILIKE :tr2 OR notes ILIKE :tr3 OR notes ILIKE :tr4)
        )
        """
        params["min_confidence"] = float(min_confidence)
        # Subset van veel voorkomende varianten
        params["tr1"] = "%Turks%"
        params["tr2"] = "%Turkse%"
        params["tr3"] = "%Turkish%"
        params["tr4"] = "%Türk%"

    # Sortering en limiet
    base_sql += """
        ORDER BY
          CASE WHEN rating IS NULL THEN 1 ELSE 0 END,  -- NULLS LAST
          rating DESC,
          id ASC
        LIMIT :limit
    """
    params["limit"] = limit

    result = await db.execute(text(base_sql), params)
    rows = result.mappings().all()
    return [LocationOut(**dict(r)) for r in rows]
