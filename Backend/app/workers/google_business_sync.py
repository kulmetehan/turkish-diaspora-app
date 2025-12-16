# Backend/app/workers/google_business_sync.py
"""
Google Business Sync Worker

Periodically syncs location data from Google Business Profiles for opted-in businesses.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Pathing
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent
BACKEND_DIR = APP_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.db_service import init_db_pool, fetch
from services.google_business_service import get_google_business_service
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    finish_worker_run,
)

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="google_business_sync")


async def sync_pending_locations(limit: int = 50) -> Dict[str, Any]:
    """
    Sync locations that are pending sync.
    """
    sql = """
        SELECT id, location_id, business_account_id, google_business_id
        FROM google_business_sync
        WHERE sync_status IN ('pending', 'synced')
            AND (last_synced_at IS NULL OR last_synced_at < NOW() - INTERVAL '24 hours')
        ORDER BY last_synced_at NULLS FIRST
        LIMIT $1
    """
    
    sync_records = await fetch(sql, limit)
    
    google_service = get_google_business_service()
    synced = 0
    failed = 0
    errors = []
    
    for record in sync_records:
        location_id = record["location_id"]
        try:
            await google_service.sync_location_data(location_id=location_id)
            synced += 1
            logger.info("location_synced", location_id=location_id)
        except Exception as e:
            failed += 1
            error_msg = str(e)
            errors.append(error_msg)
            logger.error(
                "location_sync_failed",
                location_id=location_id,
                error=error_msg,
                exc_info=True,
            )
    
    return {
        "synced": synced,
        "failed": failed,
        "total": len(sync_records),
        "errors": errors[:5],
    }


@with_run_id
async def run(limit: int = 50, dry_run: bool = False) -> None:
    """
    Main worker function.
    """
    await init_db_pool()
    
    run_id = await start_worker_run(
        worker_name="google_business_sync",
        dry_run=dry_run,
    )
    
    await mark_worker_run_running(run_id)
    
    try:
        if dry_run:
            logger.info("dry_run_mode", message="Dry run mode - no changes will be made")
        
        result = await sync_pending_locations(limit=limit)
        
        logger.info(
            "sync_complete",
            synced=result["synced"],
            failed=result["failed"],
            total=result["total"],
        )
        
        await finish_worker_run(
            run_id=run_id,
            status="completed",
            counters={
                "synced": result["synced"],
                "failed": result["failed"],
            },
        )
        
    except Exception as e:
        logger.error("worker_failed", error=str(e), exc_info=True)
        await finish_worker_run(
            run_id=run_id,
            status="failed",
            error_message=str(e),
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Business Sync Worker")
    parser.add_argument("--limit", type=int, default=50, help="Maximum locations to sync")
    parser.add_argument("--dry-run", type=int, default=0, help="Dry run mode (1=yes, 0=no)")
    
    args = parser.parse_args()
    
    asyncio.run(run(limit=args.limit, dry_run=bool(args.dry_run)))


if __name__ == "__main__":
    main()

















