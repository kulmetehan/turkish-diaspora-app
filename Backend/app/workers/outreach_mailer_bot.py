# Backend/app/workers/outreach_mailer_bot.py
"""
Outreach Mailer Bot — Automatisch verzenden van queued outreach emails.

Worker die:
- Queued emails ophaalt uit outreach_emails tabel
- Rate limiting respecteert
- Emails verzendt via outreach_mailer_service
- Logging en error handling
- Graceful shutdown support

Pad: Backend/app/workers/outreach_mailer_bot.py
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
logger = logger.bind(worker="outreach_mailer_bot")

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
# Outreach mailer service
# ---------------------------------------------------------------------------
from services.outreach_mailer_service import send_queued_emails

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


async def run_outreach_mailer_loop(
    batch_size: int = 50,
    sleep_interval: int = 60,
    max_iterations: Optional[int] = None,
) -> None:
    """
    Main loop for outreach mailer bot.
    
    Args:
        batch_size: Maximum number of emails to process per batch
        sleep_interval: Seconds to sleep between batches
        max_iterations: Maximum number of iterations (None = infinite)
    """
    global _shutdown_requested
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    
    # Initialize database pool
    await init_db_pool()
    logger.info("outreach_mailer_bot_started", batch_size=batch_size, sleep_interval=sleep_interval)
    
    iteration = 0
    
    try:
        while not _shutdown_requested:
            if max_iterations and iteration >= max_iterations:
                logger.info("outreach_mailer_bot_max_iterations_reached", iterations=iteration)
                break
            
            iteration += 1
            logger.info("outreach_mailer_bot_iteration_start", iteration=iteration)
            
            try:
                # Send queued emails
                result = await send_queued_emails(limit=batch_size)
                
                sent = result.get("sent", 0)
                failed = result.get("failed", 0)
                errors = result.get("errors", [])
                
                logger.info(
                    "outreach_mailer_bot_iteration_complete",
                    iteration=iteration,
                    sent=sent,
                    failed=failed,
                    error_count=len(errors),
                )
                
                # Log errors if any
                if errors:
                    for error in errors[:5]:  # Log first 5 errors
                        logger.warning("outreach_mailer_bot_error", error=error)
                
                # If no emails were sent and no errors, we're done for now
                if sent == 0 and failed == 0:
                    logger.debug("outreach_mailer_bot_no_emails_to_send")
                
            except Exception as e:
                logger.error(
                    "outreach_mailer_bot_iteration_error",
                    iteration=iteration,
                    error=str(e),
                    exc_info=True,
                )
                # Continue to next iteration even on error
            
            # Sleep between iterations (unless shutdown requested)
            if not _shutdown_requested:
                logger.debug("outreach_mailer_bot_sleeping", seconds=sleep_interval)
                await asyncio.sleep(sleep_interval)
    
    except KeyboardInterrupt:
        logger.info("outreach_mailer_bot_keyboard_interrupt")
    except Exception as e:
        logger.error(
            "outreach_mailer_bot_fatal_error",
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        logger.info("outreach_mailer_bot_shutdown")


async def run_outreach_mailer_with_tracking(
    batch_size: int = 50,
    sleep_interval: int = 60,
    max_iterations: Optional[int] = None,
) -> None:
    """
    Run outreach mailer bot with worker run tracking.
    
    Args:
        batch_size: Maximum number of emails to process per batch
        sleep_interval: Seconds to sleep between batches
        max_iterations: Maximum number of iterations (None = infinite)
    """
    run_id = None
    
    try:
        # Start worker run tracking
        run_id = await start_worker_run(
            worker_name="outreach_mailer_bot",
            config={
                "batch_size": batch_size,
                "sleep_interval": sleep_interval,
                "max_iterations": max_iterations,
            },
        )
        
        await mark_worker_run_running(run_id)
        
        # Run main loop
        await run_outreach_mailer_loop(
            batch_size=batch_size,
            sleep_interval=sleep_interval,
            max_iterations=max_iterations,
        )
        
        # Mark as completed
        if run_id:
            await finish_worker_run(run_id, success=True)
    
    except Exception as e:
        logger.error(
            "outreach_mailer_bot_run_failed",
            run_id=run_id,
            error=str(e),
            exc_info=True,
        )
        if run_id:
            await finish_worker_run(run_id, success=False, error_message=str(e))
        raise


def main():
    """CLI entry point for outreach mailer bot."""
    parser = argparse.ArgumentParser(
        description="Outreach Mailer Bot - Automatisch verzenden van queued outreach emails"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Maximum aantal emails per batch (default: 50)",
    )
    parser.add_argument(
        "--sleep-interval",
        type=int,
        default=60,
        help="Seconden tussen batches (default: 60)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum aantal iteraties (default: infinite)",
    )
    parser.add_argument(
        "--no-tracking",
        action="store_true",
        help="Disable worker run tracking",
    )
    
    args = parser.parse_args()
    
    # Run with or without tracking
    if args.no_tracking:
        asyncio.run(
            run_outreach_mailer_loop(
                batch_size=args.batch_size,
                sleep_interval=args.sleep_interval,
                max_iterations=args.max_iterations,
            )
        )
    else:
        asyncio.run(
            run_outreach_mailer_with_tracking(
                batch_size=args.batch_size,
                sleep_interval=args.sleep_interval,
                max_iterations=args.max_iterations,
            )
        )


if __name__ == "__main__":
    main()

