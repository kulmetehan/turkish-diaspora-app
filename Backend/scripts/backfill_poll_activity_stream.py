#!/usr/bin/env python3
"""
Backfill activity_stream entries for existing polls.
Run this once after deploying the poll activity_stream creation fix.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

# Path setup
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool, fetch, execute
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="backfill_polls")
logger = get_logger()


async def backfill_poll_activity_stream():
    """Create activity_stream entries for polls that don't have them."""
    
    # Find polls without activity_stream entries
    check_sql = """
        SELECT p.id, p.title, p.question, p.targeting_city_key, p.created_at
        FROM polls p
        WHERE NOT EXISTS (
            SELECT 1 FROM activity_stream ast
            WHERE ast.activity_type = 'poll'
            AND (ast.payload->>'poll_id')::int = p.id
        )
    """
    
    polls = await fetch(check_sql)
    
    if not polls:
        logger.info("backfill_poll_activity_stream_complete", found=0)
        return
    
    logger.info("backfill_poll_activity_stream_start", count=len(polls))
    
    # System UUID for business/system actors (all zeros)
    # This satisfies the constraint requirement that business actor_type must have actor_id NOT NULL
    system_uuid = "00000000-0000-0000-0000-000000000000"
    
    insert_sql = """
        INSERT INTO activity_stream 
        (actor_type, actor_id, client_id, activity_type, location_id, city_key, category_key, payload, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT DO NOTHING
    """
    
    created = 0
    for poll in polls:
        payload = json.dumps({
            "poll_id": poll["id"],
            "title": poll.get("title"),
            "question": poll.get("question")
        })
        
        try:
            await execute(
                insert_sql,
                'business',  # actor_type
                system_uuid,  # actor_id (system UUID for admin-created polls)
                system_uuid,  # client_id (system UUID for admin-created polls)
                'poll',  # activity_type
                None,  # location_id
                poll.get("targeting_city_key"),  # city_key
                None,  # category_key
                payload,
                poll.get("created_at") or datetime.now(),
            )
            created += 1
            logger.debug("poll_activity_stream_created", poll_id=poll["id"])
        except Exception as e:
            logger.error(
                "backfill_poll_activity_stream_error",
                poll_id=poll["id"],
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
    
    logger.info("backfill_poll_activity_stream_complete", found=len(polls), created=created)


async def main():
    """Main entry point."""
    try:
        await init_db_pool()
        await backfill_poll_activity_stream()
    except Exception as e:
        logger.error("backfill_failed", error=str(e), exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup handled by context manager
        pass


if __name__ == "__main__":
    asyncio.run(main())
