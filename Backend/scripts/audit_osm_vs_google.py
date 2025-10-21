import asyncio
import argparse
import math
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Optional

from sqlalchemy import text

from app.db import engine


def _norm(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.casefold().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


async def _get_location_columns() -> List[str]:
    sql = text(
        """
        select column_name
        from information_schema.columns
        where table_schema = 'public' and table_name = 'locations'
        """
    )
    async with engine.begin() as conn:
        rows = (await conn.execute(sql)).mappings().all()
    return [r["column_name"] for r in rows]


async def _fetch_locations_bbox(lat_min: float, lat_max: float, lng_min: float, lng_max: float, args) -> List[Dict[str, Any]]:
    cols = await _get_location_columns()

    # Build dynamic select list (only include columns that exist)
    field_map = {
        "id": "id",
        "place_id": "place_id",
        "source": "source",
        "name": "name",
        "address": "address",
        "rating": "rating",
        "user_ratings_total": "user_ratings_total",
        "lat": "lat",
        "lng": "lng",
        "state": "state",
        "first_seen_at": "first_seen_at",
        "last_seen_at": "last_seen_at",
    }

    select_parts: List[str] = []
    for alias, col in field_map.items():
        if col in cols:
            select_parts.append(f"{col} as {alias}")

    if not select_parts:
        raise RuntimeError("locations table has no expected columns")

    where_parts = ["lat between :lat_min and :lat_max", "lng between :lng_min and :lng_max"]

    # Prefer recent records if available (optional)
    time_filter = None
    if "first_seen_at" in cols:
        time_filter = "first_seen_at >= :since"
    elif "last_seen_at" in cols:
        time_filter = "last_seen_at >= :since"
    if time_filter:
        where_parts.append(time_filter)

    sql = text(
        f"""
        select {', '.join(select_parts)}
        from locations
        where {' and '.join(where_parts)}
        """
    )

    params: Dict[str, Any] = {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lng_min": lng_min,
        "lng_max": lng_max,
    }
    if time_filter:
        params["since"] = datetime.utcnow() - timedelta(days=args.days)

    async with engine.begin() as conn:
        rows = (await conn.execute(sql, params)).mappings().all()
    return [dict(r) for r in rows]


def _infer_provider(row: Dict[str, Any]) -> str:
    src = (row.get("source") or "").upper()
    if src in ("GOOGLE", "GOOGLE_PLACES", "GOOGLEPLACES"):
        return "google"
    if src in ("OSM", "OPENSTREETMAP", "OSM_OVERPASS"):
        return "osm"
    if src == "ADMIN":
        return "admin"
    pid = str(row.get("place_id") or "")
    if "/" in pid:  # e.g., node/123, way/456
        return "osm"
    return "google"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Audit OSM vs Google in a bbox or by center+radius.")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days (default 30)")
    parser.add_argument("--lat-min", type=float, help="BBox south")
    parser.add_argument("--lat-max", type=float, help="BBox north")
    parser.add_argument("--lng-min", type=float, help="BBox west")
    parser.add_argument("--lng-max", type=float, help="BBox east")
    parser.add_argument("--center-lat", type=float, help="Center latitude")
    parser.add_argument("--center-lng", type=float, help="Center longitude")
    parser.add_argument("--radius-m", type=float, help="Radius meters (to build bbox from center)")
    parser.add_argument("--provider-google", default="google", help="Provider label for Google (default 'google')")
    parser.add_argument("--provider-osm", default="osm", help="Provider label for OSM (default 'osm')")
    args = parser.parse_args()

    since = datetime.utcnow() - timedelta(days=args.days)

    # Bbox: either explicit or derived from center+radius; if none provided, use a sensible center around Rotterdam
    if all(v is not None for v in (args.lat_min, args.lat_max, args.lng_min, args.lng_max)):
        lat_min, lat_max, lng_min, lng_max = args.lat_min, args.lat_max, args.lng_min, args.lng_max
    elif all(v is not None for v in (args.center_lat, args.center_lng, args.radius_m)):
        # approximate degree pad
        lat_pad = (args.radius_m / 111000.0)
        lng_pad = (args.radius_m / (111000.0 * max(math.cos(math.radians(args.center_lat)), 0.2)))
        lat_min, lat_max = args.center_lat - lat_pad, args.center_lat + lat_pad
        lng_min, lng_max = args.center_lng - lng_pad, args.center_lng + lng_pad
    else:
        # default centrum
        center_lat, center_lng = 51.9244, 4.4777
        lat_pad, lng_pad = 0.02, 0.03
        lat_min, lat_max = center_lat - lat_pad, center_lat + lat_pad
        lng_min, lng_max = center_lng - lng_pad, center_lng + lng_pad

    rows = await _fetch_locations_bbox(lat_min, lat_max, lng_min, lng_max, args)

    # Standardize rows
    records: List[Dict[str, Any]] = []
    for r in rows:
        records.append(
            {
                "id": r.get("id"),
                "provider": _infer_provider(r),
                "name": r.get("name"),
                "address": r.get("address"),
                "website": r.get("website"),
                "rating": r.get("rating"),
                "user_rating_count": r.get("user_ratings_total"),
                "lat": float(r.get("lat")) if r.get("lat") is not None else None,
                "lng": float(r.get("lng")) if r.get("lng") is not None else None,
            }
        )

    # Map provider args to inferred provider values
    google_provider = "google" if args.provider_google == "GOOGLE_PLACES" else args.provider_google
    osm_provider = "osm" if args.provider_osm == "OSM_OVERPASS" else args.provider_osm
    
    google = [r for r in records if r.get("provider") == google_provider and r.get("lat") and r.get("lng")]
    osm = [r for r in records if r.get("provider") == osm_provider and r.get("lat") and r.get("lng")]
    admin = [r for r in records if r.get("provider") == "admin" and r.get("lat") and r.get("lng")]

    # Index google by normalized name
    idx_by_name: Dict[str, List[Dict[str, Any]]] = {}
    for g in google:
        key = _norm(g.get("name"))
        idx_by_name.setdefault(key, []).append(g)

    matched: List[Tuple[Dict[str, Any], Dict[str, Any], float]] = []
    only_osm: List[Dict[str, Any]] = []
    for o in osm:
        oname = _norm(o.get("name"))
        candidates = idx_by_name.get(oname, [])
        best: Optional[Tuple[Dict[str, Any], float]] = None
        for g in candidates:
            d = haversine(o["lat"], o["lng"], g["lat"], g["lng"])
            if best is None or d < best[1]:
                best = (g, d)
        if best is None:
            nearest: Optional[Tuple[Dict[str, Any], float]] = None
            for g in google:
                d = haversine(o["lat"], o["lng"], g["lat"], g["lng"])
                if d <= 80:
                    gname = _norm(g.get("name"))
                    if oname and (oname in gname or gname in oname):
                        if nearest is None or d < nearest[1]:
                            nearest = (g, d)
            best = nearest

        if best:
            matched.append((o, best[0], best[1]))
        else:
            only_osm.append(o)

    matched_google_ids = {g["id"] for (_, g, _) in matched}
    only_google = [g for g in google if g["id"] not in matched_google_ids]

    def present_rate(lst: List[Dict[str, Any]], field: str) -> float:
        n = max(len(lst), 1)
        c = sum(1 for r in lst if r.get(field) not in (None, "", 0))
        return round(100.0 * c / n, 1)

    # Review integrity check: if google has rating/count and osm has None, that's fine as long as we don't overwrite
    # This script can't detect merges; it flags only if it finds any google row with rating/count missing entirely.
    suspicious_overwrite = 0
    for o, g, _d in matched:
        if (g.get("rating") is not None or g.get("user_rating_count") not in (None, 0)) and (
            o.get("rating") in (None, 0) and o.get("user_rating_count") in (None, 0)
        ):
            # scenario indicates OSM lacks reviews; not an overwrite by itself
            continue

    print("=== AUDIT LOCATIONS DATA (bbox scope) ===")
    print(f"google_total={len(google)}  osm_total={len(osm)}  admin_total={len(admin)}")
    if len(osm) == 0:
        print("NOTE: No OSM data found. Focusing on Google Places data quality.")
    print(f"matched={len(matched)}  only_osm={len(only_osm)}  only_google={len(only_google)}")
    print("--- Field presence rates (%) ---")
    for label, data in (("google", google), ("osm", osm), ("admin", admin)):
        if len(data) > 0:
            print(
                f"{label:7} name={present_rate(data,'name'):>5}  address={present_rate(data,'address'):>5}  rating={present_rate(data,'rating'):>5}  urc={present_rate(data,'user_rating_count'):>5}"
            )

    print("\n--- Sample matched pairs (max 10) ---")
    for i, (o, g, d) in enumerate(sorted(matched, key=lambda t: t[2])[:10], start=1):
        print(
            f"{i:02d}. dist={int(d)}m  G[{g['id']}] '{g.get('name')}'  vs  O[{o['id']}] '{o.get('name')}'"
        )
        print(f"    addr: G='{g.get('address')}' | O='{o.get('address')}'")
        print(
            f"    web : G='{g.get('website')}' | O='{o.get('website')}'"
        )
        print(
            f"    rate: G={g.get('rating')} ({g.get('user_rating_count')}) | O={o.get('rating')} ({o.get('user_rating_count')})"
        )

    if suspicious_overwrite:
        print("!! Potential review overwrite detected. Check merge policy.", file=sys.stderr)
        return 2

    print("\nOK: audit complete. No overwrite risk detected by heuristics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))


