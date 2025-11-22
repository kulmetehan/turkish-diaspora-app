# Backend/app/workers/discovery_train_bot.py
"""
Discovery Train Bot - Sequential discovery orchestration worker.

This worker processes discovery jobs from the discovery_jobs queue one by one,
ensuring sequential execution to avoid hammering OSM Overpass API.

Usage:
    python -m app.workers.discovery_train_bot [--max-jobs N]
    
    If --max-jobs is not provided, processes 1 job and exits (cron-friendly).
    If --max-jobs is provided, processes up to N jobs sequentially.

Scheduling:
    - Render cron: Run every 30 minutes: `python -m app.workers.discovery_train_bot`
    - GitHub Actions: Add to workflow with schedule or manual trigger
    - Manual: Run with --max-jobs to process multiple jobs in one invocation
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Optional
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
from services.discovery_jobs_service import (
    get_next_pending_job,
    mark_job_running,
    mark_job_finished,
    mark_job_failed,
    DiscoveryJob,
)
from app.workers.discovery_bot import run_discovery_job

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="discovery_train_bot")


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Discovery Train Bot — Sequential discovery orchestration from job queue"
    )
    ap.add_argument(
        "--max-jobs",
        type=int,
        default=1,
        help="Maximum number of jobs to process (default: 1, processes 1 job and exits)"
    )
    ap.add_argument(
        "--worker-run-id",
        type=_parse_worker_run_id,
        help="UUID of worker_runs record for progress tracking"
    )
    return ap.parse_args()


async def process_job(job: DiscoveryJob, worker_run_id: Optional[UUID] = None) -> dict:
    """
    Process a single discovery job.
    
    Returns:
        dict with job_id, success (bool), counters (if successful), error (if failed)
    """
    job_id = job.id
    logger.info(
        "train_job_started",
        job_id=str(job_id),
        city=job.city_key,
        district=job.district_key,
        category=job.category,
    )
    print(f"\n[DiscoveryTrain] Processing job {job_id}: city={job.city_key}, district={job.district_key or 'none'}, category={job.category}")
    
    try:
        # Run discovery for this job
        counters = await run_discovery_job(
            city_key=job.city_key,
            district_key=job.district_key,
            category=job.category,
            worker_run_id=worker_run_id,
        )
        
        # Mark job as finished
        await mark_job_finished(job_id, counters)
        
        logger.info(
            "train_job_finished",
            job_id=str(job_id),
            counters=counters,
        )
        print(f"[DiscoveryTrain] Job {job_id} completed. Counters: {counters}")
        
        return {
            "job_id": str(job_id),
            "success": True,
            "counters": counters,
            "error": None,
        }
    except Exception as e:
        error_msg = str(e)
        await mark_job_failed(job_id, error_msg)
        
        logger.error(
            "train_job_failed",
            job_id=str(job_id),
            error=error_msg,
            exc_info=e,
        )
        print(f"[DiscoveryTrain] Job {job_id} failed: {error_msg}")
        
        return {
            "job_id": str(job_id),
            "success": False,
            "counters": None,
            "error": error_msg,
        }


async def main_async() -> None:
    t0 = time.perf_counter()
    
    with with_run_id() as rid:
        logger.info("worker_started")
        args = parse_args()
        worker_run_id: Optional[UUID] = getattr(args, "worker_run_id", None)
        max_jobs = int(args.max_jobs) if args.max_jobs > 0 else 1
        
        await init_db_pool()
        
        # Auto-create worker_run if not provided
        if not worker_run_id:
            from services.worker_runs_service import start_worker_run
            worker_run_id = await start_worker_run(bot="discovery_train_bot", city=None, category=None)
        
        if worker_run_id:
            from services.worker_runs_service import mark_worker_run_running, finish_worker_run
            await mark_worker_run_running(worker_run_id)
        
        jobs_processed = 0
        jobs_succeeded = 0
        jobs_failed = 0
        
        print(f"\n[DiscoveryTrain] Starting train run (max_jobs={max_jobs})")
        
        try:
            while jobs_processed < max_jobs:
                # Fetch next pending job
                job = await get_next_pending_job()
                
                if not job:
                    print(f"[DiscoveryTrain] No pending jobs found. Exiting.")
                    logger.info("train_no_pending_jobs")
                    break
                
                # Mark job as running (already done by get_next_pending_job with FOR UPDATE SKIP LOCKED,
                # but we mark it explicitly for clarity)
                await mark_job_running(job.id)
                
                # Process the job
                result = await process_job(job, worker_run_id)
                jobs_processed += 1
                
                if result["success"]:
                    jobs_succeeded += 1
                else:
                    jobs_failed += 1
                
                # Small delay between jobs to respect rate limits
                if jobs_processed < max_jobs:
                    await asyncio.sleep(2.0)  # 2 second delay between jobs
        
        except Exception as e:
            logger.error("train_worker_failed", error=str(e), exc_info=e)
            if worker_run_id:
                from services.worker_runs_service import finish_worker_run
                await finish_worker_run(worker_run_id, "failed", 0, None, str(e))
            raise
        
        # Finish worker run
        if worker_run_id:
            from services.worker_runs_service import finish_worker_run
            counters = {
                "jobs_processed": jobs_processed,
                "jobs_succeeded": jobs_succeeded,
                "jobs_failed": jobs_failed,
            }
            await finish_worker_run(worker_run_id, "finished", 100, counters, None)
        
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "worker_finished",
            duration_ms=duration_ms,
            jobs_processed=jobs_processed,
            jobs_succeeded=jobs_succeeded,
            jobs_failed=jobs_failed,
        )
        print(f"\n[DiscoveryTrain] Train run completed: processed={jobs_processed}, succeeded={jobs_succeeded}, failed={jobs_failed}")


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[DiscoveryTrain] Interrupted by user.")
    except Exception as e:
        print(f"\n[DiscoveryTrain] ERROR: {e}")
        raise


if __name__ == "__main__":
    main()




