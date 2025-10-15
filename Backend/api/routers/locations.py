# api/routers/locations.py
from __future__ import annotations

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Gebruik jouw async engine uit app/db.py
# (Daar staat: engine: AsyncEngine = create_async_engine(...))  ✅
from app.db import engine  # type: ignore

# Maak een async session factory op basis van de bestaande engine
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


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


@router.get("/ping")
async def locations_ping() -> Dict[str, Any]:
    """Rooktest: bewijst dat de router geladen is, zonder DB-aanraking."""
    return {"ok": True, "router": "locations", "message": "loaded"}


@router.get("/", response_model=List[LocationOut])
@router.get("/", response_model=List[LocationOut])
async def list_locations(
    db: AsyncSession = Depends(get_db),
    lat: Optional[float] = Query(None, description="User latitude (optional)"),
    lng: Optional[float] = Query(None, description="User longitude (optional)"),
    radius: Optional[int] = Query(None, gt=0, le=200_000, description="Meters (optional)"),
    category: Optional[List[str]] = Query(None, description="Filter categories (repeatable)"),
    limit: int = Query(200, gt=1, le=1000),
):
    """
    Returns VERIFIED locations, safely handling lat/lng/rating regardless of column types.
    - Works if columns are TEXT (with "" etc.) or NUMERIC.
    - Filters out rows where lat/lng can't be parsed.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="DB session is None.")

    # Use E'' so backslashes in regex are respected by Postgres.
    num_regex = r'^-?[0-9]+(\.[0-9]+)?$'        # float-like
    int_regex = r'^[0-9]+$'                     # integer-like

    base_sql = f"""
        WITH cleaned AS (
            SELECT
                id,
                name,
                address,

                -- Always cast to text for checks; then trim; then regex; then cast to numeric.
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

                state
            FROM locations
            WHERE state = 'VERIFIED'
        )

        SELECT
            id, name, address, lat, lng, category, business_status,
            rating, user_ratings_total, state
        FROM cleaned
        WHERE lat IS NOT NULL AND lng IS NOT NULL
    """

    params: dict = {}

    if category:
        base_sql += " AND category = ANY(:cats)"
        params["cats"] = category

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

    base_sql += " ORDER BY id ASC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(base_sql), params)
    rows = result.mappings().all()
    return [LocationOut(**dict(r)) for r in rows]
