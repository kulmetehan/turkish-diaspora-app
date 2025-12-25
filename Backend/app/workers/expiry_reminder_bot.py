# Backend/app/workers/expiry_reminder_bot.py
"""
Expiry Reminder Bot — Automatisch verzenden van expiry reminder emails.

Worker die:
- Expiring claims ophaalt (7 dagen voor expiry)
- Reminder emails verzendt via expiry_reminder_service
- Reminders markeert als verzonden
- Logging en error handling
- Graceful shutdown support

Pad: Backend/app/workers/expiry_reminder_bot.py
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
logger = logger.bind(worker="expiry_reminder_bot")

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
# Expiry reminder service
# ---------------------------------------------------------------------------
from services.expiry_reminder_service import process_expiring_claims

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


async def run_expiry_reminder_once(
    days_before_expiry: int = 7,
    batch_size: int = 50,
    language: str = "nl",
) -> dict:
    """
    Run expiry reminder bot once (single execution).
    
    Args:
        days_before_expiry: Number of days before expiry to send reminder
        batch_size: Maximum number of reminders to send in one batch
        language: Default language for emails (nl, tr, en)
        
    Returns:
        Dictionary with processing results
    """
    # Process expiring claims
    result = await process_expiring_claims(
        days_before_expiry=days_before_expiry,
        batch_size=batch_size,
        language=language,
    )
    
    return result


async def run_expiry_reminder_loop(
    days_before_expiry: int = 7,
    batch_size: int = 50,
    sleep_interval: int = 3600,  # 1 hour default
    max_iterations: Optional[int] = None,
    language: str = "nl",
) -> None:
    """
    Main loop for expiry reminder bot.
    
    Args:
        days_before_expiry: Number of days before expiry to send reminder
        batch_size: Maximum number of reminders to send per batch
        sleep_interval: Seconds to sleep between batches
        max_iterations: Maximum number of iterations (None = infinite)
        language: Default language for emails (nl, tr, en)
    """
    global _shutdown_requested
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    
    # Initialize database pool
    await init_db_pool()
    logger.info(
        "expiry_reminder_bot_started",
        days_before_expiry=days_before_expiry,
        batch_size=batch_size,
        sleep_interval=sleep_interval,
    )
    
    iteration = 0
    
    try:
        while not _shutdown_requested:
            if max_iterations and iteration >= max_iterations:
                logger.info("expiry_reminder_bot_max_iterations_reached", iterations=iteration)
                break
            
            iteration += 1
            logger.info("expiry_reminder_bot_iteration_start", iteration=iteration)
            
            try:
                # Process expiring claims
                result = await process_expiring_claims(
                    days_before_expiry=days_before_expiry,
                    batch_size=batch_size,
                    language=language,
                )
                
                total_found = result.get("total_found", 0)
                sent = result.get("sent", 0)
                failed = result.get("failed", 0)
                
                logger.info(
                    "expiry_reminder_bot_iteration_complete",
                    iteration=iteration,
                    total_found=total_found,
                    sent=sent,
                    failed=failed,
                )
                
                # If no reminders were sent, we're done for now
                if total_found == 0:
                    logger.debug("expiry_reminder_bot_no_reminders_to_send")
                
            except Exception as e:
                logger.error(
                    "expiry_reminder_bot_iteration_error",
                    iteration=iteration,
                    error=str(e),
                    exc_info=True,
                )
                # Continue to next iteration even on error
            
            # Sleep between iterations (unless shutdown requested)
            if not _shutdown_requested:
                logger.debug("expiry_reminder_bot_sleeping", seconds=sleep_interval)
                await asyncio.sleep(sleep_interval)
    
    except KeyboardInterrupt:
        logger.info("expiry_reminder_bot_keyboard_interrupt")
    except Exception as e:
        logger.error(
            "expiry_reminder_bot_fatal_error",
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        logger.info("expiry_reminder_bot_shutdown")


async def run_expiry_reminder_with_tracking(
    days_before_expiry: int = 7,
    batch_size: int = 50,
    sleep_interval: int = 3600,
    max_iterations: Optional[int] = None,
    language: str = "nl",
) -> None:
    """
    Run expiry reminder bot with worker run tracking.
    
    Args:
        days_before_expiry: Number of days before expiry to send reminder
        batch_size: Maximum number of reminders to send per batch
        sleep_interval: Seconds to sleep between batches
        max_iterations: Maximum number of iterations (None = infinite)
        language: Default language for emails (nl, tr, en)
    """
    run_id = None
    
    try:
        # Start worker run tracking
        run_id = await start_worker_run(
            worker_name="expiry_reminder_bot",
            config={
                "days_before_expiry": days_before_expiry,
                "batch_size": batch_size,
                "sleep_interval": sleep_interval,
                "max_iterations": max_iterations,
                "language": language,
            },
        )
        
        await mark_worker_run_running(run_id)
        
        # Run main loop
        await run_expiry_reminder_loop(
            days_before_expiry=days_before_expiry,
            batch_size=batch_size,
            sleep_interval=sleep_interval,
            max_iterations=max_iterations,
            language=language,
        )
        
        # Mark as completed
        if run_id:
            await finish_worker_run(run_id, success=True)
    
    except Exception as e:
        logger.error(
            "expiry_reminder_bot_run_failed",
            run_id=run_id,
            error=str(e),
            exc_info=True,
        )
        if run_id:
            await finish_worker_run(run_id, success=False, error_message=str(e))
        raise


def main():
    """CLI entry point for expiry reminder bot."""
    parser = argparse.ArgumentParser(
        description="Expiry Reminder Bot - Automatisch verzenden van expiry reminder emails"
    )
    parser.add_argument(
        "--days-before",
        type=int,
        default=7,
        help="Aantal dagen voor expiry om reminder te verzenden (default: 7)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Maximum aantal reminders per batch (default: 50)",
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
        "--language",
        type=str,
        default="nl",
        choices=["nl", "tr", "en"],
        help="Taal voor emails (default: nl)",
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
            result = await run_expiry_reminder_once(
                days_before_expiry=args.days_before,
                batch_size=args.batch_size,
                language=args.language,
            )
            logger.info("expiry_reminder_bot_complete", **result)
        
        asyncio.run(run_once())
    else:
        # Loop execution
        if args.no_tracking:
            asyncio.run(
                run_expiry_reminder_loop(
                    days_before_expiry=args.days_before,
                    batch_size=args.batch_size,
                    sleep_interval=args.sleep_interval,
                    max_iterations=args.max_iterations,
                    language=args.language,
                )
            )
        else:
            asyncio.run(
                run_expiry_reminder_with_tracking(
                    days_before_expiry=args.days_before,
                    batch_size=args.batch_size,
                    sleep_interval=args.sleep_interval,
                    max_iterations=args.max_iterations,
                    language=args.language,
                )
            )


if __name__ == "__main__":
    main()

