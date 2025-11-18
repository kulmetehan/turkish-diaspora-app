# -*- coding: utf-8 -*-
"""
DiscoveryBot — Grid-based discovery met YAML category-mapping + district support
- Leest Infra/config/categories.yml als bron voor diaspora->OSM tags
- Leest Infra/config/cities.yml voor district-bounding boxes
- CLI flags: chunking, caps per categorie, district-selectie
- OSM-only discovery using free Overpass API

Pad: Backend/app/workers/discovery_bot.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Dict, Any, Set, Tuple, Optional
from uuid import UUID

# --- Uniform logging ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="discovery_bot")

# ---------------------------------------------------------------------------
# Pathing zodat 'app.*' werkt (CI, GH Actions, lokale run)
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent           # .../Backend/app
BACKEND_DIR = APP_DIR.parent                # .../Backend
REPO_ROOT = BACKEND_DIR.parent              # .../

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))    # .../Backend

# ---------------------------------------------------------------------------
# DB (asyncpg helpers)
# ---------------------------------------------------------------------------
from services.db_service import init_db_pool, fetch, execute

# ---------------------------------------------------------------------------
# Places provider (OSM only)
# ---------------------------------------------------------------------------
from services.osm_service import OsmPlacesService

# ---------------------------------------------------------------------------
# Worker run tracking
# ---------------------------------------------------------------------------
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    update_worker_run_progress,
    finish_worker_run,
)

# ---------------------------------------------------------------------------
# YAML Config loaders
# ---------------------------------------------------------------------------
import yaml

CATEGORIES_YML = REPO_ROOT / "Infra" / "config" / "categories.yml"
CITIES_YML = REPO_ROOT / "Infra" / "config" / "cities.yml"

def load_categories_config() -> Dict[str, Any]:
    if not CATEGORIES_YML.exists():
        raise FileNotFoundError(f"Config niet gevonden: {CATEGORIES_YML}")
    data = yaml.safe_load(CATEGORIES_YML.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "categories" not in data:
        raise ValueError("categories.yml is ongeldig: mist 'categories' root-key.")
    return data

def load_cities_config() -> Dict[str, Any]:
    if not CITIES_YML.exists():
        raise FileNotFoundError(f"Config niet gevonden: {CITIES_YML}")
    data = yaml.safe_load(CITIES_YML.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "cities" not in data:
        raise ValueError("cities.yml is ongeldig: mist 'cities' root-key.")
    return data

# ---------------------------------------------------------------------------
# Geo helpers
# ---------------------------------------------------------------------------
EARTH_RADIUS_M = 6371000.0

def meters_to_lat_deg(m: float) -> float:
    return (m / EARTH_RADIUS_M) * (180.0 / math.pi)

def meters_to_lng_deg(m: float, at_lat_deg: float) -> float:
    return (m / (EARTH_RADIUS_M * math.cos(math.radians(at_lat_deg)))) * (180.0 / math.pi)

def deg_lat_to_m(deg: float) -> float:
    return deg * math.pi / 180.0 * EARTH_RADIUS_M

def deg_lng_to_m(deg: float, at_lat_deg: float) -> float:
    return deg * math.pi / 180.0 * EARTH_RADIUS_M * math.cos(math.radians(at_lat_deg))

def generate_grid_points(center_lat: float, center_lng: float, grid_span_km: float, cell_spacing_m: int) -> List[Tuple[float, float]]:
    half_span_m = grid_span_km * 1000
    lat_step = meters_to_lat_deg(cell_spacing_m)
    lng_step = meters_to_lng_deg(cell_spacing_m, center_lat)

    lat_min = center_lat - meters_to_lat_deg(half_span_m)
    lat_max = center_lat + meters_to_lat_deg(half_span_m)
    lng_min = center_lng - meters_to_lng_deg(half_span_m, center_lat)
    lng_max = center_lng + meters_to_lng_deg(half_span_m, center_lat)

    pts: List[Tuple[float, float]] = []
    lat = lat_min
    while lat <= lat_max:
        lng = lng_min
        while lng <= lng_max:
            pts.append((lat, lng))
            lng += lng_step
        lat += lat_step
    return pts

def pick_chunk(points: List[Tuple[float, float]], chunks: int, chunk_index: int) -> List[Tuple[float, float]]:
    if chunks <= 1:
        return points
    n = len(points)
    size = (n + chunks - 1) // chunks
    start = chunk_index * size
    end = min(start + size, n)
    return points[start:end]

# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------
def map_place_to_row(p: Dict[str, Any], category_hint: str) -> Dict[str, Any]:
    display_name = p.get("displayName")
    name = display_name.get("text") if isinstance(display_name, dict) else display_name
    loc = p.get("location") or {}
    now = datetime.now(timezone.utc)
    
    # All places are from OSM Overpass API
    place_id = p.get("id", "")
    source = "OSM_OVERPASS"
    
    return {
        "place_id": place_id,
        "source": source,
        "name": name,
        "address": p.get("formattedAddress"),
        "lat": loc.get("latitude") or loc.get("lat"),
        "lng": loc.get("longitude") or loc.get("lng"),
        "category": category_hint,
        "business_status": p.get("businessStatus"),
        "rating": p.get("rating"),
        "user_ratings_total": p.get("userRatingCount"),
        "state": "CANDIDATE",
        "confidence_score": None,
        "is_probable_not_open_yet": None,
        "first_seen_at": now,
        "last_seen_at": now,
        "last_verified_at": None,
        "next_check_at": None,
        "freshness_score": None,
        "evidence_urls": None,
        "notes": None,
        "is_retired": False,
    }

async def _exists_by_place_id(place_id: Optional[str]) -> bool:
    if not place_id:
        return False
    sql = "SELECT 1 FROM locations WHERE place_id = $1 LIMIT 1"
    rows = await fetch(sql, place_id)
    return bool(rows)

async def _exists_by_fuzzy(name: Optional[str], lat: Optional[float], lng: Optional[float]) -> Optional[int]:
    """
    Check for fuzzy duplicate by normalized name and rounded coordinates.
    Returns the existing location ID if found, None otherwise.
    """
    if not name or lat is None or lng is None:
        return None
    sql = (
        """
        SELECT id FROM locations
        WHERE LOWER(TRIM(name)) = LOWER(TRIM($1))
          AND ROUND(CAST(lat AS numeric), 4) = ROUND(CAST($2 AS numeric), 4)
          AND ROUND(CAST(lng AS numeric), 4) = ROUND(CAST($3 AS numeric), 4)
        LIMIT 1
        """
    )
    rows = await fetch(sql, name, float(lat), float(lng))
    if rows:
        return int(dict(rows[0]).get("id"))
    return None

async def insert_candidates(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Insert candidates with soft-dedupe logic:
    - Keep ON CONFLICT (place_id) DO NOTHING for strict place_id deduplication
    - Before insert, check for fuzzy match (normalized name + rounded coords)
    - If fuzzy match found, UPDATE existing row (last_seen_at, refresh category/type)
    - Track counters: discovered, inserted, deduped_place_id, deduped_fuzzy, updated_existing, failed
    
    Returns dictionary with counters.
    """
    if not rows:
        return {
            "discovered": 0,
            "inserted": 0,
            "deduped_place_id": 0,
            "deduped_fuzzy": 0,
            "updated_existing": 0,
            "failed": 0,
        }
    
    # Initialize counters
    counters = {
        "discovered": len(rows),
        "inserted": 0,
        "deduped_place_id": 0,
        "deduped_fuzzy": 0,
        "updated_existing": 0,
        "failed": 0,
    }
    
    # Ensure pool ready
    await init_db_pool()
    
    for row in rows:
        try:
            place_id = row.get("place_id")
            name = row.get("name")
            lat = row.get("lat")
            lng = row.get("lng")
            
            # Check for strict place_id duplicate (ON CONFLICT will handle, but we track it)
            if await _exists_by_place_id(place_id):
                counters["deduped_place_id"] += 1
                continue
            
            # Check for fuzzy duplicate (normalized name + rounded coords)
            existing_id = await _exists_by_fuzzy(name, lat, lng)
            if existing_id:
                # Soft-dedupe: Update existing record instead of skipping
                counters["deduped_fuzzy"] += 1
                counters["updated_existing"] += 1
                
                # Update existing row: refresh last_seen_at, category/type hints
                update_sql = (
                    """
                    UPDATE locations
                    SET
                        last_seen_at = NOW(),
                        category = COALESCE($1, category),
                        source = COALESCE($2, source),
                        address = COALESCE($3, address),
                        rating = COALESCE($4, rating),
                        user_ratings_total = COALESCE($5, user_ratings_total)
                    WHERE id = $6
                    """
                )
                await execute(
                    update_sql,
                    row.get("category") or "other",
                    row.get("source"),
                    row.get("address"),
                    row.get("rating"),
                    row.get("user_ratings_total"),
                    existing_id,
                )
                continue
            
            # No duplicate found - insert as new candidate
            sql = (
                """
                INSERT INTO locations (
                    place_id, source, name, address, lat, lng, category,
                    business_status, rating, user_ratings_total, state,
                    confidence_score, is_probable_not_open_yet,
                    first_seen_at, last_seen_at, last_verified_at,
                    next_check_at, freshness_score, evidence_urls, notes, is_retired
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7,
                    $8, $9, $10, 'CANDIDATE',
                    NULL, $11,
                    NOW(), NOW(), NULL,
                    $12, $13, $14, $15, FALSE
                )
                ON CONFLICT (place_id) DO NOTHING
                """
            )
            result = await execute(
                sql,
                row.get("place_id"),
                row.get("source"),
                row.get("name"),
                row.get("address"),
                row.get("lat"),
                row.get("lng"),
                row.get("category") or "other",
                row.get("business_status"),
                row.get("rating"),
                row.get("user_ratings_total"),
                row.get("is_probable_not_open_yet"),
                row.get("next_check_at"),
                row.get("freshness_score"),
                row.get("evidence_urls"),
                row.get("notes"),
            )
            
            # Check if insert actually happened (ON CONFLICT DO NOTHING returns no rows)
            if result and "INSERT" in result:
                counters["inserted"] += 1
            else:
                # ON CONFLICT occurred - this is a place_id duplicate
                counters["deduped_place_id"] += 1
                
        except Exception as e:
            counters["failed"] += 1
            logger.warning("insert_candidates failed for row", exc_info=e, row_id=row.get("place_id"))
    
    return counters

# ---------------------------------------------------------------------------
# Type sanitization / self-heal
# ---------------------------------------------------------------------------
# Bekende foute/legacy types voor v1 (vul aan indien je meer tegenkomt)
BAD_TYPES = {
    "grocery_or_supermarket",
}

def sanitize_types(types: List[str]) -> List[str]:
    """Filter ongeldige of lege type-namen; trim lowercase en underscores-only schema."""
    out: List[str] = []
    for t in types or []:
        if not t or not isinstance(t, str):
            continue
        t = t.strip()
        if not t or t in BAD_TYPES:
            continue
        # Simpele sanity: v1 types zijn lowercase en bevatten geen spaties
        if any(ch.isspace() for ch in t):
            continue
        out.append(t)
    # Dedupe behoud volgorde
    seen = set()
    deduped = []
    for t in out:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped

# ---------------------------------------------------------------------------
# Config + Bot
# ---------------------------------------------------------------------------
@dataclass
class DiscoveryConfig:
    city: str
    categories: List[str]
    center_lat: float
    center_lng: float
    nearby_radius_m: int
    grid_span_km: float
    max_per_cell_per_category: int
    inter_call_sleep_s: float
    max_total_inserts: int
    max_cells_per_category: int
    chunks: int
    chunk_index: int
    language: Optional[str]
    district: Optional[str] = None

class DiscoveryBot:
    def __init__(self, cfg: DiscoveryConfig, cfg_yaml: Dict[str, Any]):
        self.cfg = cfg
        self.yaml = cfg_yaml
        self.worker_run_id: Optional[UUID] = None
        self._worker_last_progress: int = -1
        
        # Initialize OSM service for enhanced discovery
        self.osm_service = OsmPlacesService(
            max_results=cfg.max_per_cell_per_category,
            turkish_hints=os.getenv("OSM_TURKISH_HINTS", "1").lower() == "true"
        )

    async def run(self) -> Dict[str, int]:
        """
        Run discovery and return aggregated counters.
        Returns dictionary with counters: discovered, inserted, deduped_place_id, deduped_fuzzy, updated_existing, failed
        """
        seen: Set[str] = set()
        total_inserted = 0

        cell_spacing_m = max(100, int(self.cfg.nearby_radius_m * 0.75))
        all_points = generate_grid_points(
            self.cfg.center_lat, self.cfg.center_lng, self.cfg.grid_span_km, cell_spacing_m
        )
        points = pick_chunk(all_points, self.cfg.chunks, self.cfg.chunk_index)

        print(f"[DiscoveryBot] Grid totaal={len(all_points)}, chunk={self.cfg.chunk_index}/{max(0,self.cfg.chunks-1)} → subset={len(points)}")
        print(f"[DiscoveryBot] Categorieën (interne keys): {', '.join(self.cfg.categories)}")
        if self.cfg.district:
            print(f"[DiscoveryBot] District: {self.cfg.district}")

        # Use OSM discovery (free, open-source)
        print(f"[DiscoveryBot] Using OSM discovery with subdivision")
        return await self._run_osm_discovery(points, seen, total_inserted)

    async def _run_osm_discovery(self, points: List[Tuple[float, float]], seen: Set[str], total_inserted: int) -> Dict[str, int]:
        """
        Run OSM-based discovery with adaptive subdivision.
        Includes circuit breaker to abort Overpass calls if error rate is too high.
        Returns aggregated counters dictionary.
        """
        # Circuit breaker configuration (protects Overpass from overload)
        # These thresholds detect "error storms" where Overpass is clearly struggling
        DISCOVERY_MAX_CONSECUTIVE_OVERPASS_FAILURES = int(os.getenv("DISCOVERY_MAX_CONSECUTIVE_OVERPASS_FAILURES", "10"))
        DISCOVERY_MAX_OVERPASS_ERROR_RATIO = float(os.getenv("DISCOVERY_MAX_OVERPASS_ERROR_RATIO", "0.8"))
        
        start_time = time.time()
        safety_timeout_s = 25 * 60  # 25 minutes safety timeout
        
        # Circuit breaker state tracking
        overpass_calls_total = 0
        overpass_calls_failed = 0
        consecutive_failures = 0
        circuit_breaker_triggered = False
        
        # Initialize aggregated counters
        aggregated_counters = {
            "discovered": 0,
            "inserted": 0,
            "deduped_place_id": 0,
            "deduped_fuzzy": 0,
            "updated_existing": 0,
            "failed": 0,
        }
        categories_map = self.yaml.get("categories") or {}
        valid_categories = [
            cat
            for cat in self.cfg.categories
            if (categories_map.get(cat) or {}).get("osm_tags")
        ]
        total_units = len(points) * len(valid_categories)
        if total_units == 0 and points:
            total_units = len(points)
        completed_units = 0

        for cat_key in self.cfg.categories:
            cat_def = categories_map.get(cat_key)
            if not cat_def:
                print(f"[DiscoveryBot] WAARSCHUWING: categorie '{cat_key}' niet gevonden in categories.yml; overslaan.")
                logger.warning("discovery_category_not_found", category=cat_key, available=list(categories_map.keys()))
                continue

            # Check if discovery is enabled for this category
            discovery_cfg = cat_def.get("discovery", {})
            if not discovery_cfg.get("enabled", True):
                print(f"[DiscoveryBot] INFO: categorie '{cat_key}' heeft discovery.enabled=false; overslaan.")
                logger.info("discovery_category_disabled", category=cat_key)
                continue

            # Get OSM tags for this category
            osm_tags_raw = cat_def.get("osm_tags")
            if not osm_tags_raw:
                print(f"[DiscoveryBot] WAARSCHUWING: categorie '{cat_key}' heeft geen osm_tags; overslaan.")
                logger.warning("discovery_category_no_osm_tags", category=cat_key)
                continue

            # Convert YAML structure to expected format: List[List[Dict[str, Any]]]
            # YAML: {"any": [{"amenity": "restaurant"}]}
            # Expected: [[{"any": [{"amenity": "restaurant"}]}]]
            osm_tags = [osm_tags_raw]

            print(f"\n[DiscoveryBot] === {cat_key} ===  (osm_tags={osm_tags})")
            processed_cells = 0

            for i, (lat, lng) in enumerate(points, start=1):
                # Check circuit breaker - stop making Overpass calls if error storm detected
                if circuit_breaker_triggered:
                    print(f"[DiscoveryBot] Circuit breaker active: skipping remaining Overpass calls. Processing already-found results.")
                    # Break from inner loop but continue outer loop to process remaining categories if needed
                    # Actually, we should break from both loops since we're done with Overpass
                    break
                
                # Check safety timeout
                elapsed_time = time.time() - start_time
                if elapsed_time > safety_timeout_s:
                    print(f"[DiscoveryBot] Safety timeout bereikt ({elapsed_time:.1f}s). Stoppen om GitHub Actions timeout te voorkomen.")
                    return aggregated_counters
                
                if self.cfg.max_cells_per_category > 0 and processed_cells >= self.cfg.max_cells_per_category:
                    print(f"[DiscoveryBot] Max cellen voor {cat_key} bereikt: {processed_cells}")
                    break

                # Track Overpass call attempt
                overpass_calls_total += 1
                overpass_call_failed = False
                
                try:
                    # Use OSM service with subdivision
                    places = await self.osm_service.search_nearby_with_subdivision(
                        lat=lat,
                        lng=lng,
                        radius=self.cfg.nearby_radius_m,
                        included_types=[cat_key],
                        max_results=self.cfg.max_per_cell_per_category,
                        language=self.cfg.language,
                        category_osm_tags=[osm_tags]
                    )
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc(limit=5)
                    print(f"[DiscoveryBot] {cat_key} @({lat:.5f},{lng:.5f}) OSM error: {type(e).__name__}: {e}")
                    print(f"[DiscoveryBot] Traceback: {tb}")
                    places = []
                    overpass_call_failed = True
                
                # Track failures for circuit breaker
                if overpass_call_failed:
                    overpass_calls_failed += 1
                    consecutive_failures += 1
                else:
                    consecutive_failures = 0  # Reset on success
                
                # Check circuit breaker thresholds
                if overpass_calls_total > 0:
                    error_ratio = overpass_calls_failed / overpass_calls_total
                    
                    if consecutive_failures >= DISCOVERY_MAX_CONSECUTIVE_OVERPASS_FAILURES:
                        circuit_breaker_triggered = True
                        logger.warning(
                            "discovery_circuit_breaker_triggered",
                            reason="consecutive_failures",
                            consecutive_failures=consecutive_failures,
                            threshold=DISCOVERY_MAX_CONSECUTIVE_OVERPASS_FAILURES,
                            total_calls=overpass_calls_total,
                            failed_calls=overpass_calls_failed
                        )
                        print(f"[DiscoveryBot] CIRCUIT BREAKER TRIGGERED: {consecutive_failures} consecutive Overpass failures (threshold: {DISCOVERY_MAX_CONSECUTIVE_OVERPASS_FAILURES})")
                        print(f"[DiscoveryBot] Stopping Overpass calls to avoid overloading public servers. Processing already-found results.")
                    elif error_ratio >= DISCOVERY_MAX_OVERPASS_ERROR_RATIO:
                        circuit_breaker_triggered = True
                        logger.warning(
                            "discovery_circuit_breaker_triggered",
                            reason="error_ratio",
                            error_ratio=error_ratio,
                            threshold=DISCOVERY_MAX_OVERPASS_ERROR_RATIO,
                            total_calls=overpass_calls_total,
                            failed_calls=overpass_calls_failed
                        )
                        print(f"[DiscoveryBot] CIRCUIT BREAKER TRIGGERED: Overpass error ratio {error_ratio:.1%} exceeds threshold {DISCOVERY_MAX_OVERPASS_ERROR_RATIO:.1%}")
                        print(f"[DiscoveryBot] Stopping Overpass calls to avoid overloading public servers. Processing already-found results.")

                batch: List[Dict[str, Any]] = []
                for p in places or []:
                    pid = p.get("id")
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)
                    batch.append(map_place_to_row(p, cat_key))

                if batch:
                    try:
                        counters = await insert_candidates(batch)
                        # Aggregate counters
                        for key in aggregated_counters:
                            aggregated_counters[key] += counters.get(key, 0)
                        total_inserted += counters.get("inserted", 0)
                        if counters.get("inserted", 0) > 0:
                            print(f"[DiscoveryBot] OSM Insert: batch={len(batch)} inserted={counters.get('inserted', 0)} total={total_inserted}")
                    except Exception as e:
                        print(f"[DiscoveryBot] OSM Insert fout (batch={len(batch)}): {e}")
                        aggregated_counters["failed"] += len(batch)

                processed_cells += 1

                # Progress reporting every 10 cells (more frequent)
                if i % 10 == 0:
                    elapsed_time = time.time() - start_time
                    print(f"[DiscoveryBot] {cat_key}: {i}/{len(points)} cellen, totaal ingevoegd={total_inserted}, elapsed={elapsed_time:.1f}s")

                if total_units > 0:
                    completed_units += 1
                    await self._report_progress(completed_units, total_units)

                if self.cfg.max_total_inserts > 0 and total_inserted >= self.cfg.max_total_inserts:
                    print(f"[DiscoveryBot] Max totaal inserts bereikt: {total_inserted}. Stoppen.")
                    return aggregated_counters

                if self.cfg.inter_call_sleep_s:
                    await asyncio.sleep(self.cfg.inter_call_sleep_s)
            
            # If circuit breaker triggered, break from outer category loop too
            if circuit_breaker_triggered:
                break

        # Mark run as degraded if circuit breaker was triggered
        if circuit_breaker_triggered:
            aggregated_counters["degraded"] = True
            aggregated_counters["overpass_failures"] = overpass_calls_failed
            aggregated_counters["overpass_total_calls"] = overpass_calls_total
            error_ratio = overpass_calls_failed / max(overpass_calls_total, 1)
            print(f"[DiscoveryBot] Run completed in DEGRADED mode: {overpass_calls_failed}/{overpass_calls_total} Overpass calls failed ({error_ratio:.1%})")
        
        return aggregated_counters

    async def _report_progress(self, completed: int, total: int) -> None:
        if not self.worker_run_id or total <= 0:
            return
        percent = min(99, max(0, int((completed * 100) / total)))
        if percent != self._worker_last_progress:
            await update_worker_run_progress(self.worker_run_id, percent)
            self._worker_last_progress = percent


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
@dataclass
class _Arg:
    name: str
    help: str
    type: Any = None
    default: Any = None


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="DiscoveryBot — grid-based met YAML mapping + chunking + district")
    ap.add_argument("--city", help="Stad key in cities.yml (default: rotterdam)", default="rotterdam")
    ap.add_argument("--district", help="District key in cities.yml (bv. centrum)")
    ap.add_argument("--categories", help="Komma-gescheiden interne categorieën (anders: alle uit categories.yml)")
    ap.add_argument("--center-lat", type=float, help="Override center latitude")
    ap.add_argument("--center-lng", type=float, help="Override center longitude")
    ap.add_argument("--nearby-radius-m", type=int, help="OSM search radius (meter)")
    ap.add_argument("--grid-span-km", type=float, help="Grid-span (km, zijde)")
    ap.add_argument("--max-per-cell-per-category", type=int, help="Cap resultaten per cel per categorie")
    ap.add_argument("--inter-call-sleep-s", type=float, help="Sleep tussen calls")
    ap.add_argument("--max-total-inserts", type=int, default=0, help="Stop na N inserts (0=geen limiet)")
    ap.add_argument("--max-cells-per-category", type=int, default=0, help="Stop na N cellen per categorie (0=geen limiet)")
    ap.add_argument("--chunks", type=int, default=1, help="Verdeel grid in N chunks")
    ap.add_argument("--chunk-index", type=int, default=0, help="Welke chunk index (0-based)")
    ap.add_argument("--language", help="API-taal, bv. nl")
    ap.add_argument("--worker-run-id", type=_parse_worker_run_id, help="UUID van worker_runs record voor progress rapportage")
    return ap.parse_args()

def build_config(ns: argparse.Namespace, yml: Dict[str, Any]) -> DiscoveryConfig:
    defaults = yml.get("defaults") or {}
    disc_def = defaults.get("discovery") or {}
    yaml_lang = defaults.get("language")

    city = ns.city or "rotterdam"
    # Default center coordinates (Rotterdam fallback for backward compatibility)
    default_center_lat = 51.9244
    default_center_lng = 4.4777
    
    # If CLI overrides provided, use those; otherwise try to lookup from cities.yml
    if ns.center_lat is not None and ns.center_lng is not None:
        # Both CLI overrides provided, use them directly
        center_lat = ns.center_lat
        center_lng = ns.center_lng
    else:
        # Try to lookup city center from cities.yml
        try:
            cities = load_cities_config()
            city_def = (cities.get("cities") or {}).get(city)
            if city_def:
                # Check if city has center_lat/center_lng defined
                if "center_lat" in city_def and "center_lng" in city_def:
                    center_lat = float(city_def["center_lat"])
                    center_lng = float(city_def["center_lng"])
                else:
                    # Fall back to defaults if city found but no center defined
                    center_lat = default_center_lat
                    center_lng = default_center_lng
            else:
                # City not found in config, use defaults
                center_lat = default_center_lat
                center_lng = default_center_lng
        except Exception as e:
            # If cities.yml load fails, use defaults (backward compatibility)
            logger.warning("failed_to_load_cities_config_for_center", city=city, exc_info=e)
            center_lat = default_center_lat
            center_lng = default_center_lng
        
        # CLI overrides take precedence if provided (partial overrides allowed)
        if ns.center_lat is not None:
            center_lat = ns.center_lat
        if ns.center_lng is not None:
            center_lng = ns.center_lng

    district = ns.district.strip() if ns.district else None
    if district:
        cities = load_cities_config()
        city_def = (cities.get("cities") or {}).get(city)
        if not city_def or "districts" not in city_def:
            raise ValueError(f"cities.yml: stad '{city}' of districts ontbreken.")
        d = (city_def["districts"] or {}).get(district)
        if not d:
            raise ValueError(f"cities.yml: district '{district}' niet gevonden voor stad '{city}'.")
        lat_min, lat_max = float(d["lat_min"]), float(d["lat_max"])
        lng_min, lng_max = float(d["lng_min"]), float(d["lng_max"])
        center_lat = (lat_min + lat_max) / 2.0
        center_lng = (lng_min + lng_max) / 2.0
        # span = max(latspan, lngspan) in km
        lat_span_km = deg_lat_to_m(abs(lat_max - lat_min)) / 1000.0
        lng_span_km = deg_lng_to_m(abs(lng_max - lng_min), center_lat) / 1000.0
        auto_span_km = max(lat_span_km, lng_span_km)
    else:
        auto_span_km = 12.0  # fallback zoals eerder

    if ns.categories:
        cats = [c.strip() for c in ns.categories.split(",") if c.strip()]
    else:
        cats = list((yml.get("categories") or {}).keys())

    cfg = {
        "city": city,
        "categories": cats,
        "center_lat": center_lat,
        "center_lng": center_lng,
        "nearby_radius_m": ns.nearby_radius_m if ns.nearby_radius_m is not None else int(disc_def.get("nearby_radius_m", 1000)),
        "grid_span_km": ns.grid_span_km if ns.grid_span_km is not None else float(disc_def.get("grid_span_km", auto_span_km)),
        "max_per_cell_per_category": ns.max_per_cell_per_category if ns.max_per_cell_per_category is not None else int(disc_def.get("max_per_cell_per_category", 20)),
        "inter_call_sleep_s": ns.inter_call_sleep_s if ns.inter_call_sleep_s is not None else 0.15,
        "max_total_inserts": ns.max_total_inserts or 0,
        "max_cells_per_category": ns.max_cells_per_category or 0,
        "chunks": ns.chunks or 1,
        "chunk_index": ns.chunk_index or 0,
        "language": ns.language or yaml_lang or None,
        "district": district,
    }
    return DiscoveryConfig(**cfg)

async def main_async():
    t0 = time.perf_counter()
    discovery_run_id = None
    
    with with_run_id() as rid:
        logger.info("worker_started")
        ns = parse_args()
        worker_run_id: Optional[UUID] = getattr(ns, "worker_run_id", None)
        yml = load_categories_config()
        cfg = build_config(ns, yml)

        print("\n[DiscoveryBot] Configuratie:")
        print(f"  Stad: {cfg.city}")
        if cfg.district:
            print(f"  District: {cfg.district}")
        print(f"  Center: ({cfg.center_lat:.4f}, {cfg.center_lng:.4f})")
        print(f"  Categorieën: {cfg.categories}")
        print(f"  Grid span: {cfg.grid_span_km:.2f} km")
        print(f"  Nearby radius: {cfg.nearby_radius_m} m")
        print(f"  Max per cel: {cfg.max_per_cell_per_category}")
        print(f"  Sleep tijd: {cfg.inter_call_sleep_s} s")
        if cfg.language:
            print(f"  Language: {cfg.language}")
        if cfg.max_total_inserts > 0:
            print(f"  Max totaal inserts: {cfg.max_total_inserts}")
        if cfg.max_cells_per_category > 0:
            print(f"  Max cellen/categorie: {cfg.max_cells_per_category}")
        print(f"  Chunks: {cfg.chunks} (index={cfg.chunk_index})\n")

        # Ensure DB pool ready before inserts
        await init_db_pool()
        
        # Auto-create worker_run if not provided
        if not worker_run_id:
            # Use first category if multiple, or None
            category = cfg.categories[0] if cfg.categories else None
            worker_run_id = await start_worker_run(bot="discovery_bot", city=cfg.city, category=category)
        
        if worker_run_id:
            await mark_worker_run_running(worker_run_id)
        
        # Create discovery_run record at start
        try:
            sql_insert = """
                INSERT INTO discovery_runs (started_at, notes)
                VALUES (NOW(), $1)
                RETURNING id
            """
            notes = f"Discovery run: city={cfg.city}, categories={','.join(cfg.categories)}, chunk={cfg.chunk_index}/{cfg.chunks-1}"
            rows = await fetch(sql_insert, notes)
            if rows:
                discovery_run_id = dict(rows[0]).get("id")
                logger.info("discovery_run_created", run_id=str(discovery_run_id))
        except Exception as e:
            logger.warning("failed_to_create_discovery_run", exc_info=e)
        
        # Run discovery bot and collect counters
        bot = DiscoveryBot(cfg, yml)
        bot.worker_run_id = worker_run_id
        counters: Dict[str, int] = {}
        try:
            counters = await bot.run()
        except Exception as e:
            if worker_run_id:
                progress_snapshot = bot._worker_last_progress if bot._worker_last_progress >= 0 else 0
                await finish_worker_run(
                    worker_run_id,
                    "failed",
                    progress_snapshot,
                    None,
                    str(e),
                )
            raise
        
        # Update discovery_run with finished_at and counters
        if discovery_run_id:
            try:
                # Build notes string (include degraded info if applicable)
                notes_parts = [f"Discovery run: city={cfg.city}, categories={','.join(cfg.categories)}, chunk={cfg.chunk_index}/{cfg.chunks-1}"]
                if counters.get("degraded"):
                    error_ratio = counters.get("overpass_failures", 0) / max(counters.get("overpass_total_calls", 1), 1)
                    notes_parts.append(f"degraded: overpass error storm ({counters.get('overpass_failures', 0)} failures out of {counters.get('overpass_total_calls', 0)} calls)")
                
                sql_update = """
                    UPDATE discovery_runs
                    SET finished_at = NOW(), counters = $1::jsonb, notes = $3
                    WHERE id = $2
                """
                counters_json = json.dumps(counters, ensure_ascii=False)
                notes_str = " | ".join(notes_parts)
                await execute(sql_update, counters_json, discovery_run_id, notes_str)
                logger.info("discovery_run_completed", run_id=str(discovery_run_id), counters=counters)
                print(f"\n[DiscoveryBot] Counters: {counters}")
            except Exception as e:
                logger.warning("failed_to_update_discovery_run", exc_info=e, run_id=str(discovery_run_id))
        if worker_run_id:
            await finish_worker_run(worker_run_id, "finished", 100, counters, None)
        else:
            # Log counters even if discovery_run wasn't created
            logger.info("discovery_counters", counters=counters)
            print(f"\n[DiscoveryBot] Counters: {counters}")

        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("worker_finished", duration_ms=duration_ms)

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[DiscoveryBot] Afgebroken door gebruiker.")
    except Exception as e:
        print(f"\n[DiscoveryBot] FOUT: {e}")
        raise

if __name__ == "__main__":
    main()
