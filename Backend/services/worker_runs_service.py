"""
Worker Runs Service - Unified tracking for all worker bots

Provides centralized functions for creating, updating, and querying worker run records.
All workers should use this service instead of duplicating helper functions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from services.db_service import execute, fetch, fetchrow
from app.core.logging import get_logger

logger = get_logger()


async def start_worker_run(
    bot: str,
    city: Optional[str] = None,
    category: Optional[str] = None,
) -> UUID:
    """
    Create a new worker run record with status 'pending'.
    
    Returns the UUID of the created run.
    """
    try:
        row = await fetchrow(
            """
            INSERT INTO worker_runs (bot, city, category, status)
            VALUES ($1, $2, $3, 'pending')
            RETURNING id
            """,
            bot,
            city,
            category,
        )
        if row is None:
            raise RuntimeError("Failed to create worker run")
        return UUID(str(row["id"]))
    except Exception as e:
        logger.error(
            "start_worker_run_failed",
            bot=bot,
            city=city,
            category=category,
            error=str(e),
        )
        raise


async def mark_worker_run_running(run_id: UUID) -> None:
    """
    Mark a worker run as 'running' and set started_at timestamp.
    """
    try:
        await execute(
            """
            UPDATE worker_runs
            SET status = 'running',
                started_at = NOW(),
                progress = 0
            WHERE id = $1
            """,
            run_id,
        )
    except Exception as e:
        logger.warning(
            "mark_worker_run_running_failed",
            run_id=str(run_id),
            error=str(e),
        )


async def update_worker_run_progress(run_id: UUID, progress: int) -> None:
    """
    Update the progress percentage (0-100) for a running worker.
    """
    clamped = max(0, min(100, int(progress)))
    try:
        await execute(
            """
            UPDATE worker_runs
            SET progress = $1
            WHERE id = $2
            """,
            clamped,
            run_id,
        )
    except Exception as e:
        logger.warning(
            "update_worker_run_progress_failed",
            run_id=str(run_id),
            progress=clamped,
            error=str(e),
        )


async def finish_worker_run(
    run_id: UUID,
    status: str,
    progress: int,
    counters: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> None:
    """
    Finalize a worker run with final status, progress, counters, and optional error message.
    
    Status should be 'finished' for success or 'failed' for errors.
    """
    # Convert counters to JSON string, or use empty JSON object if None
    if counters is not None:
        counters_json = json.dumps(counters, ensure_ascii=False)
    else:
        counters_json = "{}"
    
    try:
        await execute(
            """
            UPDATE worker_runs
            SET status = $1,
                progress = $2,
                counters = CAST($3::text AS JSONB),
                error_message = $4,
                finished_at = NOW()
            WHERE id = $5
            """,
            status,
            max(0, min(100, progress)),
            counters_json,
            error_message,
            run_id,
        )
    except Exception as e:
        logger.error(
            "finish_worker_run_failed",
            run_id=str(run_id),
            status=status,
            error=str(e),
        )
        raise


async def get_worker_run(run_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single worker run by ID.
    
    Returns None if not found.
    """
    try:
        row = await fetchrow(
            """
            SELECT
                id,
                bot,
                city,
                category,
                status,
                progress,
                counters,
                error_message,
                started_at,
                finished_at,
                created_at
            FROM worker_runs
            WHERE id = $1
            """,
            run_id,
        )
        if row is None:
            return None
        return dict(row)
    except Exception as e:
        logger.warning(
            "get_worker_run_failed",
            run_id=str(run_id),
            error=str(e),
        )
        return None


async def list_worker_runs(
    bot: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    List worker runs with optional filtering.
    
    Returns a tuple of (runs_list, total_count).
    """
    try:
        # Build WHERE clause dynamically
        conditions = []
        params: List[Any] = []
        param_idx = 1

        if bot is not None:
            conditions.append(f"bot = ${param_idx}")
            params.append(bot)
            param_idx += 1

        if status is not None:
            conditions.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1

        if since is not None:
            conditions.append(f"started_at >= ${param_idx}")
            params.append(since)
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_sql = f"SELECT COUNT(*)::int AS total FROM worker_runs WHERE {where_clause}"
        count_rows = await fetch(count_sql, *params)
        total = int(count_rows[0]["total"]) if count_rows else 0

        # Get paginated results
        list_sql = f"""
            SELECT
                id,
                bot,
                city,
                category,
                status,
                progress,
                counters,
                error_message,
                started_at,
                finished_at,
                created_at
            FROM worker_runs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.append(limit)
        params.append(offset)
        rows = await fetch(list_sql, *params)

        return [dict(row) for row in rows], total
    except Exception as e:
        logger.error(
            "list_worker_runs_failed",
            bot=bot,
            status=status,
            since=since,
            error=str(e),
        )
        return [], 0

