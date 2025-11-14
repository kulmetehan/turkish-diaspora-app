from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from app.core.logging import get_logger
from app.deps.admin_auth import verify_admin_user, AdminUser
from app.workers.discovery_bot import (
    load_cities_config,
    generate_grid_points,
    meters_to_lat_deg,
    meters_to_lng_deg,
    deg_lat_to_m,
    deg_lng_to_m,
    EARTH_RADIUS_M,
)
from services.db_service import fetch

logger = get_logger()

router = APIRouter(
    prefix="/admin/discovery",
    tags=["admin-discovery"],
)


class GridCell(BaseModel):
    lat_center: float
    lng_center: float
    calls: int
    inserts: int
    error_429: int
    error_other: int
    district: Optional[str] = None


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
        raise ValueError(f"City '{city}' not found in cities.yml")
    
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


@router.get("/grid", response_model=List[GridCell])
async def get_discovery_grid(
    city: str = Query(default="rotterdam", description="City key from cities.yml"),
    district: Optional[str] = Query(default=None, description="Optional district key"),
    admin: AdminUser = Depends(verify_admin_user),
) -> List[GridCell]:
    """
    Get discovery grid coverage data for a city/district.
    
    Returns grid cells with statistics:
    - calls: total overpass API calls for this cell
    - inserts: number of CANDIDATE locations created in last 30 days within cell bounds
    - error_429: number of 429 (rate limit) errors
    - error_other: number of other errors (5xx or error_message present)
    """
    # Load cities config
    try:
        cities_cfg = load_cities_config()
    except Exception as e:
        logger.error("failed_to_load_cities_config", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to load cities configuration")
    
    # Fetch grid data with timeout
    try:
        result = await asyncio.wait_for(
            _fetch_grid_data(city, district, cities_cfg),
            timeout=55.0
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
