from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple
from uuid import UUID

# ---------------------------------------------------------------------------
# Pathing and logging (mirror existing workers)
# ---------------------------------------------------------------------------
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="verification_consumer")

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
from services.db_service import (
    init_db_pool,
    run_in_transaction,
    fetch_with_conn,
    fetchrow_with_conn,
    execute_with_conn,
    update_location_classification,
)

# ---------------------------------------------------------------------------
# Worker run tracking
# ---------------------------------------------------------------------------
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    update_worker_run_progress,
    finish_worker_run,
)

# ---------------------------------------------------------------------------
# Freshness policy (reuse MonitorBot logic)
# ---------------------------------------------------------------------------
from app.workers.monitor_bot import MonitorSettings, compute_next_check_at

# ---------------------------------------------------------------------------
# Verification services (reuse verify_locations pipeline pieces)
# ---------------------------------------------------------------------------
from services.classify_service import ClassifyService, map_llm_category_to_enum
from services.ai_validation import validate_classification_payload
from services.audit_service import audit_service
from app.models.ai import Category


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------
_LOCATION_SELECT_COLS = """
    id, name, address, category, state, confidence_score, user_ratings_total,
    business_status, is_probable_not_open_yet, last_verified_at, next_check_at
"""


async def _claim_verification_tasks_txn(
    conn,
    *,
    limit: int,
    max_attempts: int,
) -> List[Mapping[str, Any]]:
    """
    Claim up to 'limit' pending VERIFICATION tasks with attempts < max_attempts.
    Uses FOR UPDATE SKIP LOCKED to avoid contention and marks them PROCESSING.
    Returns claimed task rows (id, location_id, attempts).
    """
    sql = """
        WITH task_candidates AS (
            SELECT id, location_id
            FROM tasks
            WHERE task_type = 'VERIFICATION'
              AND UPPER(status) = 'PENDING'
              AND (attempts IS NULL OR attempts < $2)
            ORDER BY created_at ASC
            LIMIT $1
            FOR UPDATE SKIP LOCKED
        )
        UPDATE tasks AS t
        SET
            status = 'PROCESSING',
            attempts = COALESCE(t.attempts, 0) + 1,
            last_attempted_at = NOW()
        FROM task_candidates c
        WHERE t.id = c.id
        RETURNING t.id, t.location_id, t.attempts
    """
    rows = await fetch_with_conn(conn, sql, int(limit), int(max_attempts))
    return [dict(r) for r in rows or []]


async def claim_verification_tasks(
    limit: int,
    max_attempts: int,
) -> List[Mapping[str, Any]]:
    """
    Wrapper to run the claim logic inside a single transaction.
    """
    async with run_in_transaction() as conn:
        return await _claim_verification_tasks_txn(
            conn, limit=int(limit), max_attempts=int(max_attempts)
        )


async def _fetch_location_by_id_txn(conn, location_id: int) -> Optional[Dict[str, Any]]:
    row = await fetchrow_with_conn(
        conn,
        f"SELECT {_LOCATION_SELECT_COLS} FROM locations WHERE id = $1",
        int(location_id),
    )
    return dict(row) if row else None


async def _update_task_complete_txn(conn, task_id: int) -> None:
    await execute_with_conn(
        conn,
        """
        UPDATE tasks
        SET status = 'COMPLETED', is_success = true, error_message = NULL
        WHERE id = $1
        """,
        int(task_id),
    )


async def _update_task_fail_txn(conn, task_id: int, message: str) -> None:
    await execute_with_conn(
        conn,
        """
        UPDATE tasks
        SET status = 'FAILED', is_success = false, error_message = $2
        WHERE id = $1
        """,
        int(task_id),
        message[:500],
    )


async def _reset_task_to_pending_txn(conn, task_id: int) -> None:
    await execute_with_conn(
        conn,
        """
        UPDATE tasks
        SET status = 'PENDING'
        WHERE id = $1
        """,
        int(task_id),
    )


async def _set_next_check_at_txn(conn, location_id: int, next_check_at: datetime) -> None:
    await execute_with_conn(
        conn,
        """
        UPDATE locations
        SET next_check_at = $1
        WHERE id = $2
        """,
        next_check_at,
        int(location_id),
    )


async def run_verification_consumer(
    *,
    limit: int,
    max_attempts: int,
    dry_run: bool,
    worker_run_id: Optional[UUID],
    city: Optional[str],
) -> Dict[str, Any]:
    """
    Core processing loop for the verification consumer worker.
    """
    await init_db_pool()

    counters: Dict[str, Any] = {
        "claimed": 0,
        "processed": 0,
        "completed": 0,
        "failed": 0,
        "skipped_no_location": 0,
        "closed_detected": 0,
        "max_attempts_exceeded": 0,
        "limit": int(limit),
        "dry_run": bool(dry_run),
    }

    # Claim tasks
    claimed = await claim_verification_tasks(limit=int(limit), max_attempts=int(max_attempts))
    total_claimed = len(claimed)
    counters["claimed"] = total_claimed

    if total_claimed == 0:
        # Nothing to do
        if worker_run_id:
            await update_worker_run_progress(worker_run_id, 100)
        return counters

    monitor_cfg = MonitorSettings()
    classify_service = ClassifyService()
    last_progress = -1

    for idx, task in enumerate(claimed, start=1):
        task_id = int(task["id"])
        attempts_after_increment = int(task.get("attempts") or 0)
        location_id = task.get("location_id")

        if location_id is None:
            counters["skipped_no_location"] += 1
            counters["failed"] += 1
            logger.warning("task_missing_location_id", task_id=task_id)
            if not dry_run:
                async with run_in_transaction() as conn:
                    await _update_task_fail_txn(conn, task_id, "Missing location_id")
            # progress update
            counters["processed"] += 1
            if worker_run_id:
                progress = min(99, max(0, int((counters["processed"] * 100) / total_claimed)))
                if progress != last_progress:
                    await update_worker_run_progress(worker_run_id, progress)
                    last_progress = progress
            continue

        # Fetch location row
        location_row: Optional[Dict[str, Any]] = None
        async with run_in_transaction(readonly=True) as conn:
            location_row = await _fetch_location_by_id_txn(conn, int(location_id))

        if not location_row:
            counters["failed"] += 1
            logger.warning("location_not_found_for_task", task_id=task_id, location_id=location_id)
            if not dry_run:
                async with run_in_transaction() as conn:
                    await _update_task_fail_txn(conn, task_id, "Location not found")
            counters["processed"] += 1
            if worker_run_id:
                progress = min(99, max(0, int((counters["processed"] * 100) / total_claimed)))
                if progress != last_progress:
                    await update_worker_run_progress(worker_run_id, progress)
                    last_progress = progress
            continue

        # Verification / reclassification pipeline (reuse verify_locations approach)
        # Note: In dry_run mode, do not perform DB writes; only log intended actions.
        try:
            name = location_row.get("name")
            address = location_row.get("address")
            category = location_row.get("category")

            classification_result, meta = classify_service.classify(
                name=name,
                address=address,
                typ=category,
                location_id=int(location_id),
            )

            validated = validate_classification_payload(classification_result.model_dump())
            action = validated.action.value
            new_category = validated.category.value if validated.category else None
            new_confidence = float(validated.confidence_score)
            reason = validated.reason

            logger.info(
                "classification_decision",
                task_id=task_id,
                location_id=int(location_id),
                action=action,
                category=new_category,
                confidence=new_confidence,
            )

            if not dry_run:
                # Normalize category into allowed enum prior to persisting (only if category is provided)
                normalized_category_value = None
                if new_category is not None:
                    enum_category = map_llm_category_to_enum(new_category)
                    normalized_category_value = enum_category.value

                # Apply classification to the location row (updates state/confidence/last_verified_at)
                await update_location_classification(
                    id=int(location_id),
                    action=action,
                    category=normalized_category_value,
                    confidence_score=new_confidence,
                    reason=reason or "verification_consumer: applied",
                )

                # Audit log
                await audit_service.log(
                    action_type="verification_consumer.classified",
                    actor="verification_consumer",
                    location_id=int(location_id),
                    before=None,
                    after={
                        "action": action,
                        "category": normalized_category_value,
                        "confidence_score": new_confidence,
                    },
                    is_success=True,
                    meta={"task_id": int(task_id)},
                )

                # Fetch updated row for freshness computation
                async with run_in_transaction(readonly=True) as conn:
                    updated_row = await _fetch_location_by_id_txn(conn, int(location_id))
                if updated_row:
                    nca = compute_next_check_at(updated_row, monitor_cfg)
                    async with run_in_transaction() as conn:
                        await _set_next_check_at_txn(conn, int(location_id), nca)

                # Update task outcome
                async with run_in_transaction() as conn:
                    await _update_task_complete_txn(conn, int(task_id))

            # Counters
            counters["completed"] += 1
            counters["processed"] += 1
            # Closed detection (terminal states) based on validated action mapping
            # We rely on update_location_classification rules (ignore -> RETIRED)
            if action == "ignore":
                counters["closed_detected"] += 1

        except Exception as exc:
            logger.exception(
                "task_processing_failed",
                task_id=int(task_id),
                location_id=int(location_id),
                attempts=attempts_after_increment,
            )

            counters["failed"] += 1
            counters["processed"] += 1

            if not dry_run:
                async with run_in_transaction() as conn:
                    if attempts_after_increment >= int(max_attempts):
                        counters["max_attempts_exceeded"] += 1
                        await _update_task_fail_txn(conn, int(task_id), f"{type(exc).__name__}: {str(exc)[:300]}")
                    else:
                        # Reset to PENDING for retry (documented choice for this story)
                        await _reset_task_to_pending_txn(conn, int(task_id))

        # Progress update
        if worker_run_id:
            progress = min(99, max(0, int((counters["processed"] * 100) / total_claimed)))
            if progress != last_progress:
                await update_worker_run_progress(worker_run_id, progress)
                last_progress = progress

    # Final progress to 100 will be handled by the caller via finish_worker_run
    return counters


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verification Consumer Worker")
    p.add_argument("--limit", type=int, default=100, help="Max tasks to process")
    p.add_argument("--city", type=str, default=None, help="Optional city label (stored on worker run only)")
    p.add_argument("--dry-run", action="store_true", help="Do not write to DB; log actions only")
    p.add_argument("--max-attempts", type=int, default=3, help="Max attempts per task before failing")
    p.add_argument("--worker-run-id", type=str, default=None, help="Existing worker_run UUID to reuse")
    return p.parse_args()


async def main_async(
    *,
    limit: Optional[int] = None,
    city: Optional[str] = None,
    dry_run: bool = False,
    max_attempts: int = 3,
    worker_run_id: Optional[UUID] = None,
) -> None:
    """
    Main entrypoint (can be used by orchestrator).
    """
    await init_db_pool()

    # Ensure worker_run exists (create if not provided)
    created_run = False
    run_id: Optional[UUID] = worker_run_id
    if run_id is None:
        run_id = await start_worker_run(bot="verification_consumer", city=city, category=None)
        created_run = True

    # Mark running
    await mark_worker_run_running(run_id)

    counters: Dict[str, Any] = {}
    status = "finished"
    error_message: Optional[str] = None

    try:
        with with_run_id(str(run_id)):
            logger.info("worker_started", city=city, limit=limit, dry_run=dry_run, max_attempts=max_attempts)
            counters = await run_verification_consumer(
                limit=int(limit or 100),
                max_attempts=int(max_attempts),
                dry_run=bool(dry_run),
                worker_run_id=run_id,
                city=city,
            )
    except Exception as exc:
        status = "failed"
        error_message = f"{type(exc).__name__}: {str(exc)[:300]}"
        logger.exception("worker_crashed", error=error_message)
    finally:
        # Ensure a counters object exists for finish
        if not counters:
            counters = {"claimed": 0, "processed": 0, "completed": 0, "failed": 0, "dry_run": bool(dry_run)}
        await finish_worker_run(
            run_id=run_id,
            status=status,
            progress=100,
            counters=counters,
            error_message=error_message,
        )
        logger.info("worker_finished", status=status, counters=counters)


def main() -> None:
    args = _parse_args()
    # Accept CLI args and delegate to async entrypoint
    asyncio.run(
        main_async(
            limit=args.limit,
            city=args.city,
            dry_run=bool(args.dry_run),
            max_attempts=int(args.max_attempts),
            worker_run_id=UUID(args.worker_run_id) if args.worker_run_id else None,
        )
    )


if __name__ == "__main__":
    main()


