"""
Worker Orchestrator Service

Orchestrates background worker execution when triggered via the admin API.
Maps bot names to worker functions, constructs appropriate arguments, and handles
execution with proper error handling and status updates.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from services.worker_runs_service import (
    mark_worker_run_running,
    finish_worker_run,
    update_worker_run_progress,
)

logger = get_logger()


@contextmanager
def mock_sys_argv(args: list[str]):
    """Temporarily replace sys.argv with mock arguments."""
    original_argv = sys.argv.copy()
    try:
        sys.argv = args
        yield
    finally:
        sys.argv = original_argv


async def start_worker_run(
    run_id: UUID,
    bot: str,
    city: Optional[str] = None,
    category: Optional[str] = None,
    max_jobs: Optional[int] = None,
) -> None:
    """
    Start a worker run in the background.
    
    Maps bot names to worker functions, constructs appropriate arguments,
    and handles execution with error handling.
    
    Args:
        run_id: UUID of the worker_runs record
        bot: Bot name (discovery, discovery_train, classify, verify, monitor)
        city: Optional city filter
        category: Optional category filter
        max_jobs: Optional max jobs parameter (for discovery_train)
    """
    try:
        # Mark as running (workers will also call this, but this ensures it happens)
        await mark_worker_run_running(run_id)
        
        # Dispatch to appropriate worker
        if bot == "discovery":
            await _run_discovery_bot(run_id, city, category)
        elif bot == "discovery_train":
            await _run_discovery_train(run_id, max_jobs)
        elif bot == "classify":
            await _run_classify_bot(run_id, city, category)
        elif bot == "verify":
            await _run_verify_locations(run_id, city, category)
        elif bot == "monitor":
            await _run_monitor_bot(run_id)
        elif bot == "verification_consumer":
            await _run_verification_consumer(run_id, city)
        elif bot == "news_ingest":
            await _run_news_ingest(run_id)
        elif bot == "news_classify":
            await _run_news_classify(run_id)
        else:
            raise ValueError(f"Unknown bot: {bot}")
            
    except Exception as exc:
        # Worker failed - update status to failed
        logger.error(
            "worker_run_failed",
            run_id=str(run_id),
            bot=bot,
            error=str(exc),
            exc_info=True,
        )
        try:
            await finish_worker_run(
                run_id=run_id,
                status="failed",
                progress=0,
                counters=None,
                error_message=str(exc),
            )
        except Exception as update_error:
            logger.error(
                "failed_to_update_worker_run_on_error",
                run_id=str(run_id),
                error=str(update_error),
            )


async def _run_discovery_bot(
    run_id: UUID,
    city: Optional[str],
    category: Optional[str],
) -> None:
    """Run discovery_bot with constructed arguments."""
    from app.workers.discovery_bot import main_async
    
    # Build sys.argv mock
    argv = ["discovery_bot"]
    
    if city:
        argv.extend(["--city", city])
    else:
        argv.extend(["--city", "rotterdam"])  # Default
    
    if category:
        argv.extend(["--categories", category])
    
    argv.extend(["--worker-run-id", str(run_id)])
    argv.extend(["--max-total-inserts", "0"])  # No limit by default
    
    logger.info(
        "starting_discovery_bot",
        run_id=str(run_id),
        city=city or "rotterdam",
        category=category,
    )
    
    with mock_sys_argv(argv):
        await main_async()


async def _run_discovery_train(
    run_id: UUID,
    max_jobs: Optional[int] = None,
) -> None:
    """Run discovery_train_bot with constructed arguments."""
    from app.workers.discovery_train_bot import main_async
    
    # Build sys.argv mock
    argv = ["discovery_train_bot"]
    argv.extend(["--worker-run-id", str(run_id)])
    
    # Default to 1 job if not specified (cron-friendly)
    max_jobs_value = max_jobs if max_jobs is not None else 1
    argv.extend(["--max-jobs", str(max_jobs_value)])
    
    logger.info(
        "starting_discovery_train",
        run_id=str(run_id),
        max_jobs=max_jobs_value,
    )
    
    with mock_sys_argv(argv):
        await main_async()


async def _run_classify_bot(
    run_id: UUID,
    city: Optional[str],
    category: Optional[str],
) -> None:
    """Run classify_bot with constructed arguments."""
    from app.workers.classify_bot import main_async
    
    # Build sys.argv mock
    argv = ["classify_bot"]
    
    argv.extend(["--limit", "50"])  # Default limit
    
    default_conf = float(os.getenv("CLASSIFY_MIN_CONF", "0.80"))
    argv.extend(["--min-confidence", str(default_conf)])
    
    if city:
        argv.extend(["--city", city])
    
    argv.extend(["--worker-run-id", str(run_id)])
    # dry-run is False by default (action="store_true" means it's only set if present)
    
    logger.info(
        "starting_classify_bot",
        run_id=str(run_id),
        city=city,
        category=category,
    )
    
    with mock_sys_argv(argv):
        await main_async()


async def _run_verify_locations(
    run_id: UUID,
    city: Optional[str],
    category: Optional[str],
) -> None:
    """Run verify_locations with constructed arguments."""
    from app.workers.verify_locations import main_async
    
    # Build sys.argv mock
    argv = ["verify_locations"]
    
    if city:
        argv.extend(["--city", city])
    
    argv.extend(["--limit", "200"])  # Default limit
    argv.extend(["--min-confidence", "0.8"])  # Default
    argv.extend(["--dry-run", "0"])  # Real execution
    argv.extend(["--worker-run-id", str(run_id)])
    
    logger.info(
        "starting_verify_locations",
        run_id=str(run_id),
        city=city,
        category=category,
    )
    
    with mock_sys_argv(argv):
        await main_async()


async def _run_monitor_bot(run_id: UUID) -> None:
    """Run monitor_bot with direct function call (accepts params directly)."""
    from app.workers.monitor_bot import main_async
    
    logger.info("starting_monitor_bot", run_id=str(run_id))
    
    # monitor_bot accepts parameters directly
    await main_async(limit=None, dry_run=False, worker_run_id=run_id)


async def _run_verification_consumer(run_id: UUID, city: Optional[str]) -> None:
    """
    Run verification_consumer with direct call. This worker accepts keyword args.
    """
    from app.workers.verification_consumer import main_async as verification_consumer_main

    logger.info(
        "starting_verification_consumer",
        run_id=str(run_id),
        city=city,
    )

    await verification_consumer_main(
        limit=100,            # default batch size
        city=city,
        dry_run=False,        # real execution
        max_attempts=3,       # default attempts
        worker_run_id=run_id,
    )


async def _run_news_ingest(run_id: UUID) -> None:
    """Run news_ingest_bot via CLI-compatible entrypoint."""
    from app.workers.news_ingest_bot import main_async

    logger.info("starting_news_ingest_bot", run_id=str(run_id))

    argv = ["news_ingest_bot", "--worker-run-id", str(run_id)]
    with mock_sys_argv(argv):
        await main_async()


async def _run_news_classify(run_id: UUID) -> None:
    """Run news_classify_bot via CLI-compatible entrypoint."""
    from app.workers.news_classify_bot import main_async

    logger.info("starting_news_classify_bot", run_id=str(run_id))

    argv = ["news_classify_bot", "--worker-run-id", str(run_id)]
    with mock_sys_argv(argv):
        await main_async()
