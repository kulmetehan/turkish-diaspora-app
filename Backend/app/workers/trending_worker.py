# Backend/app/workers/trending_worker.py
"""
Trending Locations Worker

Calculates trending scores for locations based on check-ins, reactions, and notes.
Uses exponential decay formula: score = (Wc*C + Wr*R + Wn*N) * exp(-age_hours/half_life)

Runs every 5 minutes for near-real-time updates, hourly for full recalculation.
"""
from __future__ import annotations

import argparse
import asyncio
import math
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path
import sys

# Path setup
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent
BACKEND_DIR = APP_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.db_service import init_db_pool, fetch, execute
from services.cities_config_service import get_city_key_from_coords
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    finish_worker_run,
)

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="trending")

# Trending formula weights
WEIGHT_CHECK_INS = 3.0
WEIGHT_REACTIONS = 1.5
WEIGHT_NOTES = 2.0

# Decay parameters
HALF_LIFE_HOURS = 24.0  # Score halves every 24 hours


def calculate_trending_score(
    check_ins: int,
    reactions: int,
    notes: int,
    age_hours: float,
) -> float:
    """
    Calculate trending score with exponential decay.
    
    score = (Wc*C + Wr*R + Wn*N) * exp(-age_hours / half_life)
    """
    base_score = (
        WEIGHT_CHECK_INS * check_ins +
        WEIGHT_REACTIONS * reactions +
        WEIGHT_NOTES * notes
    )
    
    decay_factor = math.exp(-age_hours / HALF_LIFE_HOURS)
    
    return base_score * decay_factor


async def calculate_trending_for_window(
    city_key: str,
    category_key: str | None,
    window_hours: float,
) -> List[Dict[str, Any]]:
    """Calculate trending scores for a specific city/category/window."""
    # Get activity counts per location in the time window
    # Note: We fetch all VERIFIED locations and filter by city_key in Python
    # since locations table doesn't have city_key column
    sql = f"""
        SELECT 
            l.id as location_id,
            l.lat,
            l.lng,
            l.category,
            COUNT(DISTINCT ci.id) as check_ins_count,
            COUNT(DISTINCT lr.id) as reactions_count,
            COUNT(DISTINCT ln.id) as notes_count,
            EXTRACT(EPOCH FROM (now() - MIN(COALESCE(ci.created_at, lr.created_at, ln.created_at)))) / 3600.0 as oldest_age_hours
        FROM locations l
        LEFT JOIN check_ins ci ON ci.location_id = l.id 
            AND ci.created_at >= now() - interval '{window_hours} hours'
        LEFT JOIN location_reactions lr ON lr.location_id = l.id
            AND lr.created_at >= now() - interval '{window_hours} hours'
        LEFT JOIN location_notes ln ON ln.location_id = l.id
            AND ln.created_at >= now() - interval '{window_hours} hours'
        WHERE l.state = 'VERIFIED'
          AND ($1::text IS NULL OR l.category = $1)
        GROUP BY l.id, l.lat, l.lng, l.category
        HAVING COUNT(DISTINCT ci.id) > 0 
            OR COUNT(DISTINCT lr.id) > 0 
            OR COUNT(DISTINCT ln.id) > 0
        ORDER BY 
            (COUNT(DISTINCT ci.id) + COUNT(DISTINCT lr.id) + COUNT(DISTINCT ln.id)) DESC
    """
    
    rows = await fetch(sql, category_key)
    
    results = []
    for row in rows:
        # Derive city_key from coordinates
        lat = float(row.get('lat')) if row.get('lat') is not None else None
        lng = float(row.get('lng')) if row.get('lng') is not None else None
        location_city_key = get_city_key_from_coords(lat, lng)
        
        # Filter by requested city_key
        if city_key and location_city_key != city_key:
            continue
        
        score = calculate_trending_score(
            check_ins=row.get('check_ins_count', 0) or 0,
            reactions=row.get('reactions_count', 0) or 0,
            notes=row.get('notes_count', 0) or 0,
            age_hours=float(row.get('oldest_age_hours', 0) or 0),
        )
        
        results.append({
            'location_id': row['location_id'],
            'city_key': location_city_key or 'unknown',  # Use derived city_key
            'category_key': row.get('category'),  # Use category column
            'score': score,
            'check_ins_count': row.get('check_ins_count', 0) or 0,
            'reactions_count': row.get('reactions_count', 0) or 0,
            'notes_count': row.get('notes_count', 0) or 0,
        })
    
    # Sort by score and assign ranks
    results.sort(key=lambda x: x['score'], reverse=True)
    for i, result in enumerate(results, start=1):
        result['rank'] = i
    
    return results


async def update_trending_table(
    window: str,
    city_key: str,
    category_key: str | None,
    results: List[Dict[str, Any]],
) -> int:
    """Update trending_locations table with new scores."""
    if not results:
        return 0
    
    # Upsert into trending_locations
    upsert_sql = """
        INSERT INTO trending_locations 
        (location_id, city_key, category_key, "window", score, rank, check_ins_count, reactions_count, notes_count, raw_counts, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, now())
        ON CONFLICT (location_id, city_key, category_key, "window")
        DO UPDATE SET
            score = EXCLUDED.score,
            rank = EXCLUDED.rank,
            check_ins_count = EXCLUDED.check_ins_count,
            reactions_count = EXCLUDED.reactions_count,
            notes_count = EXCLUDED.notes_count,
            raw_counts = EXCLUDED.raw_counts,
            updated_at = now()
    """
    
    updated = 0
    for result in results:
        raw_counts = {
            'check_ins': result['check_ins_count'],
            'reactions': result['reactions_count'],
            'notes': result['notes_count'],
        }
        
        await execute(
            upsert_sql,
            result['location_id'],
            result['city_key'],
            result['category_key'],
            window,
            result['score'],
            result['rank'],
            result['check_ins_count'],
            result['reactions_count'],
            result['notes_count'],
            json.dumps(raw_counts),
        )
        updated += 1
    
    return updated


async def run_trending_calculation(
    window: str = "24h",
    city_key: str | None = None,
    category_key: str | None = None,
) -> Dict[str, Any]:
    """Run trending calculation for specified parameters."""
    window_hours_map = {
        '5m': 5/60,
        '1h': 1.0,
        '24h': 24.0,
        '7d': 168.0,
    }
    
    window_hours = window_hours_map.get(window, 24.0)
    
    # Get all cities if not specified
    # Since locations table doesn't have city_key, we'll process all VERIFIED locations
    # and derive city_key in calculate_trending_for_window
    if city_key:
        cities = [city_key]
    else:
        # For now, use known cities from config
        # In future, we could query activity_stream for distinct city_key values
        from services.cities_config_service import load_cities_config
        config = load_cities_config()
        cities = list(config.get("cities", {}).keys())
    
    stats = {
        'window': window,
        'cities_processed': 0,
        'locations_updated': 0,
    }
    
    for city in cities:
        results = await calculate_trending_for_window(city, category_key, window_hours)
        updated = await update_trending_table(window, city, category_key, results)
        
        stats['cities_processed'] += 1
        stats['locations_updated'] += updated
        
        logger.info(
            "trending_calculation_complete",
            city_key=city,
            category_key=category_key,
            window=window,
            locations_updated=updated,
        )
    
    return stats


async def run_once(full_recalc: bool = False) -> Dict[str, Any]:
    """Run one iteration of trending calculation."""
    run_id = None
    try:
        run_id = await start_worker_run("trending")
        await mark_worker_run_running(run_id)
    except Exception as e:
        logger.warning("failed_to_start_worker_run", error=str(e))
    
    with with_run_id() as rid:
        if full_recalc:
            # Full recalculation for all windows
            windows = ['5m', '1h', '24h', '7d']
        else:
            # Near-real-time update (5m window only)
            windows = ['5m']
        
        all_stats = []
        for window in windows:
            stats = await run_trending_calculation(window=window)
            all_stats.append(stats)
        
        result = {'windows': all_stats}
    
    if run_id:
        try:
            await finish_worker_run(run_id, "completed", result)
        except Exception as e:
            logger.warning("failed_to_finish_worker_run", error=str(e))
    
    return result


async def run_forever(interval_seconds: int = 300) -> None:  # 5 minutes default
    """Run worker continuously."""
    await init_db_pool()
    
    logger.info("trending_worker_started", interval_seconds=interval_seconds)
    
    while True:
        try:
            await run_once(full_recalc=False)
        except Exception as e:
            logger.error("trending_worker_error", error=str(e))
        
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--full", action="store_true", help="Full recalculation for all windows")
    parser.add_argument("--interval", type=int, default=300, help="Interval in seconds")
    
    args = parser.parse_args()
    
    if args.once:
        asyncio.run(run_once(full_recalc=args.full))
    else:
        asyncio.run(run_forever(interval_seconds=args.interval))

