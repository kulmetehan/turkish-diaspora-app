# Backend/app/workers/promotion_expiry_worker.py
"""
Promotion Expiry Worker

Marks expired promotions as 'expired' status.
Runs daily via scheduled cron job.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
from typing import Dict, Any, Optional
from uuid import UUID

# Path setup
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent
BACKEND_DIR = APP_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.db_service import init_db_pool
from services.promotion_service import get_promotion_service
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    finish_worker_run,
)

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="promotion_expiry")


async def run_expiry_worker(worker_run_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Main worker function to expire promotions.
    """
    if worker_run_id:
        await mark_worker_run_running(worker_run_id)
    
    await init_db_pool()
    
    promotion_service = get_promotion_service()
    result = await promotion_service.expire_promotions()
    
    logger.info(
        "promotion_expiry_completed",
        location_count=result["location_count"],
        news_count=result["news_count"],
    )
    
    if worker_run_id:
        await finish_worker_run(
            worker_run_id,
            is_success=True,
            result={
                "location_count": result["location_count"],
                "news_count": result["news_count"],
            },
        )
    
    return result


async def main(worker_run_id: Optional[UUID] = None) -> None:
    """
    CLI entry point for promotion expiry worker.
    """
    with with_run_id():
        parser = argparse.ArgumentParser(description="Promotion Expiry Worker")
        parser.add_argument(
            "--worker-run-id",
            type=str,
            help="Optional worker run ID for tracking",
        )
        args = parser.parse_args()
        
        run_id = worker_run_id or (UUID(args.worker_run_id) if args.worker_run_id else None)
        
        if not run_id:
            run_id = await start_worker_run(
                bot="promotion_expiry",
                city=None,
                category=None,
            )
        
        try:
            result = await run_expiry_worker(worker_run_id=run_id)
            logger.info("promotion_expiry_worker_finished", result=result)
        except Exception as exc:
            logger.error(
                "promotion_expiry_worker_failed",
                error=str(exc),
                exc_info=True,
            )
            if run_id:
                await finish_worker_run(
                    run_id,
                    is_success=False,
                    error_message=str(exc),
                )
            raise


if __name__ == "__main__":
    asyncio.run(main())

