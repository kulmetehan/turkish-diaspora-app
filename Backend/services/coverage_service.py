from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from services.db_service import fetch
from app.workers.discovery_bot import (
    load_cities_config,
    generate_grid_points,
    meters_to_lat_deg,
    meters_to_lng_deg,
    deg_lat_to_m,
    deg_lng_to_m,
)

# Types
GridPoint = Tuple[float, float, str, str]  # (lat_center, lng_center, cell_id, district)


def _distance_sq(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    dlat = a_lat - b_lat
    dlng = a_lng - b_lng
    return dlat * dlat + dlng * dlng


def _compute_city_bbox(city_key: str) -> Optional[Tuple[float, float, float, float]]:
    cfg = load_cities_config()
    cities = cfg.get("cities", {})
    city_def = cities.get(city_key)
    if not city_def:
        return None
    districts = city_def.get("districts", {})
    if not districts:
        return None
    lat_mins: List[float] = []
    lat_maxs: List[float] = []
    lng_mins: List[float] = []
    lng_maxs: List[float] = []
    for district_data in districts.values():
        if isinstance(district_data, dict):
            if "lat_min" in district_data and "lat_max" in district_data:
                lat_mins.append(float(district_data["lat_min"]))
                lat_maxs.append(float(district_data["lat_max"]))
            if "lng_min" in district_data and "lng_max" in district_data:
                lng_mins.append(float(district_data["lng_min"]))
                lng_maxs.append(float(district_data["lng_max"]))
    if not lat_mins or not lat_maxs or not lng_mins or not lng_maxs:
        return None
    return (min(lat_mins), max(lat_maxs), min(lng_mins), max(lng_maxs))


def _build_grid_points(city: str, district: Optional[str]) -> Tuple[List[GridPoint], Tuple[float, float, float, float], int]:
    """
    Build grid points using the same logic as admin_discovery grid endpoints.
    Returns (grid_points, city_bbox, nearby_radius_m).
    """
    cfg = load_cities_config()
    cities = cfg.get("cities", {})
    if city not in cities:
        raise ValueError(f"City '{city}' not found in cities.yml")
    city_def = cities[city]
    defaults = cfg.get("defaults", {})

    grid_span_km_default = float(defaults.get("grid_span_km", 8))
    nearby_radius_m = int(defaults.get("nearby_radius_m", 1000))
    cell_spacing_m = max(100, int(nearby_radius_m * 0.75))

    districts_to_process: List[tuple[str, Dict[str, Any]]] = []
    if district:
        districts = city_def.get("districts", {})
        if district not in districts:
            raise ValueError(f"District '{district}' not found for city '{city}'")
        districts_to_process.append((district, districts[district]))
    else:
        for dist_name, dist_data in city_def.get("districts", {}).items():
            districts_to_process.append((dist_name, dist_data))

    all_grid_points: List[GridPoint] = []
    city_lat_min = float("inf")
    city_lat_max = float("-inf")
    city_lng_min = float("inf")
    city_lng_max = float("-inf")

    for dist_name, dist_data in districts_to_process:
        lat_min = float(dist_data.get("lat_min"))
        lat_max = float(dist_data.get("lat_max"))
        lng_min = float(dist_data.get("lng_min"))
        lng_max = float(dist_data.get("lng_max"))

        city_lat_min = min(city_lat_min, lat_min)
        city_lat_max = max(city_lat_max, lat_max)
        city_lng_min = min(city_lng_min, lng_min)
        city_lng_max = max(city_lng_max, lng_max)

        center_lat = (lat_min + lat_max) / 2.0
        center_lng = (lng_min + lng_max) / 2.0

        lat_span_km = deg_lat_to_m(abs(lat_max - lat_min)) / 1000.0
        lng_span_km = deg_lng_to_m(abs(lng_max - lng_min), center_lat) / 1000.0
        actual_span_km = max(lat_span_km, lng_span_km)
        grid_span_km = float(dist_data.get("grid_span_km", actual_span_km or grid_span_km_default))

        grid_points = generate_grid_points(center_lat, center_lng, grid_span_km, cell_spacing_m)
        for lat_center, lng_center in grid_points:
            lat_rounded = round(lat_center, 4)
            lng_rounded = round(lng_center, 4)
            cell_id = f"{lat_rounded}_{lng_rounded}_{nearby_radius_m}"
            all_grid_points.append((lat_center, lng_center, cell_id, dist_name))

    if not all_grid_points:
        return [], (0.0, 0.0, 0.0, 0.0), nearby_radius_m

    bbox = (city_lat_min, city_lat_max, city_lng_min, city_lng_max)
    return all_grid_points, bbox, nearby_radius_m


async def _fetch_locations_coverage(
    grid_points: Sequence[GridPoint],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
) -> Dict[str, int]:
    """
    Map OSM_OVERPASS locations within bbox/date filters to nearest grid cell_id.
    Returns dict cell_id -> count
    """
    if not grid_points:
        return {}
    all_lat_min = min(lat for lat, _, _, _ in grid_points)
    all_lat_max = max(lat for lat, _, _, _ in grid_points)
    all_lng_min = min(lng for _, lng, _, _ in grid_points)
    all_lng_max = max(lng for _, lng, _, _ in grid_points)

    sql = """
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
    rows = await fetch(sql, all_lat_min, all_lat_max, all_lng_min, all_lng_max, from_date, to_date)

    # Precompute grid centers for nearest match
    centers: List[Tuple[float, float, str]] = [(lat, lng, cell_id) for lat, lng, cell_id, _ in grid_points]
    coverage: Dict[str, int] = {}
    for r in rows or []:
        lat = r.get("lat")
        lng = r.get("lng")
        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (TypeError, ValueError):
            continue
        # nearest cell
        min_d = float("inf")
        min_cell: Optional[str] = None
        for c_lat, c_lng, c_id in centers:
            d = _distance_sq(lat_f, lng_f, c_lat, c_lng)
            if d < min_d:
                min_d = d
                min_cell = c_id
        if min_cell:
            coverage[min_cell] = coverage.get(min_cell, 0) + 1
    return coverage


async def _fetch_overpass_call_coverage(
    grid_points: Sequence[GridPoint],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
) -> Dict[str, Dict[str, Any]]:
    """
    SQL-driven aggregation over overpass_calls constrained by cell_id list and optional dates.
    Returns dict cell_id -> { call_count, error_429, error_other, first_seen_at, last_seen_at }
    """
    if not grid_points:
        return {}

    # Derive the list of relevant cell_ids from the grid definition to leverage indexes
    cell_ids: List[str] = [cell_id for _, _, cell_id, _ in grid_points]
    if not cell_ids:
        return {}

    sql = """
        SELECT
          cell_id,
          COUNT(*)::int AS total_calls,
          COUNT(*) FILTER (WHERE status_code BETWEEN 200 AND 299)::int AS successful_calls,
          COUNT(*) FILTER (WHERE status_code = 429)::int AS error_429,
          COUNT(*) FILTER (WHERE status_code >= 400 AND status_code <> 429)::int AS error_other,
          MIN(ts) AS first_seen_at,
          MAX(ts) AS last_seen_at
        FROM overpass_calls
        WHERE cell_id = ANY($1::text[])
          AND ($2::timestamptz IS NULL OR ts >= $2)
          AND ($3::timestamptz IS NULL OR ts <= $3)
        GROUP BY cell_id
    """
    rows = await fetch(sql, cell_ids, from_date, to_date)

    metrics: Dict[str, Dict[str, Any]] = {}
    for r in rows or []:
        d = dict(r)
        cid = d.get("cell_id")
        if not cid:
            continue
        metrics[str(cid)] = {
            "call_count": int(d.get("total_calls") or 0),
            "error_429": int(d.get("error_429") or 0),
            "error_other": int(d.get("error_other") or 0),
            "first_seen_at": d.get("first_seen_at"),
            "last_seen_at": d.get("last_seen_at"),
            # successful_calls is computed but not currently part of output shape; can be added if needed
            "successful_calls": int(d.get("successful_calls") or 0),
        }
    return metrics


async def _count_total_inserts_30d(bbox: Tuple[float, float, float, float]) -> int:
    lat_min, lat_max, lng_min, lng_max = bbox
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    sql = """
        SELECT COUNT(*)::int AS n
        FROM locations
        WHERE source = 'OSM_OVERPASS'
          AND first_seen_at >= $1
          AND lat BETWEEN $2 AND $3
          AND lng BETWEEN $4 AND $5
          AND lat IS NOT NULL
          AND lng IS NOT NULL
    """
    rows = await fetch(sql, thirty_days_ago, lat_min, lat_max, lng_min, lng_max)
    return int(rows[0]["n"]) if rows else 0


async def get_city_coverage_summary(
    city: str,
    district: Optional[str],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
) -> Dict[str, Any]:
    """
    Unified coverage summary for both the summary widget and the heatmap.
    Ensures:
    - historical data is included immediately
    - subdivided cells contribute
    - locations also count as coverage (same logic as heatmap)
    - total calls, errors, timestamps come from overpass_calls
    """
    grid_points, city_bbox, _ = _build_grid_points(city, district)
    # cells list to preserve ordering/coords/districts
    cell_index: Dict[str, Tuple[float, float, str]] = {
        cell_id: (lat, lng, dist) for (lat, lng, cell_id, dist) in grid_points
    }

    locations_cov = await _fetch_locations_coverage(grid_points, from_date, to_date)
    calls_cov = await _fetch_overpass_call_coverage(grid_points, from_date, to_date)

    cells: List[Dict[str, Any]] = []
    total_calls = 0
    total_error_429 = 0
    total_error_other = 0
    visited_cells = 0

    for lat, lng, cell_id, dist in grid_points:
        loc_count = int(locations_cov.get(cell_id, 0))
        call_metrics = calls_cov.get(cell_id, None)
        call_count = int(call_metrics.get("call_count", 0)) if call_metrics else 0
        error_429 = int(call_metrics.get("error_429", 0)) if call_metrics else 0
        error_other = int(call_metrics.get("error_other", 0)) if call_metrics else 0
        first_seen_at = call_metrics.get("first_seen_at") if call_metrics else None
        last_seen_at = call_metrics.get("last_seen_at") if call_metrics else None
        total = call_count

        visited = (loc_count > 0) or (call_count > 0)
        if visited:
            visited_cells += 1
        total_calls += call_count
        total_error_429 += error_429
        total_error_other += error_other

        cells.append({
            "lat_center": lat,
            "lng_center": lng,
            "district": dist,
            "location_count": loc_count,
            "call_count": call_count,
            "total_calls": total,
            "error_429": error_429,
            "error_other": error_other,
            "first_seen_at": first_seen_at,
            "last_seen_at": last_seen_at,
        })

    total_cells = len(grid_points)
    coverage_ratio = (visited_cells / total_cells) if total_cells > 0 else 0.0
    error_rate = ((total_error_429 + total_error_other) / total_calls) if total_calls > 0 else 0.0
    total_inserts_30d = await _count_total_inserts_30d(city_bbox) if total_cells > 0 else 0

    summary = {
        "visitedCells": visited_cells,
        "totalCells": total_cells,
        "coverageRatio": coverage_ratio,
        "totalCalls": total_calls,
        "errorRate": error_rate,
        "totalInserts30d": total_inserts_30d,
    }

    return {"cells": cells, "summary": summary}


