# Backend/app/workers/expiry_bot.py
"""
Expiry Bot — Automatisch updaten van expired claims.

Worker die:
- Expired claims ophaalt (free_until < NOW())
- Claim status update naar 'expired'
- Sync met locations.claimed_status
- Logging en error handling
- Graceful shutdown support

Pad: Backend/app/workers/expiry_bot.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import signal
from pathlib import Path
from typing import Optional

# --- Uniform logging ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="expiry_bot")

# ---------------------------------------------------------------------------
# Pathing zodat 'app.*' werkt (CI, GH Actions, lokale run)
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent           # .../Backend/app
BACKEND_DIR = APP_DIR.parent                # .../Backend

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))    # .../Backend

# ---------------------------------------------------------------------------
# DB (asyncpg helpers)
# ---------------------------------------------------------------------------
from services.db_service import init_db_pool

# ---------------------------------------------------------------------------
# Expiry service
# ---------------------------------------------------------------------------
from services.expiry_service import process_expired_claims

# ---------------------------------------------------------------------------
# Worker run tracking
# ---------------------------------------------------------------------------
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    update_worker_run_progress,
    finish_worker_run,
)

# Global flag for graceful shutdown
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    logger.info("shutdown_signal_received", signal=signum)
    _shutdown_requested = True


async def run_expiry_once(batch_size: int = 100) -> dict:
    """
    Run expiry bot once (single execution).
    
    Args:
        batch_size: Maximum number of claims to process in one batch
        
    Returns:
        Dictionary with processing results
    """
    # Process expired claims
    result = await process_expired_claims(batch_size=batch_size)
    
    return result


async def run_expiry_loop(
    batch_size: int = 100,
    sleep_interval: int = 3600,  # 1 hour default
    max_iterations: Optional[int] = None,
) -> None:
    """
    Main loop for expiry bot.
    
    Args:
        batch_size: Maximum number of claims to process per batch
        sleep_interval: Seconds to sleep between batches
        max_iterations: Maximum number of iterations (None = infinite)
    """
    global _shutdown_requested
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    
    # Initialize database pool
    await init_db_pool()
    logger.info(
        "expiry_bot_started",
        batch_size=batch_size,
        sleep_interval=sleep_interval,
    )
    
    iteration = 0
    
    try:
        while not _shutdown_requested:
            if max_iterations and iteration >= max_iterations:
                logger.info("expiry_bot_max_iterations_reached", iterations=iteration)
                break
            
            iteration += 1
            logger.info("expiry_bot_iteration_start", iteration=iteration)
            
            try:
                # Process expired claims
                result = await process_expired_claims(batch_size=batch_size)
                
                total_found = result.get("total_found", 0)
                processed = result.get("processed", 0)
                failed = result.get("failed", 0)
                
                logger.info(
                    "expiry_bot_iteration_complete",
                    iteration=iteration,
                    total_found=total_found,
                    processed=processed,
                    failed=failed,
                )
                
                # If no expired claims were found, we're done for now
                if total_found == 0:
                    logger.debug("expiry_bot_no_expired_claims")
                
            except Exception as e:
                logger.error(
                    "expiry_bot_iteration_error",
                    iteration=iteration,
                    error=str(e),
                    exc_info=True,
                )
                # Continue to next iteration even on error
            
            # Sleep between iterations (unless shutdown requested)
            if not _shutdown_requested:
                logger.debug("expiry_bot_sleeping", seconds=sleep_interval)
                await asyncio.sleep(sleep_interval)
    
    except KeyboardInterrupt:
        logger.info("expiry_bot_keyboard_interrupt")
    except Exception as e:
        logger.error(
            "expiry_bot_fatal_error",
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        logger.info("expiry_bot_shutdown")


async def run_expiry_with_tracking(
    batch_size: int = 100,
    sleep_interval: int = 3600,
    max_iterations: Optional[int] = None,
) -> None:
    """
    Run expiry bot with worker run tracking.
    
    Args:
        batch_size: Maximum number of claims to process per batch
        sleep_interval: Seconds to sleep between batches
        max_iterations: Maximum number of iterations (None = infinite)
    """
    run_id = None
    
    try:
        # Start worker run tracking
        run_id = await start_worker_run(
            worker_name="expiry_bot",
            config={
                "batch_size": batch_size,
                "sleep_interval": sleep_interval,
                "max_iterations": max_iterations,
            },
        )
        
        await mark_worker_run_running(run_id)
        
        # Run main loop
        await run_expiry_loop(
            batch_size=batch_size,
            sleep_interval=sleep_interval,
            max_iterations=max_iterations,
        )
        
        # Mark as completed
        if run_id:
            await finish_worker_run(run_id, success=True)
    
    except Exception as e:
        logger.error(
            "expiry_bot_run_failed",
            run_id=run_id,
            error=str(e),
            exc_info=True,
        )
        if run_id:
            await finish_worker_run(run_id, success=False, error_message=str(e))
        raise


def main():
    """CLI entry point for expiry bot."""
    parser = argparse.ArgumentParser(
        description="Expiry Bot - Automatisch updaten van expired claims"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Maximum aantal claims per batch (default: 100)",
    )
    parser.add_argument(
        "--sleep-interval",
        type=int,
        default=3600,
        help="Seconden tussen batches (default: 3600 = 1 uur)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum aantal iteraties (default: infinite)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (geen loop)",
    )
    parser.add_argument(
        "--no-tracking",
        action="store_true",
        help="Disable worker run tracking",
    )
    
    args = parser.parse_args()
    
    # Run once or in loop
    if args.once:
        # Single execution
        async def run_once():
            await init_db_pool()
            result = await run_expiry_once(batch_size=args.batch_size)
            logger.info("expiry_bot_complete", **result)
        
        asyncio.run(run_once())
    else:
        # Loop execution
        if args.no_tracking:
            asyncio.run(
                run_expiry_loop(
                    batch_size=args.batch_size,
                    sleep_interval=args.sleep_interval,
                    max_iterations=args.max_iterations,
                )
            )
        else:
            asyncio.run(
                run_expiry_with_tracking(
                    batch_size=args.batch_size,
                    sleep_interval=args.sleep_interval,
                    max_iterations=args.max_iterations,
                )
            )


if __name__ == "__main__":
    main()

