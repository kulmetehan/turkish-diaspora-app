# Backend/app/workers/activity_stream_ingest_worker.py
"""
Activity Stream Ingest Worker

Processes canonical activity tables (check_ins, location_reactions, location_notes, 
favorites, poll_responses) and denormalizes them into activity_stream for fast feed queries.

Runs every 1 minute, processes up to 1000 events per run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
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
logger = logger.bind(worker="activity_stream_ingest")

BATCH_SIZE = 1000
PROCESSING_DELAY_SECONDS = 5  # Only process events older than 5 seconds


async def process_check_ins(limit: int) -> int:
    """Process unprocessed check-ins into activity_stream."""
    sql = f"""
        SELECT 
            ci.id,
            ci.location_id,
            ci.user_id,
            ci.client_id,
            ci.created_at,
            l.lat,
            l.lng,
            l.category
        FROM check_ins ci
        JOIN locations l ON ci.location_id = l.id
        WHERE ci.processed_in_activity_stream = false
          AND ci.created_at <= now() - interval '{PROCESSING_DELAY_SECONDS} seconds'
        ORDER BY ci.created_at ASC
        LIMIT $1
    """
    
    rows = await fetch(sql, limit)
    if not rows:
        return 0
    
    processed = 0
    for row in rows:
        actor_type = 'user' if row.get('user_id') else 'client'
        actor_id = row.get('user_id')
        client_id = row.get('client_id') or row.get('user_id')  # Fallback for traceability
        
        # Derive city_key from coordinates
        lat = float(row.get('lat')) if row.get('lat') is not None else None
        lng = float(row.get('lng')) if row.get('lng') is not None else None
        city_key = get_city_key_from_coords(lat, lng)
        category_key = row.get('category')  # Use category column instead of category_key
        
        # Insert into activity_stream
        insert_sql = """
            INSERT INTO activity_stream 
            (actor_type, actor_id, client_id, activity_type, location_id, city_key, category_key, payload, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        try:
            await execute(
                insert_sql,
                actor_type,
                actor_id,
                client_id,
                'check_in',
                row['location_id'],
                city_key,
                category_key,
                json.dumps({}),  # Empty payload for check-ins
                row['created_at'],
            )
            
            # Mark as processed
            mark_sql = """
                UPDATE check_ins
                SET processed_in_activity_stream = true
                WHERE id = $1
            """
            await execute(mark_sql, row['id'])
            processed += 1
        except Exception as e:
            logger.error("failed_to_process_check_in", check_in_id=row['id'], error=str(e))
    
    return processed


async def process_reactions(limit: int) -> int:
    """Process unprocessed reactions into activity_stream."""
    sql = f"""
        SELECT 
            lr.id,
            lr.location_id,
            lr.user_id,
            lr.client_id,
            lr.reaction_type,
            lr.created_at,
            l.lat,
            l.lng,
            l.category
        FROM location_reactions lr
        JOIN locations l ON lr.location_id = l.id
        WHERE lr.processed_in_activity_stream = false
          AND lr.created_at <= now() - interval '{PROCESSING_DELAY_SECONDS} seconds'
        ORDER BY lr.created_at ASC
        LIMIT $1
    """
    
    rows = await fetch(sql, limit)
    if not rows:
        return 0
    
    processed = 0
    for row in rows:
        actor_type = 'user' if row.get('user_id') else 'client'
        actor_id = row.get('user_id')
        client_id = row.get('client_id') or row.get('user_id')
        
        # Derive city_key from coordinates
        lat = float(row.get('lat')) if row.get('lat') is not None else None
        lng = float(row.get('lng')) if row.get('lng') is not None else None
        city_key = get_city_key_from_coords(lat, lng)
        category_key = row.get('category')  # Use category column instead of category_key
        
        payload = json.dumps({"reaction_type": row['reaction_type']})
        
        insert_sql = """
            INSERT INTO activity_stream 
            (actor_type, actor_id, client_id, activity_type, location_id, city_key, category_key, payload, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        try:
            await execute(
                insert_sql,
                actor_type,
                actor_id,
                client_id,
                'reaction',
                row['location_id'],
                city_key,
                category_key,
                payload,
                row['created_at'],
            )
            
            mark_sql = """
                UPDATE location_reactions
                SET processed_in_activity_stream = true
                WHERE id = $1
            """
            await execute(mark_sql, row['id'])
            processed += 1
        except Exception as e:
            logger.error("failed_to_process_reaction", reaction_id=row['id'], error=str(e))
    
    return processed


async def process_notes(limit: int) -> int:
    """Process unprocessed notes into activity_stream."""
    sql = f"""
        SELECT 
            ln.id,
            ln.location_id,
            ln.user_id,
            ln.client_id,
            ln.content,
            ln.created_at,
            l.lat,
            l.lng,
            l.category
        FROM location_notes ln
        JOIN locations l ON ln.location_id = l.id
        WHERE ln.processed_in_activity_stream = false
          AND ln.created_at <= now() - interval '{PROCESSING_DELAY_SECONDS} seconds'
        ORDER BY ln.created_at ASC
        LIMIT $1
    """
    
    rows = await fetch(sql, limit)
    if not rows:
        return 0
    
    processed = 0
    for row in rows:
        actor_type = 'user' if row.get('user_id') else 'client'
        actor_id = row.get('user_id')
        client_id = row.get('client_id') or row.get('user_id')
        
        # Derive city_key from coordinates
        lat = float(row.get('lat')) if row.get('lat') is not None else None
        lng = float(row.get('lng')) if row.get('lng') is not None else None
        city_key = get_city_key_from_coords(lat, lng)
        category_key = row.get('category')  # Use category column instead of category_key
        
        # Preview first 100 chars
        note_preview = row['content'][:100] if len(row['content']) > 100 else row['content']
        payload = json.dumps({"note_preview": note_preview})
        
        insert_sql = """
            INSERT INTO activity_stream 
            (actor_type, actor_id, client_id, activity_type, location_id, city_key, category_key, payload, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        try:
            await execute(
                insert_sql,
                actor_type,
                actor_id,
                client_id,
                'note',
                row['location_id'],
                city_key,
                category_key,
                payload,
                row['created_at'],
            )
            
            mark_sql = """
                UPDATE location_notes
                SET processed_in_activity_stream = true
                WHERE id = $1
            """
            await execute(mark_sql, row['id'])
            processed += 1
        except Exception as e:
            logger.error("failed_to_process_note", note_id=row['id'], error=str(e))
    
    return processed


async def process_favorites(limit: int) -> int:
    """Process unprocessed favorites into activity_stream."""
    sql = f"""
        SELECT 
            f.id,
            f.location_id,
            f.user_id,
            f.client_id,
            f.created_at,
            l.lat,
            l.lng,
            l.category
        FROM favorites f
        JOIN locations l ON f.location_id = l.id
        WHERE f.processed_in_activity_stream = false
          AND f.created_at <= now() - interval '{PROCESSING_DELAY_SECONDS} seconds'
        ORDER BY f.created_at ASC
        LIMIT $1
    """
    
    rows = await fetch(sql, limit)
    if not rows:
        return 0
    
    processed = 0
    for row in rows:
        actor_type = 'user' if row.get('user_id') else 'client'
        actor_id = row.get('user_id')
        client_id = row.get('client_id') or row.get('user_id')
        
        # Derive city_key from coordinates
        lat = float(row.get('lat')) if row.get('lat') is not None else None
        lng = float(row.get('lng')) if row.get('lng') is not None else None
        city_key = get_city_key_from_coords(lat, lng)
        category_key = row.get('category')  # Use category column instead of category_key
        
        insert_sql = """
            INSERT INTO activity_stream 
            (actor_type, actor_id, client_id, activity_type, location_id, city_key, category_key, payload, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        try:
            await execute(
                insert_sql,
                actor_type,
                actor_id,
                client_id,
                'favorite',
                row['location_id'],
                city_key,
                category_key,
                json.dumps({}),
                row['created_at'],
            )
            
            mark_sql = """
                UPDATE favorites
                SET processed_in_activity_stream = true
                WHERE id = $1
            """
            await execute(mark_sql, row['id'])
            processed += 1
        except Exception as e:
            logger.error("failed_to_process_favorite", favorite_id=row['id'], error=str(e))
    
    return processed


async def process_poll_responses(limit: int) -> int:
    """Process unprocessed poll responses into activity_stream."""
    sql = f"""
        SELECT 
            pr.id,
            pr.poll_id,
            pr.user_id,
            pr.client_id,
            pr.created_at
        FROM poll_responses pr
        WHERE pr.processed_in_activity_stream = false
          AND pr.created_at <= now() - interval '{PROCESSING_DELAY_SECONDS} seconds'
        ORDER BY pr.created_at ASC
        LIMIT $1
    """
    
    rows = await fetch(sql, limit)
    if not rows:
        return 0
    
    processed = 0
    for row in rows:
        actor_type = 'user' if row.get('user_id') else 'client'
        actor_id = row.get('user_id')
        client_id = row.get('client_id') or row.get('user_id')
        
        payload = json.dumps({"poll_id": row['poll_id']})
        
        insert_sql = """
            INSERT INTO activity_stream 
            (actor_type, actor_id, client_id, activity_type, location_id, city_key, category_key, payload, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        try:
            await execute(
                insert_sql,
                actor_type,
                actor_id,
                client_id,
                'poll_response',
                None,  # No location_id for polls
                None,  # No city_key
                None,  # No category_key
                payload,
                row['created_at'],
            )
            
            mark_sql = """
                UPDATE poll_responses
                SET processed_in_activity_stream = true
                WHERE id = $1
            """
            await execute(mark_sql, row['id'])
            processed += 1
        except Exception as e:
            logger.error("failed_to_process_poll_response", response_id=row['id'], error=str(e))
    
    return processed


async def process_bulletin_posts(limit: int) -> int:
    """Process unprocessed bulletin posts into activity_stream."""
    sql = f"""
        SELECT 
            bp.id,
            bp.created_by_user_id,
            bp.created_by_business_id,
            bp.creator_type,
            bp.title,
            bp.category,
            bp.city,
            bp.linked_location_id,
            bp.created_at,
            l.lat,
            l.lng,
            l.category as location_category
        FROM bulletin_posts bp
        LEFT JOIN locations l ON bp.linked_location_id = l.id
        WHERE bp.processed_in_activity_stream = false
          AND bp.status = 'active'
          AND bp.moderation_status = 'approved'
          AND bp.created_at <= now() - interval '{PROCESSING_DELAY_SECONDS} seconds'
        ORDER BY bp.created_at ASC
        LIMIT $1
    """
    
    rows = await fetch(sql, limit)
    if not rows:
        return 0
    
    processed = 0
    for row in rows:
        # Determine actor info
        if row.get('creator_type') == 'user' and row.get('created_by_user_id'):
            actor_type = 'user'
            actor_id = row.get('created_by_user_id')
            client_id = row.get('created_by_user_id')  # Fallback for traceability
        elif row.get('creator_type') == 'business' and row.get('created_by_business_id'):
            actor_type = 'business'
            # Convert BIGINT business_id to string for actor_id (UUID column accepts text)
            # Store as string representation since actor_id is UUID type
            actor_id = str(row.get('created_by_business_id'))
            client_id = None  # Businesses don't have client_id
        else:
            # Fallback: treat as anonymous/client
            actor_type = 'client'
            actor_id = None
            client_id = None
        
        # Derive city_key from bulletin post city or linked location
        city_key = None
        if row.get('city'):
            # Use bulletin post city directly if available
            city_key = row.get('city').lower().replace(' ', '_') if row.get('city') else None
        elif row.get('lat') and row.get('lng'):
            # Fallback to deriving from coordinates
            lat = float(row.get('lat')) if row.get('lat') is not None else None
            lng = float(row.get('lng')) if row.get('lng') is not None else None
            city_key = get_city_key_from_coords(lat, lng) if lat and lng else None
        
        # Use location category if available, otherwise None
        category_key = row.get('location_category')
        
        # Build payload with bulletin post details
        payload = json.dumps({
            "bulletin_post_id": row['id'],
            "title": row.get('title', '')[:100],  # Truncate for payload
            "category": row.get('category'),
            "city": row.get('city'),
        })
        
        insert_sql = """
            INSERT INTO activity_stream 
            (actor_type, actor_id, client_id, activity_type, location_id, city_key, category_key, payload, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        try:
            await execute(
                insert_sql,
                actor_type,
                actor_id,
                client_id,
                'bulletin_post',
                row.get('linked_location_id'),  # Can be NULL
                city_key,
                category_key,
                payload,
                row['created_at'],
            )
            
            # Mark as processed
            mark_sql = """
                UPDATE bulletin_posts
                SET processed_in_activity_stream = true
                WHERE id = $1
            """
            await execute(mark_sql, row['id'])
            processed += 1
        except Exception as e:
            logger.error("failed_to_process_bulletin_post", bulletin_post_id=row['id'], error=str(e))
    
    return processed


async def run_once(rebuild: bool = False) -> Dict[str, Any]:
    """Run one iteration of the activity stream ingest worker."""
    run_id = None
    try:
        run_id = await start_worker_run("activity_stream_ingest")
        await mark_worker_run_running(run_id)
    except Exception as e:
        logger.warning("failed_to_start_worker_run", error=str(e))
    
    with with_run_id() as rid:
        stats = {
            'check_ins': 0,
            'reactions': 0,
            'notes': 0,
            'favorites': 0,
            'poll_responses': 0,
            'bulletin_posts': 0,
        }
        
        if rebuild:
            logger.info("activity_stream_rebuild_start")
            # TODO: Truncate activity_stream and rebuild from all canonical tables
            # For now, just process all unprocessed events
            stats['check_ins'] = await process_check_ins(BATCH_SIZE * 10)
            stats['reactions'] = await process_reactions(BATCH_SIZE * 10)
            stats['notes'] = await process_notes(BATCH_SIZE * 10)
            stats['favorites'] = await process_favorites(BATCH_SIZE * 10)
            stats['poll_responses'] = await process_poll_responses(BATCH_SIZE * 10)
            stats['bulletin_posts'] = await process_bulletin_posts(BATCH_SIZE * 10)
        else:
            # Process each canonical table
            stats['check_ins'] = await process_check_ins(BATCH_SIZE)
            stats['reactions'] = await process_reactions(BATCH_SIZE)
            stats['notes'] = await process_notes(BATCH_SIZE)
            stats['favorites'] = await process_favorites(BATCH_SIZE)
            stats['poll_responses'] = await process_poll_responses(BATCH_SIZE)
            stats['bulletin_posts'] = await process_bulletin_posts(BATCH_SIZE)
        
        total = sum(stats.values())
        logger.info("activity_stream_ingest_complete", **stats, total=total)
    
    if run_id:
        try:
            await finish_worker_run(run_id, "completed", {"stats": stats})
        except Exception as e:
            logger.warning("failed_to_finish_worker_run", error=str(e))
    
    return stats


async def run_forever(interval_seconds: int = 60) -> None:
    """Run worker continuously with specified interval."""
    await init_db_pool()
    
    logger.info("activity_stream_worker_started", interval_seconds=interval_seconds)
    
    while True:
        try:
            await run_once()
        except Exception as e:
            logger.error("activity_stream_worker_error", error=str(e))
        
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild entire stream")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds")
    
    args = parser.parse_args()
    
    if args.once:
        asyncio.run(run_once(rebuild=args.rebuild))
    else:
        asyncio.run(run_forever(interval_seconds=args.interval))


