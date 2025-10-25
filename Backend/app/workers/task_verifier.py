from __future__ import annotations

import argparse
import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

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


async def _fetch_ready_rows(limit: int) -> list[dict[str, Any]]:
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
          AND (confidence_score IS NOT NULL AND confidence_score >= 0.90)
          AND (is_retired = false OR is_retired IS NULL)
          AND last_verified_at IS NULL
        ORDER BY first_seen_at DESC
        LIMIT $1
        """
    )
    rows = await fetch(sql, int(limit))
    return [dict(r) for r in rows]


async def run_tasks(limit: int, min_confidence: float, dry_run: bool) -> Dict[str, Any]:
    rows = await _fetch_ready_rows(limit)
    if not rows:
        return {"fetched": 0, "promoted": 0, "stamped": 0}

    promoted = 0
    stamped = 0
    for r in rows:
        decision = should_force_promote(r)
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

    return {"fetched": len(rows), "promoted": promoted, "stamped": stamped}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TDA Task Verifier — heuristic auto-promotion (no OpenAI)")
    p.add_argument("--limit", type=int, default=500, help="Max rows per run")
    p.add_argument("--min-confidence", type=float, default=0.80, help="Threshold to keep as VERIFIED")
    p.add_argument("--dry-run", action="store_true", help="No writes")
    return p.parse_args()


async def main_async() -> None:
    t0 = time.perf_counter()
    with with_run_id() as rid:
        logger.info("worker_started")
        args = parse_args()
        await init_db_pool()
        res = await run_tasks(
            limit=int(args.limit),
            min_confidence=float(args.min_confidence),
            dry_run=bool(args.dry_run),
        )
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("worker_finished", duration_ms=duration_ms, **res)


if __name__ == "__main__":
    asyncio.run(main_async())


