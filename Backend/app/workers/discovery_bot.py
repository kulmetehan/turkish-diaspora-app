# -*- coding: utf-8 -*-
"""
DiscoveryBot - Grid-Based Search Scheduler (standalone script)

Pad: Backend/workers/discovery_bot.py

Gebruik:
    cd "/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/Backend"
    source .venv/bin/activate
    
    # Met CLI argumenten:
    python workers/discovery_bot.py \
      --city rotterdam \
      --categories bakery,restaurant,supermarket \
      --nearby-radius-m 1000 \
      --grid-span-km 12 \
      --max-per-cell-per-category 20 \
      --inter-call-sleep-s 0.15 \
      --max-total-inserts 1200 \
      --max-cells-per-category 50
    
    # Met YAML config profiel:
    python workers/discovery_bot.py \
      --profile rotterdam \
      --config config/discovery.yml
"""
from __future__ import annotations

import argparse
import asyncio
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Dict, Any, Set, Tuple, Optional

# ---------------------------------------------------------------------------
# 1) sys.path zo instellen dat we app/* kunnen importeren
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
BACKEND_ROOT = THIS_FILE.parent.parent  # .../Backend
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# ---------------------------------------------------------------------------
# 2) DB-URL ophalen (env of app.config)
# ---------------------------------------------------------------------------
def _resolve_database_url() -> str:
    """
    Probeert in deze volgorde:
    1) ENV: DATABASE_URL of DB_URL
    2) app.config: settings.DATABASE_URL of settings.database_url of Config.DATABASE_URL
    """
    # 1) Env vars
    for key in ("DATABASE_URL", "DB_URL"):
        v = os.getenv(key)
        if v:
            return v

    # 2) Probeer app.config varianten
    try:
        # Variant: from app.config import settings
        from app.config import settings  # type: ignore
        for attr in ("DATABASE_URL", "database_url", "DB_URL"):
            if hasattr(settings, attr):
                val = getattr(settings, attr)
                if isinstance(val, str) and val:
                    return val
    except Exception:
        pass

    try:
        # Variant: from app.config import Config
        from app.config import Config  # type: ignore
        for attr in ("DATABASE_URL", "database_url", "DB_URL"):
            if hasattr(Config, attr):
                val = getattr(Config, attr)
                if isinstance(val, str) and val:
                    return val
    except Exception:
        pass

    raise RuntimeError(
        "Kon geen DATABASE_URL vinden. Zet env var DATABASE_URL of definieer deze in app.config (settings/Config)."
    )

DATABASE_URL = _resolve_database_url()

# ---------------------------------------------------------------------------
# 3) SQLAlchemy async engine + sessionmaker
# ---------------------------------------------------------------------------
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

# Zorg dat we een async driver gebruiken (postgresql+asyncpg bijvoorbeeld)
# Als je URL nog 'postgresql://' is, vervang die veilig naar 'postgresql+asyncpg://'
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

async_engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True
)
Session = async_sessionmaker(async_engine, expire_on_commit=False)

# ---------------------------------------------------------------------------
# 4) Google service importeren (met stabiele fallback)
# ---------------------------------------------------------------------------
USING_STUB = False
try:
    # voorkeurslocatie
    from app.services.google_service import GooglePlacesService  # type: ignore
except Exception:
    try:
        # jouw huidige locatie
        from services.google_service import GooglePlacesService  # type: ignore
    except Exception as _e:
        USING_STUB = True
        print("[DiscoveryBot] WAARSCHUWING: GooglePlacesService niet gevonden/geladen. Fallback stub actief (0 resultaten).", _e)
        class GooglePlacesService:
            async def search_nearby(self, lat, lng, radius, included_types, max_results=20, language=None):
                return []

# ---------------------------------------------------------------------------
# 5) YAML config loader (optioneel)
# ---------------------------------------------------------------------------
def load_yaml_config(config_path: str, profile: str) -> Optional[Dict[str, Any]]:
    """Laadt configuratie uit YAML bestand voor opgegeven profiel."""
    try:
        import yaml
    except ImportError:
        print("[DiscoveryBot] WAARSCHUWING: PyYAML niet geïnstalleerd. Gebruik CLI argumenten.")
        return None
    
    path = Path(config_path)
    if not path.exists():
        print(f"[DiscoveryBot] Config bestand niet gevonden: {config_path}")
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        profiles = config.get('profiles', {})
        if profile not in profiles:
            print(f"[DiscoveryBot] Profiel '{profile}' niet gevonden in config. Beschikbare profielen: {list(profiles.keys())}")
            return None
        
        return profiles[profile]
    except Exception as e:
        print(f"[DiscoveryBot] Fout bij laden YAML config: {e}")
        return None

# ---------------------------------------------------------------------------
# 6) Geo helpers + mapping
# ---------------------------------------------------------------------------
ROTTERDAM_CENTER = (51.9244, 4.4777)
EARTH_RADIUS_M = 6371000.0

def meters_to_lat_deg(m: float) -> float:
    return (m / EARTH_RADIUS_M) * (180.0 / math.pi)

def meters_to_lng_deg(m: float, at_lat_deg: float) -> float:
    return (m / (EARTH_RADIUS_M * math.cos(math.radians(at_lat_deg)))) * (180.0 / math.pi)

def generate_grid_points(
    center_lat: float,
    center_lng: float,
    grid_span_km: float,
    cell_spacing_m: int
) -> Iterable[Tuple[float, float]]:
    half_span_m = grid_span_km * 1000
    lat_step = meters_to_lat_deg(cell_spacing_m)
    lng_step = meters_to_lng_deg(cell_spacing_m, center_lat)

    lat_min = center_lat - meters_to_lat_deg(half_span_m)
    lat_max = center_lat + meters_to_lat_deg(half_span_m)
    lng_min = center_lng - meters_to_lng_deg(half_span_m, center_lat)
    lng_max = center_lng + meters_to_lng_deg(half_span_m, center_lat)

    lat = lat_min
    while lat <= lat_max:
        lng = lng_min
        while lng <= lng_max:
            yield (lat, lng)
            lng += lng_step
        lat += lat_step

def map_google_place_to_location_row(p: Dict[str, Any], category_hint: str) -> Dict[str, Any]:
    # Google Places v1 velden
    place_id = p.get("id")
    display_name = p.get("displayName")
    if isinstance(display_name, dict):
        name = (display_name.get("text") or "").strip() or None
    else:
        name = display_name

    formatted_address = p.get("formattedAddress")
    loc = p.get("location") or {}
    lat = loc.get("latitude")
    lng = loc.get("longitude")
    rating = p.get("rating")
    user_ratings_total = p.get("userRatingCount")
    business_status = p.get("businessStatus")

    now = datetime.now(timezone.utc)

    return {
        "place_id": place_id,
        "source": "GOOGLE_PLACES",
        "name": name,
        "address": formatted_address,
        "lat": lat,
        "lng": lng,
        "category": category_hint,
        "business_status": business_status,
        "rating": rating,
        "user_ratings_total": user_ratings_total,
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
        "is_retired": False
    }

# ---------------------------------------------------------------------------
# 7) DB insert (idempotent met ON CONFLICT DO NOTHING)
# ---------------------------------------------------------------------------
INSERT_SQL = text("""
INSERT INTO locations (
    place_id,
    source,
    name,
    address,
    lat,
    lng,
    category,
    business_status,
    rating,
    user_ratings_total,
    state,
    confidence_score,
    is_probable_not_open_yet,
    first_seen_at,
    last_seen_at,
    last_verified_at,
    next_check_at,
    freshness_score,
    evidence_urls,
    notes,
    is_retired
)
VALUES (
    :place_id,
    :source,
    :name,
    :address,
    :lat,
    :lng,
    :category,
    :business_status,
    :rating,
    :user_ratings_total,
    :state,
    :confidence_score,
    :is_probable_not_open_yet,
    :first_seen_at,
    :last_seen_at,
    :last_verified_at,
    :next_check_at,
    :freshness_score,
    :evidence_urls,
    :notes,
    :is_retired
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
# 8) DiscoveryBot
# ---------------------------------------------------------------------------
@dataclass
class DiscoveryConfig:
    city: str = "rotterdam"
    categories: List[str] = None
    center_lat: float = ROTTERDAM_CENTER[0]
    center_lng: float = ROTTERDAM_CENTER[1]
    nearby_radius_m: int = 1000
    grid_span_km: float = 12.0
    max_per_cell_per_category: int = 20
    inter_call_sleep_s: float = 0.15
    max_total_inserts: int = 0  # 0 = geen limiet
    max_cells_per_category: int = 0  # 0 = alle cellen

class DiscoveryBot:
    def __init__(self, cfg: DiscoveryConfig):
        self.cfg = cfg
        self.google = GooglePlacesService()

    async def run(self) -> int:
        seen: Set[str] = set()
        total_inserted = 0

        cell_spacing_m = max(100, int(self.cfg.nearby_radius_m * 0.75))
        points = list(generate_grid_points(
            self.cfg.center_lat,
            self.cfg.center_lng,
            self.cfg.grid_span_km,
            cell_spacing_m
        ))
        print(f"[DiscoveryBot] Grid opgebouwd: {len(points)} cellen (spacing {cell_spacing_m} m)")
        print(f"[DiscoveryBot] Categorieën: {', '.join(self.cfg.categories)}")
        if self.cfg.max_total_inserts > 0:
            print(f"[DiscoveryBot] Max totaal inserts: {self.cfg.max_total_inserts}")
        if self.cfg.max_cells_per_category > 0:
            print(f"[DiscoveryBot] Max cellen per categorie: {self.cfg.max_cells_per_category}")

        for cat in self.cfg.categories:
            print(f"\n[DiscoveryBot] === Verwerken categorie: {cat} ===")
            processed_cells = 0
            
            for i, (lat, lng) in enumerate(points, start=1):
                # Check max cells per category
                if self.cfg.max_cells_per_category > 0 and processed_cells >= self.cfg.max_cells_per_category:
                    print(f"[DiscoveryBot] Max cellen voor {cat} bereikt: {processed_cells}")
                    break
                
                try:
                    places = await self.google.search_nearby(
                        lat=lat,
                        lng=lng,
                        radius=self.cfg.nearby_radius_m,
                        included_types=[cat],
                        max_results=self.cfg.max_per_cell_per_category,
                        language=None
                    )
                except Exception as e:
                    print(f"[DiscoveryBot] Google call fout @({lat:.5f},{lng:.5f}) {cat}: {e}")
                    places = []

                batch: List[Dict[str, Any]] = []
                for p in places or []:
                    pid = p.get("id")
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)
                    batch.append(map_google_place_to_location_row(p, cat))

                if batch:
                    try:
                        ins = await insert_candidates(batch)
                        total_inserted += ins
                        if ins > 0:
                            print(f"[DiscoveryBot] Insert: batch={len(batch)} inserted={ins} total={total_inserted}")
                    except Exception as e:
                        print(f"[DiscoveryBot] Insert fout (batch={len(batch)}): {e}")

                processed_cells += 1
                
                # Progress indicator elke 50 cellen
                if i % 50 == 0:
                    print(f"[DiscoveryBot] {cat}: {i}/{len(points)} cellen verwerkt, {total_inserted} totaal ingevoegd")
                
                # Check max total inserts
                if self.cfg.max_total_inserts > 0 and total_inserted >= self.cfg.max_total_inserts:
                    print(f"\n[DiscoveryBot] ⚠️  Max totaal inserts bereikt: {total_inserted}. Stoppen.")
                    return total_inserted

                if self.cfg.inter_call_sleep_s:
                    await asyncio.sleep(self.cfg.inter_call_sleep_s)

        print(f"\n[DiscoveryBot] ✓ Klaar. Totaal nieuw ingevoegd (idempotent): {total_inserted}")
        return total_inserted

# ---------------------------------------------------------------------------
# 9) CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="DiscoveryBot – Grid-Based Search met rate limiting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  # Met CLI argumenten
  python workers/discovery_bot.py --city rotterdam --categories bakery,restaurant --max-total-inserts 1000
  
  # Met YAML profiel
  python workers/discovery_bot.py --profile rotterdam --config config/discovery.yml
        """
    )
    
    # Config file opties
    ap.add_argument("--profile", help="Profiel naam uit YAML config (bv. 'rotterdam')")
    ap.add_argument("--config", default="config/discovery.yml", help="Pad naar YAML config bestand")
    
    # Basis opties
    ap.add_argument("--city", help="Stad (nu alleen Rotterdam center-coördinaten)")
    ap.add_argument("--categories", 
                    help="Comma-separated Google included types (bv. bakery,restaurant,supermarket)")
    ap.add_argument("--center-lat", type=float, help="Center latitude")
    ap.add_argument("--center-lng", type=float, help="Center longitude")
    
    # Grid opties
    ap.add_argument("--nearby-radius-m", type=int, help="Nearby Search radius per cel (meters)")
    ap.add_argument("--grid-span-km", type=float, help="Span van grid in km (totale breedte/hoogte)")
    ap.add_argument("--max-per-cell-per-category", type=int, help="Maximum resultaten per cel per categorie")
    ap.add_argument("--inter-call-sleep-s", type=float, help="Pauze tussen API-calls (seconden)")
    
    # Rate limiting opties (NIEUW)
    ap.add_argument("--max-total-inserts", type=int, 
                    help="Stop zodra dit aantal inserts bereikt is (0 = geen limiet)")
    ap.add_argument("--max-cells-per-category", type=int,
                    help="Max cellen per categorie (0 = alle cellen)")
    
    return ap.parse_args()

def build_config_from_args(ns: argparse.Namespace) -> DiscoveryConfig:
    """Bouwt DiscoveryConfig vanuit CLI args en optioneel YAML profiel."""
    
    # Start met defaults
    config_dict = {
        "city": "rotterdam",
        "categories": ["bakery", "restaurant", "supermarket"],
        "center_lat": ROTTERDAM_CENTER[0],
        "center_lng": ROTTERDAM_CENTER[1],
        "nearby_radius_m": 1000,
        "grid_span_km": 12.0,
        "max_per_cell_per_category": 20,
        "inter_call_sleep_s": 0.15,
        "max_total_inserts": 0,
        "max_cells_per_category": 0,
    }
    
    # Laad YAML profiel indien opgegeven
    if ns.profile:
        yaml_config = load_yaml_config(ns.config, ns.profile)
        if yaml_config:
            print(f"[DiscoveryBot] Profiel '{ns.profile}' geladen uit {ns.config}")
            # Update met YAML waardes
            for key in config_dict.keys():
                if key in yaml_config:
                    config_dict[key] = yaml_config[key]
    
    # Override met CLI argumenten (indien opgegeven)
    if ns.city is not None:
        config_dict["city"] = ns.city
    if ns.categories is not None:
        config_dict["categories"] = [c.strip() for c in ns.categories.split(",") if c.strip()]
    if ns.center_lat is not None:
        config_dict["center_lat"] = ns.center_lat
    if ns.center_lng is not None:
        config_dict["center_lng"] = ns.center_lng
    if ns.nearby_radius_m is not None:
        config_dict["nearby_radius_m"] = ns.nearby_radius_m
    if ns.grid_span_km is not None:
        config_dict["grid_span_km"] = ns.grid_span_km
    if ns.max_per_cell_per_category is not None:
        config_dict["max_per_cell_per_category"] = ns.max_per_cell_per_category
    if ns.inter_call_sleep_s is not None:
        config_dict["inter_call_sleep_s"] = ns.inter_call_sleep_s
    if ns.max_total_inserts is not None:
        config_dict["max_total_inserts"] = ns.max_total_inserts
    if ns.max_cells_per_category is not None:
        config_dict["max_cells_per_category"] = ns.max_cells_per_category
    
    return DiscoveryConfig(**config_dict)

async def main_async(ns: argparse.Namespace) -> None:
    cfg = build_config_from_args(ns)
    
    print(f"\n[DiscoveryBot] Configuratie:")
    print(f"  Stad: {cfg.city}")
    print(f"  Center: ({cfg.center_lat:.4f}, {cfg.center_lng:.4f})")
    print(f"  Categorieën: {cfg.categories}")
    print(f"  Grid span: {cfg.grid_span_km} km")
    print(f"  Nearby radius: {cfg.nearby_radius_m} m")
    print(f"  Max per cel: {cfg.max_per_cell_per_category}")
    print(f"  Sleep tijd: {cfg.inter_call_sleep_s} s")
    if cfg.max_total_inserts > 0:
        print(f"  Max totaal inserts: {cfg.max_total_inserts}")
    if cfg.max_cells_per_category > 0:
        print(f"  Max cellen/categorie: {cfg.max_cells_per_category}")
    print()
    
    bot = DiscoveryBot(cfg)
    await bot.run()

def main() -> None:
    ns = parse_args()
    try:
        asyncio.run(main_async(ns))
    except KeyboardInterrupt:
        print("\n[DiscoveryBot] Afgebroken door gebruiker.")
    except Exception as e:
        print(f"\n[DiscoveryBot] FOUT: {e}")
        raise

if __name__ == "__main__":
    main()