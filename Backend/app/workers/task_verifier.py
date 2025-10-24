from __future__ import annotations

import argparse
import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

# --- Uniform logging for workers ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="task_verifier")

# --- Shared async engine and services ---
from services.db_service import async_engine
from services.audit_service import audit_service
from services.classify_service import ClassifyService
from services.ai_validation import validate_classification_payload


# ------------------------------
# SQL helpers
# ------------------------------
SQL_FETCH_TASKS = text(
    """
    SELECT id, location_id
    FROM tasks
    WHERE task_type = 'VERIFICATION'
      AND status = 'PENDING'
    ORDER BY created_at ASC
    LIMIT :lim
    FOR UPDATE SKIP LOCKED
    """
)

SQL_GET_LOCATION = text(
    """
    SELECT id, name, address, category, state
    FROM locations
    WHERE id = :id
    """
)

SQL_UPDATE_LOCATION_VERIFIED = text(
    """
    UPDATE locations
    SET
      state = 'VERIFIED',
      category = :category,
      confidence_score = :confidence_score,
      last_verified_at = :now
    WHERE id = :id
    """
)

SQL_UPDATE_LOCATION_RETIRED = text(
    """
    UPDATE locations
    SET
      state = 'RETIRED',
      last_verified_at = :now
    WHERE id = :id
    """
)

SQL_TASK_DONE = text(
    """
    UPDATE tasks
    SET status = 'DONE', is_success = true, error_message = NULL, updated_at = NOW()
    WHERE id = :id
    """
)

SQL_TASK_FAILED = text(
    """
    UPDATE tasks
    SET status = 'FAILED', is_success = false, error_message = :err, updated_at = NOW()
    WHERE id = :id
    """
)


async def _fetch_pending_verification_tasks(limit: int) -> List[Dict[str, Any]]:
    async with async_engine.begin() as conn:
        rows = (await conn.execute(SQL_FETCH_TASKS, {"lim": limit})).mappings().all()
        return [dict(r) for r in rows]


async def _get_location(location_id: int) -> Optional[Dict[str, Any]]:
    async with async_engine.begin() as conn:
        row = (await conn.execute(SQL_GET_LOCATION, {"id": location_id})).mappings().first()
        return dict(row) if row else None


async def _mark_task_done(task_id: int) -> None:
    async with async_engine.begin() as conn:
        await conn.execute(SQL_TASK_DONE, {"id": task_id})


async def _mark_task_failed(task_id: int, error: str) -> None:
    async with async_engine.begin() as conn:
        await conn.execute(SQL_TASK_FAILED, {"id": task_id, "err": error[:1000]})


async def _update_location_verified(location_id: int, category: str, confidence: float, dry_run: bool) -> None:
    if dry_run:
        return
    now = datetime.now(timezone.utc)
    async with async_engine.begin() as conn:
        await conn.execute(
            SQL_UPDATE_LOCATION_VERIFIED,
            {"id": location_id, "category": category, "confidence_score": confidence, "now": now},
        )


async def _update_location_retired(location_id: int, dry_run: bool) -> None:
    if dry_run:
        return
    now = datetime.now(timezone.utc)
    async with async_engine.begin() as conn:
        await conn.execute(SQL_UPDATE_LOCATION_RETIRED, {"id": location_id, "now": now})


async def process_task(
    *,
    task_id: int,
    location_id: int,
    min_confidence: float,
    dry_run: bool,
    model: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """Process a single VERIFICATION task. Returns (success, error)."""
    # Fetch target location
    loc = await _get_location(location_id)
    if not loc:
        return False, f"location_id {location_id} not found"

    classify = ClassifyService(model=model)
    try:
        parsed, meta = classify.classify(
            name=loc.get("name") or "",
            address=loc.get("address"),
            typ=loc.get("category"),
            location_id=location_id,
        )
        validated = validate_classification_payload(parsed.model_dump())
        action = validated.action.value
        category = (validated.category or "other").lower()
        confidence = float(validated.confidence_score)

        if action == "keep" and confidence >= min_confidence:
            await _update_location_verified(location_id, category, confidence, dry_run)
            if not dry_run:
                await audit_service.log(
                    action_type="task_verifier.recheck_keep",
                    actor="task_verifier",
                    location_id=location_id,
                    before={"state": loc.get("state")},
                    after={"state": "VERIFIED", "category": category, "confidence_score": confidence},
                    is_success=True,
                    meta={"task_id": task_id},
                )
        else:
            # Not Turkish anymore or confidence too low -> retire conservatively
            await _update_location_retired(location_id, dry_run)
            if not dry_run:
                await audit_service.log(
                    action_type="task_verifier.recheck_retire",
                    actor="task_verifier",
                    location_id=location_id,
                    before={"state": loc.get("state")},
                    after={"state": "RETIRED"},
                    is_success=True,
                    meta={
                        "task_id": task_id,
                        "reason": "not_turkish" if action != "keep" else "low_confidence",
                        "confidence": confidence,
                        "threshold": min_confidence,
                    },
                )

        if not dry_run:
            await _mark_task_done(task_id)
        return True, None

    except Exception as e:  # pragma: no cover
        err = str(e)
        logger.error("task_verifier_error", task_id=task_id, location_id=location_id, error=err)
        if not dry_run:
            await _mark_task_failed(task_id, err)
            await audit_service.log(
                action_type="task_verifier.error",
                actor="task_verifier",
                location_id=location_id,
                before=None,
                after=None,
                is_success=False,
                error_message=err,
                meta={"task_id": task_id},
            )
        return False, err


async def run_tasks(limit: int, min_confidence: float, dry_run: bool, model: Optional[str]) -> Dict[str, Any]:
    tasks = await _fetch_pending_verification_tasks(limit)
    if not tasks:
        return {"fetched": 0, "processed": 0, "failed": 0}

    processed = 0
    failed = 0
    for t in tasks:
        ok, _ = await process_task(
            task_id=int(t["id"]),
            location_id=int(t["location_id"]),
            min_confidence=min_confidence,
            dry_run=dry_run,
            model=model,
        )
        if ok:
            processed += 1
        else:
            failed += 1

    return {"fetched": len(tasks), "processed": processed, "failed": failed}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TDA Task Verifier — process VERIFICATION tasks")
    p.add_argument("--limit", type=int, default=500, help="Max tasks per run")
    p.add_argument("--min-confidence", type=float, default=0.80, help="Threshold to keep as VERIFIED")
    p.add_argument("--dry-run", action="store_true", help="No writes")
    p.add_argument("--model", type=str, default=None, help="Override AI model")
    return p.parse_args()


async def main_async() -> None:
    t0 = time.perf_counter()
    with with_run_id() as rid:
        logger.info("worker_started")
        args = parse_args()
        res = await run_tasks(
            limit=int(args.limit),
            min_confidence=float(args.min_confidence),
            dry_run=bool(args.dry_run),
            model=args.model,
        )
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("worker_finished", duration_ms=duration_ms, **res)


if __name__ == "__main__":
    asyncio.run(main_async())


