from __future__ import annotations

from typing import Any, List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.db_service import fetch
from app.services.category_map import normalize_category
# Import shared filter definition (single source of truth for Admin metrics and public API)
from app.core.location_filters import get_verified_filter_sql

router = APIRouter(
    prefix="/locations",
    tags=["locations"],
)


class CategoryItem(BaseModel):
    key: str
    label: str


def parse_bbox(bbox_str: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    """
    Parse bbox query parameter from format 'west,south,east,north' to (lat_min, lat_max, lng_min, lng_max).
    
    Args:
        bbox_str: Comma-separated string "west,south,east,north" in WGS84 degrees
        
    Returns:
        Tuple of (lat_min, lat_max, lng_min, lng_max) or None if bbox_str is None/empty
        
    Raises:
        HTTPException: If bbox format is invalid or values are out of range
    """
    if not bbox_str or not bbox_str.strip():
        return None
    
    try:
        parts = [p.strip() for p in bbox_str.split(",")]
        if len(parts) != 4:
            raise HTTPException(
                status_code=400,
                detail="bbox must have exactly 4 comma-separated values: west,south,east,north"
            )
        
        west, south, east, north = [float(p) for p in parts]
        
        # Validate ranges
        if not (-180 <= west <= 180) or not (-180 <= east <= 180):
            raise HTTPException(
                status_code=400,
                detail="bbox longitude values must be between -180 and 180"
            )
        if not (-90 <= south <= 90) or not (-90 <= north <= 90):
            raise HTTPException(
                status_code=400,
                detail="bbox latitude values must be between -90 and 90"
            )
        if west >= east:
            raise HTTPException(
                status_code=400,
                detail="bbox west must be less than east"
            )
        if south >= north:
            raise HTTPException(
                status_code=400,
                detail="bbox south must be less than north"
            )
        
        # Convert from (west, south, east, north) to (lat_min, lat_max, lng_min, lng_max)
        # for get_verified_filter_sql()
        return (south, north, west, east)
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"bbox values must be numeric: {str(e)}"
        )

@router.get("/ping")
async def ping() -> dict[str, Any]:
    """
    Health check that also verifies DB connectivity.
    """
    try:
        await fetch("SELECT 1")
        return {"ok": True, "router": "locations", "db": True}
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")


@router.get("", response_model=List[dict])
async def list_locations(
    state: str = Query(
        "VERIFIED",
        description="Client hint only. Server enforces its own visibility rules.",
    ),
    bbox: Optional[str] = Query(
        None,
        description="Bounding box in format 'west,south,east,north' (WGS84 degrees). Example: 4.1,51.8,4.7,52.0",
    ),
    limit: int = Query(
        200,
        gt=1,
        le=10000,
        description="Max number of records to return (2..10000)",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
):
    """
    Public list of diaspora locations for the map.

    Visibility rules:
    - Always include rows that are already VERIFIED and not retired,
      with confidence_score >= 0.80 (using shared filter definition).
    - ALSO include high-confidence (>=0.90) rows that are still
      PENDING_VERIFICATION or CANDIDATE and not retired.
      These are auto-surfaced "almost certainly Turkish" places.

    We never return RETIRED and we skip anything with low/null confidence.

    Query parameters:
    - bbox: Optional bounding box filter (west,south,east,north). If provided, only
      locations within the bounding box are returned.
    - limit: Maximum number of records to return (default 200, max 10000).
    - offset: Number of records to skip for pagination (default 0).

    NOTE: This endpoint uses the shared filter definition from
    app.core.location_filters to maintain parity with Admin metrics.

    NOTE: we are using asyncpg via services.db_service.fetch(), not SQLAlchemy.
    """
    
    # Parse and validate bbox
    bbox_tuple = parse_bbox(bbox)
    
    # Use shared filter definition for VERIFIED locations (single source of truth)
    # This ensures parity with Admin metrics verified count
    # Use "l" alias for locations table
    verified_filter_sql, verified_params = get_verified_filter_sql(bbox=bbox_tuple, alias="l")
    
    # High-confidence PENDING/CANDIDATE filter (additional to shared VERIFIED filter)
    # Apply bbox filter to pending filter as well
    pending_conditions = [
        "l.state IN ('PENDING_VERIFICATION', 'CANDIDATE')",
        "(l.confidence_score IS NOT NULL AND l.confidence_score >= 0.90)",
        "(l.is_retired = false OR l.is_retired IS NULL)",
        "l.lat IS NOT NULL",
        "l.lng IS NOT NULL",
    ]
    
    # Add bbox filter to pending if provided
    pending_params = []
    param_num = len(verified_params) + 1
    if bbox_tuple:
        lat_min, lat_max, lng_min, lng_max = bbox_tuple
        pending_conditions.append(f"l.lat BETWEEN ${param_num} AND ${param_num + 1}")
        pending_conditions.append(f"l.lng BETWEEN ${param_num + 2} AND ${param_num + 3}")
        pending_params = [float(lat_min), float(lat_max), float(lng_min), float(lng_max)]
        param_num += 4
    
    pending_filter_sql = " AND ".join(pending_conditions)
    
    # Combine both filters with OR
    # Parameter placeholders: verified_params use $1, $2, etc.
    # pending_params continue from where verified_params end
    all_params = list(verified_params) + pending_params
    
    # Calculate parameter numbers for LIMIT and OFFSET
    limit_param_num = len(all_params) + 1
    offset_param_num = len(all_params) + 2
    
    sql = f"""
        SELECT
            l.id,
            l.name,
            l.address,
            l.lat,
            l.lng,
            l.category,
            l.rating,
            l.state,
            l.confidence_score,
            COALESCE(blc.status::text, NULL) as claim_status
        FROM locations l
        LEFT JOIN business_location_claims blc ON l.id = blc.location_id
        WHERE ({verified_filter_sql}) OR ({pending_filter_sql})
        ORDER BY l.id DESC
        LIMIT ${limit_param_num} OFFSET ${offset_param_num}
    """
    
    # Combine parameters: verified_params, pending_params, limit, offset
    all_params = all_params + [limit, offset]
    
    # Log request parameters
    print(f"[locations] query: bbox={bbox}, limit={limit}, offset={offset}, params_count={len(all_params)}")

    try:
        data = await fetch(sql, *all_params)
        rows = [dict(r) for r in data]

        # Normalize field types for the frontend
        for r in rows:
            # force id to string for React key stability
            r["id"] = str(r.get("id"))

            # lat / lng to floats
            if r.get("lat") is not None:
                try:
                    r["lat"] = float(r["lat"])
                except Exception:
                    r["lat"] = None
            else:
                r["lat"] = None

            if r.get("lng") is not None:
                try:
                    r["lng"] = float(r["lng"])
                except Exception:
                    r["lng"] = None
            else:
                r["lng"] = None

            # numeric fields that might come back as Decimal / str
            if r.get("rating") is not None:
                try:
                    r["rating"] = float(r["rating"])
                except Exception:
                    r["rating"] = None

            if r.get("confidence_score") is not None:
                try:
                    r["confidence_score"] = float(r["confidence_score"])
                except Exception:
                    pass

            # Category normalization enrichment for frontend
            try:
                cat_info = normalize_category(str(r.get("category") or ""))
                r["category_raw"] = cat_info.get("category_raw")
                r["category_key"] = cat_info.get("category_key")
                r["category_label"] = cat_info.get("category_label")
            except Exception:
                # Best-effort fallback to raw values if normalization fails
                raw = r.get("category")
                r["category_raw"] = raw
                r["category_key"] = str(raw).strip().lower().replace("/", "_").replace(" ", "_") if raw else "other"
                # Simple labelization
                try:
                    tmp = str(raw or "").replace("/", " ").replace("_", " ").strip()
                    r["category_label"] = " ".join([t[:1].upper() + t[1:].lower() for t in tmp.split()]) or "Overig"
                except Exception:
                    r["category_label"] = "Overig"
            
            # Verified badge based on claim status
            claim_status = r.get("claim_status")
            r["has_verified_badge"] = (claim_status == "approved")

        return rows

    except Exception as e:
        print(f"[locations] query failed: {e}")
        raise HTTPException(status_code=503, detail="database unavailable")


@router.get("/", response_model=List[dict])
async def list_locations_slash(
    state: str = Query(
        "VERIFIED",
        description="Client hint only. Server enforces its own visibility rules.",
    ),
    bbox: Optional[str] = Query(
        None,
        description="Bounding box in format 'west,south,east,north' (WGS84 degrees). Example: 4.1,51.8,4.7,52.0",
    ),
    limit: int = Query(
        200,
        gt=1,
        le=10000,
        description="Max number of records to return (2..10000)",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
):
    return await list_locations(state=state, bbox=bbox, limit=limit, offset=offset)


@router.get("/count")
async def count_locations(
    bbox: Optional[str] = Query(
        None,
        description="Bounding box in format 'west,south,east,north' (WGS84 degrees). Example: 4.1,51.8,4.7,52.0",
    ),
) -> dict[str, int]:
    """
    Get total count of locations matching the same filters as the list endpoint.
    
    Returns the count of locations that are:
    - VERIFIED with confidence_score >= 0.80, not retired, with valid coordinates
    - OR PENDING_VERIFICATION/CANDIDATE with confidence_score >= 0.90, not retired, with valid coordinates
    
    If bbox is provided, only counts locations within the bounding box.
    
    Returns:
        Dictionary with "count" key containing the total number of matching locations.
    """
    
    # Parse and validate bbox
    bbox_tuple = parse_bbox(bbox)
    
    # Use shared filter definition for VERIFIED locations (single source of truth)
    verified_filter_sql, verified_params = get_verified_filter_sql(bbox=bbox_tuple)
    
    # High-confidence PENDING/CANDIDATE filter (same as list endpoint)
    pending_conditions = [
        "state IN ('PENDING_VERIFICATION', 'CANDIDATE')",
        "(confidence_score IS NOT NULL AND confidence_score >= 0.90)",
        "(is_retired = false OR is_retired IS NULL)",
        "lat IS NOT NULL",
        "lng IS NOT NULL",
    ]
    
    # Add bbox filter to pending if provided
    pending_params = []
    param_num = len(verified_params) + 1
    if bbox_tuple:
        lat_min, lat_max, lng_min, lng_max = bbox_tuple
        pending_conditions.append(f"lat BETWEEN ${param_num} AND ${param_num + 1}")
        pending_conditions.append(f"lng BETWEEN ${param_num + 2} AND ${param_num + 3}")
        pending_params = [float(lat_min), float(lat_max), float(lng_min), float(lng_max)]
    
    pending_filter_sql = " AND ".join(pending_conditions)
    
    # Combine both filters with OR
    all_params = list(verified_params) + pending_params
    
    sql = f"""
        SELECT COUNT(*) as count
        FROM locations
        WHERE ({verified_filter_sql}) OR ({pending_filter_sql})
    """
    
    # Log request parameters
    print(f"[locations/count] query: bbox={bbox}, params_count={len(all_params)}")
    
    try:
        result = await fetch(sql, *all_params)
        count = int(dict(result[0]).get("count", 0)) if result else 0
        return {"count": count}
    except Exception as e:
        print(f"[locations/count] query failed: {e}")
        raise HTTPException(status_code=503, detail="database unavailable")


@router.get("/categories", response_model=List[CategoryItem])
async def list_categories() -> List[CategoryItem]:
    """
    Get all available categories from VERIFIED locations.
    Returns distinct category_key and category_label pairs.
    """
    sql = """
        SELECT DISTINCT category
        FROM locations
        WHERE state = 'VERIFIED'
          AND category IS NOT NULL
          AND category <> ''
        ORDER BY category
    """
    
    try:
        rows = await fetch(sql)
        unique: dict[str, str] = {}
        
        for row in rows:
            r = dict(row)
            raw_category = str(r.get("category") or "").strip()
            if not raw_category:
                continue
            
            # Normalize using same logic as /locations endpoint
            try:
                cat_info = normalize_category(raw_category)
                key = (cat_info.get("category_key") or "").strip().lower()
                label = (cat_info.get("category_label") or "").strip()
            except Exception:
                # Fallback: simple normalization if normalize_category fails
                key = raw_category.lower().strip().replace("/", "_").replace(" ", "_")
                tmp = raw_category.replace("/", " ").replace("_", " ").strip()
                label = " ".join([t[:1].upper() + t[1:].lower() for t in tmp.split()]) if tmp else raw_category
            
            # Skip empty keys and "other" category
            if not key or key == "other":
                continue
            
            # Use first occurrence (label may vary, but key should be stable)
            if key not in unique:
                unique[key] = label or key
        
        # Build response sorted by key
        items = [
            CategoryItem(key=k, label=v)
            for k, v in sorted(unique.items(), key=lambda kv: kv[0])
        ]
        return items
    except Exception as e:
        print(f"[categories] query failed: {e}")
        raise HTTPException(status_code=503, detail="database unavailable")
