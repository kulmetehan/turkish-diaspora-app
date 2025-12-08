from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel

from app.core.logging import get_logger
from app.deps.admin_auth import verify_admin_user, AdminUser
from app.workers.discovery_bot import (
    generate_grid_points,
    meters_to_lat_deg,
    meters_to_lng_deg,
    deg_lat_to_m,
    deg_lng_to_m,
    EARTH_RADIUS_M,
)
from services.db_service import fetch
from services.discovery_coverage import get_city_grid_coverage, CoverageGridCell
from services.coverage_service import get_city_coverage_summary
from services.db_service import fetch

logger = get_logger()

router = APIRouter(
    prefix="/admin/discovery",
    tags=["admin-discovery"],
)

# Type alias for grid point: (lat_center, lng_center, cell_id, district)
GridPoint = Tuple[float, float, str, str]


class GridCell(BaseModel):
    lat_center: float
    lng_center: float
    calls: int
    inserts: int
    error_429: int
    error_other: int
    district: Optional[str] = None


class DiscoveryCoverageCell(BaseModel):
    lat_center: float
    lng_center: float
    district: Optional[str] = None
    total_calls: int
    visit_count: int  # alias for total_calls
    successful_calls: int
    error_429: int
    error_other: int
    first_seen_at: Optional[datetime]
    last_seen_at: Optional[datetime]

class DiscoveryKPIDaily(BaseModel):
    day: str
    inserted: int
    deduped_fuzzy: int
    updated_existing: int
    deduped_place_id: int
    discovered: int
    failed: int

class DiscoveryKPIs(BaseModel):
    days: int
    daily: List[DiscoveryKPIDaily]
    totals: Dict[str, int]


def _generate_cell_id(lat: float, lng: float, radius: int) -> str:
    """Generate cell ID matching osm_service._generate_cell_id format."""
    lat_rounded = round(lat, 4)
    lng_rounded = round(lng, 4)
    return f"{lat_rounded}_{lng_rounded}_{radius}"


def _get_cell_bounds(lat_center: float, lng_center: float, cell_spacing_m: int) -> tuple[float, float, float, float]:
    """Calculate cell bounding box in degrees."""
    half_spacing_deg_lat = meters_to_lat_deg(cell_spacing_m / 2.0)
    half_spacing_deg_lng = meters_to_lng_deg(cell_spacing_m / 2.0, lat_center)
    
    lat_min = lat_center - half_spacing_deg_lat
    lat_max = lat_center + half_spacing_deg_lat
    lng_min = lng_center - half_spacing_deg_lng
    lng_max = lng_center + half_spacing_deg_lng
    
    return (lat_min, lat_max, lng_min, lng_max)


def _distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate approximate distance in meters between two points using Haversine formula."""
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return EARTH_RADIUS_M * c


def _find_nearest_cell(lat: float, lng: float, grid_cells: List[Tuple[float, float]]) -> Optional[int]:
    """Find the index of the nearest grid cell for a location."""
    if not grid_cells:
        return None
    
    min_distance = float('inf')
    nearest_idx = 0
    
    for idx, (cell_lat, cell_lng) in enumerate(grid_cells):
        distance = _distance_meters(lat, lng, cell_lat, cell_lng)
        if distance < min_distance:
            min_distance = distance
            nearest_idx = idx
    
    return nearest_idx


async def _fetch_grid_data(
    city: str,
    district: Optional[str],
    cities_cfg: Dict[str, Any],
) -> List[GridCell]:
    """
    Fetch discovery grid data using batched queries.
    
    This function:
    1. Generates all grid points for the requested city/districts
    2. Runs a single batched query on overpass_calls grouped by cell_id
    3. Runs a single query on locations for the city/district bbox, then matches to cells in Python
    4. Combines the results into GridCell objects
    """
    cities = cities_cfg.get("cities", {})
    if city not in cities:
        raise ValueError(f"City '{city}' not found in cities_config table")
    
    city_def = cities[city]
    defaults = cities_cfg.get("defaults", {})
    
    # Get grid parameters
    grid_span_km = float(defaults.get("grid_span_km", 8))
    nearby_radius_m = int(defaults.get("nearby_radius_m", 1000))
    cell_spacing_m = max(100, int(nearby_radius_m * 0.75))
    
    # Determine districts to process
    districts_to_process: List[tuple[str, Dict[str, Any]]] = []
    
    if district:
        # Single district
        districts = city_def.get("districts", {})
        if district not in districts:
            raise ValueError(f"District '{district}' not found for city '{city}'")
        districts_to_process.append((district, districts[district]))
    else:
        # All districts for the city
        districts = city_def.get("districts", {})
        for dist_name, dist_data in districts.items():
            districts_to_process.append((dist_name, dist_data))
    
    # Generate all grid points and cell_ids upfront
    all_grid_points: List[Tuple[float, float, str, str]] = []  # (lat, lng, cell_id, district)
    city_lat_min = float('inf')
    city_lat_max = float('-inf')
    city_lng_min = float('inf')
    city_lng_max = float('-inf')
    
    for dist_name, dist_data in districts_to_process:
        # Get district bbox
        lat_min = float(dist_data.get("lat_min"))
        lat_max = float(dist_data.get("lat_max"))
        lng_min = float(dist_data.get("lng_min"))
        lng_max = float(dist_data.get("lng_max"))
        
        # Update city bbox (union of all districts)
        city_lat_min = min(city_lat_min, lat_min)
        city_lat_max = max(city_lat_max, lat_max)
        city_lng_min = min(city_lng_min, lng_min)
        city_lng_max = max(city_lng_max, lng_max)
        
        # Calculate center and grid span
        center_lat = (lat_min + lat_max) / 2.0
        center_lng = (lng_min + lng_max) / 2.0
        
        # Calculate actual span from bbox
        lat_span_km = deg_lat_to_m(abs(lat_max - lat_min)) / 1000.0
        lng_span_km = deg_lng_to_m(abs(lng_max - lng_min), center_lat) / 1000.0
        actual_span_km = max(lat_span_km, lng_span_km)
        
        # Use district-specific grid_span_km if available
        dist_grid_span = dist_data.get("grid_span_km")
        if dist_grid_span is not None:
            grid_span_km_dist = float(dist_grid_span)
        elif actual_span_km > 0:
            grid_span_km_dist = actual_span_km
        else:
            grid_span_km_dist = grid_span_km
        
        # Generate grid points for this district
        grid_points = generate_grid_points(center_lat, center_lng, grid_span_km_dist, cell_spacing_m)
        
        # Store grid points with cell_id and district
        for lat_center, lng_center in grid_points:
            cell_id = _generate_cell_id(lat_center, lng_center, nearby_radius_m)
            all_grid_points.append((lat_center, lng_center, cell_id, dist_name))
    
    if not all_grid_points:
        return []
    
    # Extract all cell_ids for batched query
    cell_ids = [cell_id for _, _, cell_id, _ in all_grid_points]
    
    # Batched query on overpass_calls
    sql_overpass = """
        SELECT
            cell_id,
            COUNT(*)::int AS total_calls,
            COUNT(*) FILTER (WHERE status_code = 429)::int AS error_429,
            COUNT(*) FILTER (WHERE status_code >= 500 OR error_message IS NOT NULL)::int AS error_other
        FROM overpass_calls
        WHERE cell_id = ANY($1::text[])
        GROUP BY cell_id
    """
    overpass_rows = await fetch(sql_overpass, cell_ids)
    
    # Build map of cell_id -> overpass metrics
    overpass_metrics: Dict[str, Dict[str, int]] = {}
    for row in overpass_rows or []:
        row_dict = dict(row)
        cell_id = row_dict.get("cell_id")
        if cell_id:
            overpass_metrics[cell_id] = {
                "calls": int(row_dict.get("total_calls", 0)),
                "error_429": int(row_dict.get("error_429", 0)),
                "error_other": int(row_dict.get("error_other", 0)),
            }
    
    # Single query for all locations in city/district bbox (30-day window, CANDIDATE state)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    sql_locations = """
        SELECT lat, lng
        FROM locations
        WHERE state = 'CANDIDATE'
          AND first_seen_at >= $1
          AND lat BETWEEN $2 AND $3
          AND lng BETWEEN $4 AND $5
          AND lat IS NOT NULL
          AND lng IS NOT NULL
    """
    location_rows = await fetch(
        sql_locations,
        thirty_days_ago,
        city_lat_min,
        city_lat_max,
        city_lng_min,
        city_lng_max,
    )
    
    # Match locations to grid cells by finding nearest grid point
    # Build list of (lat, lng) tuples for grid cells
    grid_cells_list = [(lat, lng) for lat, lng, _, _ in all_grid_points]
    
    # Count inserts per cell
    cell_inserts: Dict[int, int] = {}
    for row in location_rows or []:
        row_dict = dict(row)
        loc_lat = float(row_dict.get("lat", 0))
        loc_lng = float(row_dict.get("lng", 0))
        
        if loc_lat == 0 or loc_lng == 0:
            continue
        
        # Find nearest grid cell
        nearest_idx = _find_nearest_cell(loc_lat, loc_lng, grid_cells_list)
        if nearest_idx is not None:
            cell_inserts[nearest_idx] = cell_inserts.get(nearest_idx, 0) + 1
    
    # Build final GridCell list
    all_cells: List[GridCell] = []
    should_include_district = district is not None or len(districts_to_process) > 1
    
    for idx, (lat_center, lng_center, cell_id, dist_name) in enumerate(all_grid_points):
        # Get overpass metrics (default to 0 if not found)
        metrics = overpass_metrics.get(cell_id, {
            "calls": 0,
            "error_429": 0,
            "error_other": 0,
        })
        
        # Get insert count (default to 0 if not found)
        inserts = cell_inserts.get(idx, 0)
        
        all_cells.append(
            GridCell(
                lat_center=lat_center,
                lng_center=lng_center,
                calls=metrics["calls"],
                inserts=inserts,
                error_429=metrics["error_429"],
                error_other=metrics["error_other"],
                district=dist_name if should_include_district else None,
            )
        )
    
    return all_cells


async def _fetch_coverage_data(
    city: str,
    district: Optional[str],
    cities_cfg: Dict[str, Any],
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> List[DiscoveryCoverageCell]:
    """
    Fetch cumulative discovery coverage data using batched queries.
    
    This function:
    1. Generates all grid points for the requested city/districts first
    2. Maps existing locations to nearest grid cells for retroactive coverage
    3. Runs a single aggregated query on overpass_calls grouped by cell_id with date filtering
    4. Merges location-based coverage with overpass_calls coverage
    5. Returns DiscoveryCoverageCell objects for all grid cells (including zero-call cells)
    
    Coverage includes both overpass API calls and existing locations, ensuring
    visit_count and total_calls reflect all discovery activity, not just logged calls.
    """
    cities = cities_cfg.get("cities", {})
    if city not in cities:
        raise ValueError(f"City '{city}' not found in cities_config table")
    
    city_def = cities[city]
    defaults = cities_cfg.get("defaults", {})
    
    # Get grid parameters
    grid_span_km = float(defaults.get("grid_span_km", 8))
    nearby_radius_m = int(defaults.get("nearby_radius_m", 1000))
    cell_spacing_m = max(100, int(nearby_radius_m * 0.75))
    
    # Determine districts to process
    districts_to_process: List[tuple[str, Dict[str, Any]]] = []
    
    if district:
        # Single district
        districts = city_def.get("districts", {})
        if district not in districts:
            raise ValueError(f"District '{district}' not found for city '{city}'")
        districts_to_process.append((district, districts[district]))
    else:
        # All districts for the city
        districts = city_def.get("districts", {})
        for dist_name, dist_data in districts.items():
            districts_to_process.append((dist_name, dist_data))
    
    # Generate all grid points and cell_ids upfront
    all_grid_points: List[Tuple[float, float, str, str]] = []  # (lat, lng, cell_id, district)
    
    for dist_name, dist_data in districts_to_process:
        # Get district bbox
        lat_min = float(dist_data.get("lat_min"))
        lat_max = float(dist_data.get("lat_max"))
        lng_min = float(dist_data.get("lng_min"))
        lng_max = float(dist_data.get("lng_max"))
        
        # Calculate center and grid span
        center_lat = (lat_min + lat_max) / 2.0
        center_lng = (lng_min + lng_max) / 2.0
        
        # Calculate actual span from bbox
        lat_span_km = deg_lat_to_m(abs(lat_max - lat_min)) / 1000.0
        lng_span_km = deg_lng_to_m(abs(lng_max - lng_min), center_lat) / 1000.0
        actual_span_km = max(lat_span_km, lng_span_km)
        
        # Use district-specific grid_span_km if available
        dist_grid_span = dist_data.get("grid_span_km")
        if dist_grid_span is not None:
            grid_span_km_dist = float(dist_grid_span)
        elif actual_span_km > 0:
            grid_span_km_dist = actual_span_km
        else:
            grid_span_km_dist = grid_span_km
        
        # Generate grid points for this district
        grid_points = generate_grid_points(center_lat, center_lng, grid_span_km_dist, cell_spacing_m)
        
        # Store grid points with cell_id and district
        for lat_center, lng_center in grid_points:
            cell_id = _generate_cell_id(lat_center, lng_center, nearby_radius_m)
            all_grid_points.append((lat_center, lng_center, cell_id, dist_name))
    
    if not all_grid_points:
        return []
    
    # Fetch locations-based coverage for retroactive coverage
    # This enables showing coverage even when historical overpass_calls logs are missing
    # Locations are mapped to nearest grid cell to ensure cell_ids match grid points
    location_coverage = await _fetch_locations_coverage(
        grid_points=all_grid_points,
        from_date=from_date,
        to_date=to_date,
    )
    
    # Extract all cell_ids for batched query
    cell_ids = [cell_id for _, _, cell_id, _ in all_grid_points]
    
    # Single aggregated query on overpass_calls with date filtering
    sql_overpass = """
        SELECT
            cell_id,
            COUNT(*)::int AS total_calls,
            COUNT(*) FILTER (WHERE status_code BETWEEN 200 AND 299)::int AS successful_calls,
            COUNT(*) FILTER (WHERE status_code = 429)::int AS error_429,
            COUNT(*) FILTER (WHERE status_code >= 500 OR error_message IS NOT NULL)::int AS error_other,
            MIN(ts) AS first_seen_at,
            MAX(ts) AS last_seen_at
        FROM overpass_calls
        WHERE cell_id = ANY($1::text[])
          AND ($2::timestamptz IS NULL OR ts >= $2)
          AND ($3::timestamptz IS NULL OR ts <= $3)
        GROUP BY cell_id
    """
    overpass_rows = await fetch(sql_overpass, cell_ids, from_date, to_date)
    
    # Build map of cell_id -> coverage metrics from overpass_calls
    coverage_metrics: Dict[str, Dict[str, Any]] = {}
    for row in overpass_rows or []:
        row_dict = dict(row)
        cell_id = row_dict.get("cell_id")
        if cell_id:
            coverage_metrics[cell_id] = {
                "total_calls": int(row_dict.get("total_calls", 0)),
                "successful_calls": int(row_dict.get("successful_calls", 0)),
                "error_429": int(row_dict.get("error_429", 0)),
                "error_other": int(row_dict.get("error_other", 0)),
                "first_seen_at": row_dict.get("first_seen_at"),
                "last_seen_at": row_dict.get("last_seen_at"),
            }
    
    # Merge locations-based coverage into overpass_calls coverage
    # Coverage now includes both overpass API calls and existing locations for retroactive visibility
    # visit_count and total_calls now include both sources, ensuring historical locations contribute to coverage
    for cell_id, location_count in location_coverage.items():
        if cell_id in coverage_metrics:
            # Augment existing overpass_calls data with locations
            coverage_metrics[cell_id]["total_calls"] += location_count
            coverage_metrics[cell_id]["successful_calls"] += location_count
            # visit_count is an alias for total_calls, so it will be updated below
            # Error counts remain from overpass_calls only (locations don't add errors)
        else:
            # Create new entry for location-only cells
            coverage_metrics[cell_id] = {
                "total_calls": location_count,
                "successful_calls": location_count,  # Conceptually: "successful discoveries"
                "error_429": 0,
                "error_other": 0,
                "first_seen_at": None,  # Leave as None for location-only cells (simplest approach)
                "last_seen_at": None,
            }
    
    # Build final DiscoveryCoverageCell list (including cells with zero calls)
    all_cells: List[DiscoveryCoverageCell] = []
    should_include_district = district is not None or len(districts_to_process) > 1
    
    for lat_center, lng_center, cell_id, dist_name in all_grid_points:
        # Get coverage metrics (default to zeros/None if not found)
        metrics = coverage_metrics.get(cell_id, {
            "total_calls": 0,
            "successful_calls": 0,
            "error_429": 0,
            "error_other": 0,
            "first_seen_at": None,
            "last_seen_at": None,
        })
        
        all_cells.append(
            DiscoveryCoverageCell(
                lat_center=lat_center,
                lng_center=lng_center,
                district=dist_name if should_include_district else None,
                total_calls=metrics["total_calls"],
                visit_count=metrics["total_calls"],  # alias
                successful_calls=metrics["successful_calls"],
                error_429=metrics["error_429"],
                error_other=metrics["error_other"],
                first_seen_at=metrics["first_seen_at"],
                last_seen_at=metrics["last_seen_at"],
            )
        )
    
    return all_cells


async def _fetch_locations_coverage(
    grid_points: Sequence[GridPoint],
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> Dict[str, int]:
    """
    Fetch coverage data from existing locations table for retroactive coverage.
    
    This enables showing coverage even when historical overpass_calls logs are missing.
    Queries OSM_OVERPASS locations within the grid bounding box and maps each location
    to its nearest grid cell to ensure cell_ids match the grid points.
    
    Args:
        grid_points: Sequence of grid points as (lat_center, lng_center, cell_id, district)
        from_date: Optional start date filter for locations
        to_date: Optional end date filter for locations
    
    Returns:
        Dictionary mapping cell_id -> location count (keys match grid point cell_ids)
    """
    try:
        if not grid_points:
            return {}
        
        # Compute bounding box from grid points for SQL query
        all_lat_min = min(lat for lat, _, _, _ in grid_points)
        all_lat_max = max(lat for lat, _, _, _ in grid_points)
        all_lng_min = min(lng for _, lng, _, _ in grid_points)
        all_lng_max = max(lng for _, lng, _, _ in grid_points)
        
        # Query locations within bounding box
        sql_locations = """
            SELECT lat, lng, first_seen_at
            FROM locations
            WHERE source = 'OSM_OVERPASS'
              AND lat BETWEEN $1 AND $2
              AND lng BETWEEN $3 AND $4
              AND ($5::timestamptz IS NULL OR first_seen_at >= $5)
              AND ($6::timestamptz IS NULL OR first_seen_at <= $6)
              AND lat IS NOT NULL
              AND lng IS NOT NULL
        """
        
        location_rows = await fetch(
            sql_locations,
            all_lat_min,
            all_lat_max,
            all_lng_min,
            all_lng_max,
            from_date,
            to_date,
        )
        
        # Aggregate locations by mapping each to its nearest grid cell
        # This ensures cell_ids match grid points, enabling location-based coverage
        location_coverage: Dict[str, int] = {}
        
        for row in location_rows or []:
            row_dict = dict(row)
            lat = row_dict.get("lat")
            lng = row_dict.get("lng")
            
            # Skip invalid coordinates
            if lat is None or lng is None:
                continue
            
            try:
                lat_float = float(lat)
                lng_float = float(lng)
                
                # Validate coordinate ranges
                if not (-90 <= lat_float <= 90) or not (-180 <= lng_float <= 180):
                    continue
                
                # Find nearest grid cell for this location
                # Use squared distance (no need for precise geodesic distance for grouping)
                min_dist_sq = float('inf')
                nearest_cell_id: Optional[str] = None
                
                for lat_center, lng_center, cell_id, _ in grid_points:
                    dist_sq = (lat_float - lat_center) ** 2 + (lng_float - lng_center) ** 2
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        nearest_cell_id = cell_id
                
                # Increment count for nearest grid cell
                if nearest_cell_id:
                    location_coverage[nearest_cell_id] = location_coverage.get(nearest_cell_id, 0) + 1
                
            except (ValueError, TypeError) as e:
                logger.debug("fetch_locations_coverage_invalid_coords", lat=lat, lng=lng, error=str(e))
                continue
        
        return location_coverage
        
    except Exception as e:
        # Log warning but don't break the endpoint - fallback to overpass_calls only
        logger.warning("fetch_locations_coverage_failed", error=str(e))
        return {}


@router.get("/grid", response_model=List[GridCell])
async def get_discovery_grid(
    city: str = Query(default="rotterdam", description="City key from cities_config table"),
    district: Optional[str] = Query(default=None, description="Optional district key"),
    category: Optional[str] = Query(default=None, description="Optional category filter"),
    admin: AdminUser = Depends(verify_admin_user),
) -> List[GridCell]:
    """
    Get unified discovery coverage cells for a city/district using shared coverage service.
    """
    try:
        # Use unified coverage service (no date filters)
        data = await asyncio.wait_for(
            get_city_coverage_summary(city, district, None, None, category),
            timeout=55.0,
        )
        cells = data.get("cells", [])
        # Backward-compatible GridCell projection
        # calls := total_calls, inserts approximated from location_count (historical presence)
        # error fields mapped 1:1
        result: List[GridCell] = []
        for c in cells:
            result.append(
                GridCell(
                    lat_center=float(c.get("lat_center")),
                    lng_center=float(c.get("lng_center")),
                    calls=int(c.get("total_calls") or 0),
                    inserts=int(c.get("location_count") or 0),
                    error_429=int(c.get("error_429") or 0),
                    error_other=int(c.get("error_other") or 0),
                    district=c.get("district"),
                )
            )
        return result
    except asyncio.TimeoutError:
        logger.warning("discovery_grid_query_timeout", city=city, district=district)
        raise HTTPException(
            status_code=504,
            detail="Discovery grid query timed out. Try filtering by district."
        )
    except ValueError as e:
        logger.warning("discovery_grid_invalid_request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("discovery_grid_query_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Discovery grid query failed"
        )


@router.get("/coverage", response_model=List[DiscoveryCoverageCell])
async def get_discovery_coverage(
    city: str = Query(..., description="City key from cities_config table"),
    district: Optional[str] = Query(None, description="Optional district key"),
    from_: Optional[datetime] = Query(None, alias="from", description="Start date (ISO format)"),
    to: Optional[datetime] = Query(None, description="End date (ISO format)"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    admin: AdminUser = Depends(verify_admin_user),
) -> List[DiscoveryCoverageCell]:
    """
    Get cumulative discovery coverage data using unified coverage service.
    """
    try:
        data = await asyncio.wait_for(
            get_city_coverage_summary(city, district, from_, to, category),
            timeout=55.0,
        )
        cells = data.get("cells", [])
        result: List[DiscoveryCoverageCell] = []
        for c in cells:
            result.append(
                DiscoveryCoverageCell(
                    lat_center=float(c.get("lat_center")),
                    lng_center=float(c.get("lng_center")),
                    district=c.get("district"),
                    total_calls=int(c.get("total_calls") or 0),
                    visit_count=int(c.get("call_count") or 0),
                    successful_calls=0,  # not computed in unified service (kept for BC)
                    error_429=int(c.get("error_429") or 0),
                    error_other=int(c.get("error_other") or 0),
                    first_seen_at=c.get("first_seen_at"),
                    last_seen_at=c.get("last_seen_at"),
                )
            )
        return result
    except asyncio.TimeoutError:
        logger.warning("discovery_coverage_query_timeout", city=city, district=district)
        raise HTTPException(
            status_code=504,
            detail="Discovery coverage query timed out. Try filtering by district or date range."
        )
    except ValueError as e:
        logger.warning("discovery_coverage_invalid_request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("discovery_coverage_query_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Discovery coverage query failed"
        )


@router.get("/summary")
async def get_discovery_summary(
    city: str = Query(..., description="City key from cities_config table"),
    district: Optional[str] = Query(None, description="Optional district key"),
    from_: Optional[datetime] = Query(None, alias="from", description="Start date (ISO format)"),
    to: Optional[datetime] = Query(None, description="End date (ISO format)"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, Any]:
    """
    Unified discovery summary for admin widget and heatmap alignment.
    """
    try:
        data = await asyncio.wait_for(
            get_city_coverage_summary(city, district, from_, to, category),
            timeout=55.0,
        )
        return data.get("summary", {})
    except asyncio.TimeoutError:
        logger.warning("discovery_summary_query_timeout", city=city, district=district)
        raise HTTPException(
            status_code=504,
            detail="Discovery summary query timed out. Try filtering by district or date range."
        )
    except ValueError as e:
        logger.warning("discovery_summary_invalid_request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("discovery_summary_query_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Discovery summary query failed"
        )

@router.get("/districts")
async def get_city_districts(
    city: str = Query(..., description="City key from cities_config table"),
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, List[str]]:
    """
    Get list of districts for a city.
    
    Returns dictionary with 'districts' key containing list of district names.
    """
    try:
        from services.cities_db_service import get_city_from_db
        
        # Load from database directly (async)
        city_data = await get_city_from_db(city)
        if not city_data:
            raise HTTPException(status_code=404, detail=f"City '{city}' not found")
        
        districts = list(city_data.get("districts", {}).keys())
        return {"districts": districts}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_load_cities_from_db", city=city, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to load cities configuration")


class CityInfo(BaseModel):
    """City information for API responses."""
    name: str
    key: str
    has_districts: bool


class CitiesResponse(BaseModel):
    """Response model for cities list."""
    cities: List[CityInfo]


@router.get("/cities", response_model=CitiesResponse)
async def get_cities(
    admin: AdminUser = Depends(verify_admin_user),
) -> CitiesResponse:
    """
    Get list of all cities from database.
    
    Returns list of cities with their names, keys, and whether they have districts.
    """
    try:
        from services.cities_db_service import load_cities_config_from_db
        cities_cfg = await load_cities_config_from_db()
        cities = cities_cfg.get("cities", {})
        
        city_list: List[CityInfo] = []
        for city_key, city_def in cities.items():
            if not isinstance(city_def, dict):
                continue
            
            city_name = city_def.get("city_name", city_key.title())
            has_districts = bool(city_def.get("districts"))
            
            city_list.append(
                CityInfo(
                    name=city_name,
                    key=city_key,
                    has_districts=has_districts,
                )
            )
        
        # Sort by key alphabetically
        city_list.sort(key=lambda c: c.key)
        
        return CitiesResponse(cities=city_list)
    except Exception as e:
        logger.error("failed_to_load_cities_config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load cities configuration"
        )

@router.get("/kpis", response_model=DiscoveryKPIs)
async def get_discovery_kpis(
    days: int = Query(30, ge=1, le=365),
    admin: AdminUser = Depends(verify_admin_user),
) -> DiscoveryKPIs:
    """
    Discovery KPIs over the last N days, aggregated from discovery_runs.counters.
    """
    sql_daily = """
        SELECT
          (date_trunc('day', COALESCE(finished_at, started_at)))::date AS day,
          COALESCE(SUM(COALESCE((counters->>'inserted')::int, 0)), 0)::int AS inserted,
          COALESCE(SUM(COALESCE((counters->>'deduped_fuzzy')::int, 0)), 0)::int AS deduped_fuzzy,
          COALESCE(SUM(COALESCE((counters->>'updated_existing')::int, 0)), 0)::int AS updated_existing,
          COALESCE(SUM(COALESCE((counters->>'deduped_place_id')::int, 0)), 0)::int AS deduped_place_id,
          COALESCE(SUM(COALESCE((counters->>'discovered')::int, 0)), 0)::int AS discovered,
          COALESCE(SUM(COALESCE((counters->>'failed')::int, 0)), 0)::int AS failed
        FROM discovery_runs
        WHERE COALESCE(finished_at, started_at) >= NOW() - (($1::int || ' days')::interval)
        GROUP BY 1
        ORDER BY day DESC
        LIMIT 60
    """
    rows_daily = await fetch(sql_daily, int(days))
    daily: List[DiscoveryKPIDaily] = []
    for r in rows_daily or []:
        d = dict(r)
        day_val = d.get("day")
        day_str = str(day_val) if isinstance(day_val, (str,)) else (day_val.isoformat() if day_val else "")
        daily.append(
            DiscoveryKPIDaily(
                day=day_str[:10],
                inserted=int(d.get("inserted") or 0),
                deduped_fuzzy=int(d.get("deduped_fuzzy") or 0),
                updated_existing=int(d.get("updated_existing") or 0),
                deduped_place_id=int(d.get("deduped_place_id") or 0),
                discovered=int(d.get("discovered") or 0),
                failed=int(d.get("failed") or 0),
            )
        )

    sql_totals = """
        SELECT
          COALESCE(SUM(COALESCE((counters->>'inserted')::int, 0)), 0)::int AS inserted,
          COALESCE(SUM(COALESCE((counters->>'deduped_fuzzy')::int, 0)), 0)::int AS deduped_fuzzy,
          COALESCE(SUM(COALESCE((counters->>'updated_existing')::int, 0)), 0)::int AS updated_existing,
          COALESCE(SUM(COALESCE((counters->>'deduped_place_id')::int, 0)), 0)::int AS deduped_place_id,
          COALESCE(SUM(COALESCE((counters->>'discovered')::int, 0)), 0)::int AS discovered,
          COALESCE(SUM(COALESCE((counters->>'failed')::int, 0)), 0)::int AS failed
        FROM discovery_runs
        WHERE COALESCE(finished_at, started_at) >= NOW() - (($1::int || ' days')::interval)
    """
    rows_tot = await fetch(sql_totals, int(days))
    trow = dict(rows_tot[0]) if rows_tot else {}
    totals = {
        "inserted": int(trow.get("inserted") or 0),
        "deduped_fuzzy": int(trow.get("deduped_fuzzy") or 0),
        "updated_existing": int(trow.get("updated_existing") or 0),
        "deduped_place_id": int(trow.get("deduped_place_id") or 0),
        "discovered": int(trow.get("discovered") or 0),
        "failed": int(trow.get("failed") or 0),
    }

    return DiscoveryKPIs(days=int(days), daily=daily, totals=totals)


class EnqueueJobsRequest(BaseModel):
    """Request model for enqueuing discovery jobs."""
    city_key: str
    categories: Optional[List[str]] = None
    districts: Optional[List[str]] = None


class EnqueueJobsResponse(BaseModel):
    """Response model for enqueuing discovery jobs."""
    jobs_created: int
    job_ids: List[str]
    preview: Dict[str, Any]


@router.post("/enqueue_jobs", response_model=EnqueueJobsResponse, status_code=status.HTTP_201_CREATED)
async def enqueue_discovery_jobs(
    body: EnqueueJobsRequest,
    admin: AdminUser = Depends(verify_admin_user),
) -> EnqueueJobsResponse:
    """
    Enqueue discovery jobs for (city, district?, category) combinations.
    
    Validates inputs, calculates preview, and creates jobs in discovery_jobs table.
    Hard limit: 200 jobs per request.
    """
    from services.discovery_jobs_service import enqueue_jobs
    from app.models.categories import get_discoverable_categories, get_all_categories
    from services.cities_db_service import get_city_from_db
    
    # Load city from database
    try:
        city_def = await get_city_from_db(body.city_key)
        if not city_def:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"City '{body.city_key}' not found in database"
            )
        
        city_districts = city_def.get("districts", {})
    except Exception as e:
        logger.error("failed_to_load_cities_for_enqueue", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load cities configuration: {e}"
        )
    
    # Determine districts
    districts_to_use: Optional[List[str]] = None
    if body.districts is not None:
        if len(body.districts) == 0:
            # Empty list means "all districts"
            districts_to_use = list(city_districts.keys()) if city_districts else None
        else:
            # Specific districts requested - validate
            invalid_districts = [d for d in body.districts if d not in city_districts]
            if invalid_districts:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid districts for city '{body.city_key}': {', '.join(invalid_districts)}"
                )
            districts_to_use = body.districts
    
    # Determine categories
    discoverable_categories = get_discoverable_categories()
    discoverable_keys = [c.key for c in discoverable_categories]
    
    if body.categories is None or len(body.categories) == 0:
        # Use all discoverable categories
        categories_to_use = discoverable_keys
    else:
        # Specific categories requested - validate
        all_category_metadata = {c.key: c for c in get_all_categories()}
        invalid_categories = [c for c in body.categories if c not in all_category_metadata]
        if invalid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid categories: {', '.join(invalid_categories)}"
            )
        
        # Check if requested categories are discoverable
        non_discoverable = [c for c in body.categories if c not in discoverable_keys]
        if non_discoverable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Categories with discovery.enabled=false: {', '.join(non_discoverable)}"
            )
        
        categories_to_use = body.categories
    
    # Calculate preview: number of jobs that will be created
    if districts_to_use is None:
        job_count = len(categories_to_use)
    else:
        job_count = len(districts_to_use) * len(categories_to_use)
    
    preview = {
        "city": body.city_key,
        "districts": districts_to_use if districts_to_use else ["city-level"],
        "categories": categories_to_use,
        "estimated_jobs": job_count,
    }
    
    # Hard limit check
    MAX_JOBS_PER_REQUEST = 200
    if job_count > MAX_JOBS_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many jobs ({job_count}). Maximum allowed per request: {MAX_JOBS_PER_REQUEST}"
        )
    
    # Enqueue jobs
    try:
        job_ids = await enqueue_jobs(
            city_key=body.city_key,
            categories=categories_to_use,
            districts=districts_to_use,
        )
        
        logger.info(
            "discovery_jobs_enqueued_via_api",
            city_key=body.city_key,
            categories=categories_to_use,
            districts=districts_to_use,
            job_count=len(job_ids),
            admin_email=admin.email,
        )
        
        return EnqueueJobsResponse(
            jobs_created=len(job_ids),
            job_ids=[str(jid) for jid in job_ids],
            preview=preview,
        )
    except Exception as e:
        logger.error(
            "enqueue_jobs_api_failed",
            city_key=body.city_key,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue jobs: {e}"
        )
