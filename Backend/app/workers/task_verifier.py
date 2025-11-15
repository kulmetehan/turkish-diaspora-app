from __future__ import annotations

import argparse
import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="task_verifier")

"""
STATE MACHINE (canonical):
- CANDIDATE: raw discovered location, unreviewed.
- PENDING_VERIFICATION: AI thinks it's Turkish (confidence >=0.80) but not yet promoted.
- VERIFIED: approved and visible in the app.
- RETIRED: explicitly considered not relevant / no longer valid.
Only VERIFIED locations are sent to the frontend.
"""

from services.db_service import init_db_pool, fetch, update_location_classification, mark_last_verified
from app.workers.classify_bot import should_force_promote

# Worker run tracking
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    update_worker_run_progress,
    finish_worker_run,
)


async def _fetch_ready_rows(limit: int, auto_promote_conf: float = 0.90) -> list[dict[str, Any]]:
    sql = (
        """
        SELECT id,
               name,
               address,
               lat,
               lng,
               category,
               state,
               confidence_score,
               notes
        FROM locations
        WHERE state IN ('CANDIDATE', 'PENDING_VERIFICATION')
          AND (confidence_score IS NOT NULL AND confidence_score >= $1)
          AND (is_retired = false OR is_retired IS NULL)
          AND last_verified_at IS NULL
        ORDER BY first_seen_at DESC
        LIMIT $2
        """
    )
    rows = await fetch(sql, float(auto_promote_conf), int(limit))
    return [dict(r) for r in rows]


async def run_tasks(limit: int, min_confidence: float, auto_promote_conf: float, dry_run: bool, worker_run_id: Optional[UUID] = None) -> Dict[str, Any]:
    rows = await _fetch_ready_rows(limit, auto_promote_conf)
    if not rows:
        if worker_run_id:
            await finish_worker_run(worker_run_id, "finished", 100, {"fetched": 0, "promoted": 0, "stamped": 0}, None)
        return {"fetched": 0, "promoted": 0, "stamped": 0}

    total = len(rows)
    promoted = 0
    stamped = 0
    
    for idx, r in enumerate(rows, start=1):
        decision = should_force_promote(r, auto_promote_conf)
        if decision and float(decision.get("confidence", 0.0)) >= float(min_confidence):
            if not dry_run:
                await update_location_classification(
                    id=int(r["id"]),
                    action="keep",
                    category=str(decision.get("category") or (r.get("category") or "other")),
                    confidence_score=float(decision.get("confidence", 0.0)),
                    reason=str(decision.get("reason") or "auto by task_verifier heuristic"),
                )
            promoted += 1
        else:
            if not dry_run:
                await mark_last_verified(int(r["id"]), note="checked by task_verifier heuristic, not auto-promoted")
            stamped += 1
        
        # Update progress
        if worker_run_id and total > 0:
            progress = min(99, max(0, int((idx * 100) / total)))
            await update_worker_run_progress(worker_run_id, progress)

    return {"fetched": total, "promoted": promoted, "stamped": stamped}


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TDA Task Verifier — heuristic auto-promotion (no OpenAI)")
    p.add_argument("--limit", type=int, default=500, help="Max rows per run")
    
    # Pre-parse to check if --min-confidence was explicitly provided
    import sys
    explicit_min_conf = '--min-confidence' in sys.argv
    
    # Default: try config, then hard-coded default
    default_min_conf = 0.80
    default_auto_promote = 0.90
    if not explicit_min_conf:
        try:
            import asyncio
            from services.db_service import init_db_pool
            from services.ai_config_service import get_threshold_for_bot, get_auto_promote_conf
            # Use asyncio.run for one-time config fetch
            async def _get_config():
                await init_db_pool()
                min_conf = await get_threshold_for_bot("task_verifier")
                auto_promote = await get_auto_promote_conf()
                return min_conf, auto_promote
            config_min_conf, config_auto_promote = asyncio.run(_get_config())
            if config_min_conf is not None:
                default_min_conf = config_min_conf
            if config_auto_promote is not None:
                default_auto_promote = config_auto_promote
        except Exception as e:
            logger.warning("failed_to_load_config", error=str(e), fallback_to_default=True)
    
    p.add_argument("--min-confidence", type=float, default=default_min_conf, help="Threshold to keep as VERIFIED. Precedence: CLI > config > default")
    p.add_argument("--auto-promote-conf", type=float, default=default_auto_promote, help="Auto-promotion threshold (high confidence + Turkish cues). Precedence: CLI > config > default")
    p.add_argument("--dry-run", action="store_true", help="No writes")
    p.add_argument("--worker-run-id", type=_parse_worker_run_id, help="UUID of worker_runs record for progress tracking")
    return p.parse_args()


async def main_async() -> None:
    t0 = time.perf_counter()
    with with_run_id() as rid:
        logger.info("worker_started")
        args = parse_args()
        worker_run_id: Optional[UUID] = getattr(args, "worker_run_id", None)
        await init_db_pool()
        
        # Auto-create worker_run if not provided
        if not worker_run_id:
            worker_run_id = await start_worker_run(bot="task_verifier", city=None, category=None)
        
        if worker_run_id:
            await mark_worker_run_running(worker_run_id)
        
        try:
            auto_promote_conf = float(getattr(args, "auto_promote_conf", 0.90))
            res = await run_tasks(
                limit=int(args.limit),
                min_confidence=float(args.min_confidence),
                auto_promote_conf=auto_promote_conf,
                dry_run=bool(args.dry_run),
                worker_run_id=worker_run_id,
            )
            
            if worker_run_id:
                counters = {
                    "fetched": res["fetched"],
                    "promoted": res["promoted"],
                    "stamped": res["stamped"],
                }
                await finish_worker_run(worker_run_id, "finished", 100, counters, None)
        except Exception as e:
            if worker_run_id:
                await finish_worker_run(worker_run_id, "failed", 0, None, str(e))
            raise
        
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("worker_finished", duration_ms=duration_ms, **res)


if __name__ == "__main__":
    asyncio.run(main_async())


