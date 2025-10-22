# -*- coding: utf-8 -*-
"""
DiscoveryBot — Grid-based discovery met YAML category-mapping + district support
- Leest Infra/config/categories.yml als bron voor diaspora->Google place_types
- Leest Infra/config/cities.yml voor district-bounding boxes
- CLI flags: chunking, caps per categorie, district-selectie
- Inclusief sanitization + self-heal voor ongeldige Google types

Pad: Backend/app/workers/discovery_bot.py
"""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Dict, Any, Set, Tuple, Optional

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
# DB (async)
# ---------------------------------------------------------------------------
def _resolve_database_url() -> str:
    for key in ("DATABASE_URL", "DB_URL"):
        v = os.getenv(key)
        if v:
            return v
    try:
        from app.config import settings  # type: ignore
        for attr in ("DATABASE_URL", "database_url", "DB_URL"):
            if hasattr(settings, attr):
                val = getattr(settings, attr)
                if isinstance(val, str) and val:
                    return val
    except Exception:
        pass
    try:
        from app.config import Config  # type: ignore
        for attr in ("DATABASE_URL", "database_url", "DB_URL"):
            if hasattr(Config, attr):
                val = getattr(Config, attr)
                if isinstance(val, str) and val:
                    return val
    except Exception:
        pass
    raise RuntimeError("DATABASE_URL ontbreekt (env of config).")

DATABASE_URL = _resolve_database_url()
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, future=True)
Session = async_sessionmaker(engine, expire_on_commit=False)

# ---------------------------------------------------------------------------
# Places provider (Google or OSM)
# ---------------------------------------------------------------------------
from app.services.provider_factory import get_places_provider
from services.osm_service import OsmPlacesService

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
def map_google_place_to_row(p: Dict[str, Any], category_hint: str) -> Dict[str, Any]:
    display_name = p.get("displayName")
    name = display_name.get("text") if isinstance(display_name, dict) else display_name
    loc = p.get("location") or {}
    now = datetime.now(timezone.utc)
    
    # Determine source based on place_id format
    place_id = p.get("id", "")
    if "/" in str(place_id):  # OSM format: node/123, way/456, relation/789
        source = "OSM_OVERPASS"
    else:
        source = "GOOGLE_PLACES"
    
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

INSERT_SQL = text("""
INSERT INTO locations (
    place_id, source, name, address, lat, lng, category,
    business_status, rating, user_ratings_total, state,
    confidence_score, is_probable_not_open_yet,
    first_seen_at, last_seen_at, last_verified_at,
    next_check_at, freshness_score, evidence_urls, notes, is_retired
) VALUES (
    :place_id, :source, :name, :address, :lat, :lng, :category,
    :business_status, :rating, :user_ratings_total, :state,
    :confidence_score, :is_probable_not_open_yet,
    :first_seen_at, :last_seen_at, :last_verified_at,
    :next_check_at, :freshness_score, :evidence_urls, :notes, :is_retired
)
ON CONFLICT (place_id) DO NOTHING
RETURNING id;
""")

async def insert_candidates(rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    inserted = 0
    async with Session() as session:
        async with session.begin():
            for row in rows:
                res = await session.execute(INSERT_SQL, row)
                if res.scalar_one_or_none() is not None:
                    inserted += 1
    return inserted

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
        self.provider = get_places_provider()
        
        # Initialize OSM service for enhanced discovery
        self.osm_service = OsmPlacesService(
            max_results=cfg.max_per_cell_per_category,
            turkish_hints=os.getenv("OSM_TURKISH_HINTS", "1").lower() == "true"
        )

    async def run(self) -> int:
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

        # Check if we should use OSM discovery (default to OSM when unset)
        use_osm = os.getenv("DATA_PROVIDER", "osm").lower() == "osm"
        
        if use_osm:
            print(f"[DiscoveryBot] Using OSM discovery with subdivision")
            return await self._run_osm_discovery(points, seen, total_inserted)
        else:
            print(f"[DiscoveryBot] Using Google Places discovery")
            return await self._run_google_discovery(points, seen, total_inserted)

    async def _run_osm_discovery(self, points: List[Tuple[float, float]], seen: Set[str], total_inserted: int) -> int:
        """Run OSM-based discovery with adaptive subdivision."""
        for cat_key in self.cfg.categories:
            cat_def = (self.yaml.get("categories") or {}).get(cat_key)
            if not cat_def:
                print(f"[DiscoveryBot] WAARSCHUWING: categorie '{cat_key}' niet gevonden in YAML; overslaan.")
                continue

            # Get OSM tags for this category
            osm_tags_raw = cat_def.get("osm_tags")
            if not osm_tags_raw:
                print(f"[DiscoveryBot] WAARSCHUWING: categorie '{cat_key}' heeft geen osm_tags; overslaan.")
                continue

            # Convert YAML structure to expected format: List[List[Dict[str, Any]]]
            # YAML: {"any": [{"amenity": "restaurant"}]}
            # Expected: [[{"any": [{"amenity": "restaurant"}]}]]
            osm_tags = [osm_tags_raw]

            print(f"\n[DiscoveryBot] === {cat_key} ===  (osm_tags={osm_tags})")
            processed_cells = 0

            for i, (lat, lng) in enumerate(points, start=1):
                if self.cfg.max_cells_per_category > 0 and processed_cells >= self.cfg.max_cells_per_category:
                    print(f"[DiscoveryBot] Max cellen voor {cat_key} bereikt: {processed_cells}")
                    break

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

                batch: List[Dict[str, Any]] = []
                for p in places or []:
                    pid = p.get("id")
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)
                    batch.append(map_google_place_to_row(p, cat_key))

                if batch:
                    try:
                        ins = await insert_candidates(batch)
                        total_inserted += ins
                        if ins > 0:
                            print(f"[DiscoveryBot] OSM Insert: batch={len(batch)} inserted={ins} total={total_inserted}")
                    except Exception as e:
                        print(f"[DiscoveryBot] OSM Insert fout (batch={len(batch)}): {e}")

                processed_cells += 1

                if i % 50 == 0:
                    print(f"[DiscoveryBot] {cat_key}: {i}/{len(points)} cellen, totaal ingevoegd={total_inserted}")

                if self.cfg.max_total_inserts > 0 and total_inserted >= self.cfg.max_total_inserts:
                    print(f"[DiscoveryBot] Max totaal inserts bereikt: {total_inserted}. Stoppen.")
                    return total_inserted

                if self.cfg.inter_call_sleep_s:
                    await asyncio.sleep(self.cfg.inter_call_sleep_s)

        return total_inserted

    async def _run_google_discovery(self, points: List[Tuple[float, float]], seen: Set[str], total_inserted: int) -> int:
        """Run Google Places-based discovery (original logic)."""
        for cat_key in self.cfg.categories:
            cat_def = (self.yaml.get("categories") or {}).get(cat_key)
            if not cat_def:
                print(f"[DiscoveryBot] WAARSCHUWING: categorie '{cat_key}' niet gevonden in YAML; overslaan.")
                continue

            google_types = sanitize_types(cat_def.get("google_types") or [])
            if not google_types:
                print(f"[DiscoveryBot] WAARSCHUWING: categorie '{cat_key}' heeft geen geldige google_types; overslaan.")
                continue

            print(f"\n[DiscoveryBot] === {cat_key} ===  (google_types={google_types})")
            processed_cells = 0

            for i, (lat, lng) in enumerate(points, start=1):
                if self.cfg.max_cells_per_category > 0 and processed_cells >= self.cfg.max_cells_per_category:
                    print(f"[DiscoveryBot] Max cellen voor {cat_key} bereikt: {processed_cells}")
                    break

                try:
                    places = await self.provider.search_nearby(
                        lat=lat,
                        lng=lng,
                        radius=self.cfg.nearby_radius_m,
                        included_types=google_types,
                        max_results=max(1, int(self.cfg.max_per_cell_per_category)),
                        language=self.cfg.language,
                    )
                except Exception as e:
                    msg = str(e)
                    error_class = type(e).__name__
                    # Self-heal bij "Unsupported types: X"
                    if "Unsupported types:" in msg:
                        bad = msg.split("Unsupported types:")[-1].strip().strip(".").strip()
                        if bad in google_types:
                            print(f"[DiscoveryBot] Unsupported type gedetecteerd: {bad} → opnieuw zonder dit type")
                            google_types = [t for t in google_types if t != bad]
                            if not google_types:
                                print(f"[DiscoveryBot] Geen valide google_types meer voor {cat_key}; sla cel over.")
                                processed_cells += 1
                                continue
                            try:
                                places = await self.provider.search_nearby(
                                    lat=lat, lng=lng, radius=self.cfg.nearby_radius_m,
                                    included_types=google_types,
                                    max_results=max(1, int(self.cfg.max_per_cell_per_category)),
                                    language=self.cfg.language,
                                )
                            except Exception as e2:
                                print(f"[DiscoveryBot] {cat_key} @({lat:.5f},{lng:.5f}) retry: {type(e2).__name__}")
                                places = []
                        else:
                            print(f"[DiscoveryBot] {cat_key} @({lat:.5f},{lng:.5f}) {error_class}: {e}")
                            places = []
                    else:
                        print(f"[DiscoveryBot] {cat_key} @({lat:.5f},{lng:.5f}) {error_class}: {e}")
                        places = []

                batch: List[Dict[str, Any]] = []
                for p in places or []:
                    pid = p.get("id")
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)
                    batch.append(map_google_place_to_row(p, cat_key))

                if batch:
                    try:
                        ins = await insert_candidates(batch)
                        total_inserted += ins
                        if ins > 0:
                            print(f"[DiscoveryBot] Insert: batch={len(batch)} inserted={ins} total={total_inserted}")
                    except Exception as e:
                        print(f"[DiscoveryBot] Insert fout (batch={len(batch)}): {e}")

                processed_cells += 1

                if i % 50 == 0:
                    print(f"[DiscoveryBot] {cat_key}: {i}/{len(points)} cellen, totaal ingevoegd={total_inserted}")

                if self.cfg.max_total_inserts > 0 and total_inserted >= self.cfg.max_total_inserts:
                    print(f"[DiscoveryBot] Max totaal inserts bereikt: {total_inserted}. Stoppen.")
                    return total_inserted

                if self.cfg.inter_call_sleep_s:
                    await asyncio.sleep(self.cfg.inter_call_sleep_s)

        print(f"\n[DiscoveryBot] ✓ Klaar. Totaal nieuw (idempotent) ingevoegd: {total_inserted}")
        return total_inserted

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
@dataclass
class _Arg:
    name: str
    help: str
    type: Any = None
    default: Any = None

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="DiscoveryBot — grid-based met YAML mapping + chunking + district")
    ap.add_argument("--city", help="Stad key in cities.yml (default: rotterdam)", default="rotterdam")
    ap.add_argument("--district", help="District key in cities.yml (bv. centrum)")
    ap.add_argument("--categories", help="Komma-gescheiden interne categorieën (anders: alle uit categories.yml)")
    ap.add_argument("--center-lat", type=float, help="Override center latitude")
    ap.add_argument("--center-lng", type=float, help="Override center longitude")
    ap.add_argument("--nearby-radius-m", type=int, help="Google Nearby radius (meter)")
    ap.add_argument("--grid-span-km", type=float, help="Grid-span (km, zijde)")
    ap.add_argument("--max-per-cell-per-category", type=int, help="Cap resultaten per cel per categorie")
    ap.add_argument("--inter-call-sleep-s", type=float, help="Sleep tussen calls")
    ap.add_argument("--max-total-inserts", type=int, default=0, help="Stop na N inserts (0=geen limiet)")
    ap.add_argument("--max-cells-per-category", type=int, default=0, help="Stop na N cellen per categorie (0=geen limiet)")
    ap.add_argument("--chunks", type=int, default=1, help="Verdeel grid in N chunks")
    ap.add_argument("--chunk-index", type=int, default=0, help="Welke chunk index (0-based)")
    ap.add_argument("--language", help="API-taal, bv. nl")
    return ap.parse_args()

def build_config(ns: argparse.Namespace, yml: Dict[str, Any]) -> DiscoveryConfig:
    defaults = yml.get("defaults") or {}
    disc_def = defaults.get("discovery") or {}
    yaml_lang = defaults.get("language")

    city = ns.city or "rotterdam"
    center_lat = ns.center_lat if ns.center_lat is not None else 51.9244
    center_lng = ns.center_lng if ns.center_lng is not None else 4.4777

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
    with with_run_id() as rid:
        logger.info("worker_started")
        ns = parse_args()
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

        bot = DiscoveryBot(cfg, yml)
        await bot.run()

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
