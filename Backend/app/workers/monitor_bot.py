# Backend/app/workers/monitor_bot.py
# TDA-16: MonitorBot & Freshness Policy Engine
# - Selecteert due records (next_check_at <= NOW()) voor actieve locaties
# - Enqueue't VERIFICATION-taken in tasks-queue
# - (Re)calculeert next_check_at volgens Freshness Policy
# - CLI: python -m app.workers.monitor_bot --limit 200 --dry-run

from __future__ import annotations

import argparse
import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence
from pathlib import Path
import sys
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pathing zodat 'app.*' en 'services.*' werken (CI, GH Actions, lokale run)
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent           # .../Backend/app
BACKEND_DIR = APP_DIR.parent                # .../Backend

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))    # .../Backend

# --- Uniform logging voor workers ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="monitor_bot")

# DB helpers (asyncpg)
from services.db_service import init_db_pool, fetch, execute  # noqa: E402

# Worker run tracking
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    update_worker_run_progress,
    finish_worker_run,
)

UTC = timezone.utc
TERMINAL_STATES: tuple[str, ...] = ("RETIRED", "SUSPENDED")

# Module-level defaults for monitor freshness policy (days)
DEFAULT_LOW_CONF_DAYS_FAST = 3
DEFAULT_LOW_CONF_DAYS_SLOW = 7
DEFAULT_NEW_HIGH_CONF_DAYS = 14
DEFAULT_VERIFIED_FEW_REVIEWS_DAYS = 30
DEFAULT_VERIFIED_MEDIUM_REVIEWS_DAYS = 60
DEFAULT_VERIFIED_MANY_REVIEWS_DAYS = 90


# ------------------------------
# Config (Pydantic v2 style)
# ------------------------------
class MonitorSettings(BaseModel):
    # Batch-limieten
    MONITOR_MAX_PER_RUN: int = Field(200, description="Maximaal aantal due records per run")
    BOOTSTRAP_BATCH: int = Field(2000, description="Init batch voor ontbrekende next_check_at")

    # Run-gedrag
    DRY_RUN: bool = Field(False, description="Geen writes uitvoeren")

    # Freshness Policy (dagen)
    LOW_CONF_DAYS_FAST: int = DEFAULT_LOW_CONF_DAYS_FAST
    LOW_CONF_DAYS_SLOW: int = DEFAULT_LOW_CONF_DAYS_SLOW
    NEW_HIGH_CONF_DAYS: int = DEFAULT_NEW_HIGH_CONF_DAYS
    PROBABLE_NOT_OPEN_YET_DAYS: int = 14
    VERIFIED_FEW_REVIEWS_DAYS: int = DEFAULT_VERIFIED_FEW_REVIEWS_DAYS
    VERIFIED_MEDIUM_REVIEWS_DAYS: int = DEFAULT_VERIFIED_MEDIUM_REVIEWS_DAYS
    VERIFIED_MANY_REVIEWS_MIN: int = 100
    VERIFIED_MANY_REVIEWS_DAYS: int = DEFAULT_VERIFIED_MANY_REVIEWS_DAYS
    TEMP_CLOSED_MIN_DAYS: int = 7
    TEMP_CLOSED_MAX_DAYS: int = 14
    ABS_MAX_DAYS: int = 90  # harde cap â€" nooit ouder dan 90 dagen

    @classmethod
    def from_env(cls) -> "MonitorSettings":
        import os

        def _b(name: str, default: bool) -> bool:
            v = os.environ.get(name)
            return default if v is None else v.strip().lower() in ("1", "true", "yes", "y")

        def _i(name: str, default: int) -> int:
            v = os.environ.get(name)
            if v is None:
                return default
            try:
                return int(v)
            except Exception:
                return default

        # Try to load freshness days from ai_config, fallback to defaults
        low_conf_days = DEFAULT_LOW_CONF_DAYS_FAST
        medium_conf_days = DEFAULT_LOW_CONF_DAYS_SLOW
        high_conf_days = DEFAULT_NEW_HIGH_CONF_DAYS
        few_reviews_days = DEFAULT_VERIFIED_FEW_REVIEWS_DAYS
        medium_reviews_days = DEFAULT_VERIFIED_MEDIUM_REVIEWS_DAYS
        many_reviews_days = DEFAULT_VERIFIED_MANY_REVIEWS_DAYS
        
        try:
            import asyncio
            from services.db_service import init_db_pool
            from services.ai_config_service import get_ai_config
            
            async def _load_config():
                await init_db_pool()
                config = await get_ai_config()
                if config:
                    return (
                        config.monitor_low_conf_days,
                        config.monitor_medium_conf_days,
                        config.monitor_high_conf_days,
                        config.monitor_verified_few_reviews_days,
                        config.monitor_verified_medium_reviews_days,
                        config.monitor_verified_many_reviews_days,
                    )
                return None
            
            config_values = asyncio.run(_load_config())
            if config_values:
                low_conf_days, medium_conf_days, high_conf_days, few_reviews_days, medium_reviews_days, many_reviews_days = config_values
        except Exception as e:
            from app.core.logging import get_logger
            logger = get_logger()
            logger.warning("failed_to_load_monitor_config", error=str(e), fallback_to_defaults=True)

        return cls(
            MONITOR_MAX_PER_RUN=_i("MONITOR_MAX_PER_RUN", 200),
            BOOTSTRAP_BATCH=_i("MONITOR_BOOTSTRAP_BATCH", 2000),
            DRY_RUN=_b("MONITOR_DRY_RUN", False),
            LOW_CONF_DAYS_FAST=low_conf_days,
            LOW_CONF_DAYS_SLOW=medium_conf_days,
            NEW_HIGH_CONF_DAYS=high_conf_days,
            VERIFIED_FEW_REVIEWS_DAYS=few_reviews_days,
            VERIFIED_MEDIUM_REVIEWS_DAYS=medium_reviews_days,
            VERIFIED_MANY_REVIEWS_DAYS=many_reviews_days,
        )


# ------------------------------
# Policy
# ------------------------------
def compute_next_check_at(row: Mapping[str, Any], cfg: MonitorSettings) -> datetime:
    """
    Freshness Policy o.b.v. status, confidence, reviews en flags.
    Houdt een harde cap van 90 dagen aan.
    """
    state: str = (row.get("state") or "").upper()
    business_status: Optional[str] = (row.get("business_status") or "").upper() or None
    conf: float = float(row.get("confidence_score") or 0.0)
    urt: int = int(row.get("user_ratings_total") or 0)
    probable_not_open: bool = bool(row.get("is_probable_not_open_yet"))

    last_verified_at = row.get("last_verified_at")
    base_dt = (
        last_verified_at.astimezone(UTC)
        if isinstance(last_verified_at, datetime)
        else datetime.now(tz=UTC)
    )

    # Temporarily closed â†' kort-cyclisch
    if business_status and "TEMPORARILY_CLOSED" in business_status:
        days = cfg.TEMP_CLOSED_MIN_DAYS
    # Nog niet open â†' sneller terugkomen
    elif probable_not_open:
        days = cfg.PROBABLE_NOT_OPEN_YET_DAYS
    # Verified â†' afhankelijk van volume reviews
    elif state == "VERIFIED":
        if urt >= cfg.VERIFIED_MANY_REVIEWS_MIN:
            days = cfg.VERIFIED_MANY_REVIEWS_DAYS
        elif urt >= 10:
            days = cfg.VERIFIED_MEDIUM_REVIEWS_DAYS
        else:
            days = cfg.VERIFIED_FEW_REVIEWS_DAYS
    # Candidate/pending â†' confidence-gestuurd
    else:
        if conf < 0.60:
            days = cfg.LOW_CONF_DAYS_FAST
        elif conf < 0.80:
            days = cfg.LOW_CONF_DAYS_SLOW
        else:
            days = cfg.NEW_HIGH_CONF_DAYS

    days = min(days, cfg.ABS_MAX_DAYS)
    return base_dt + timedelta(days=days)


# ------------------------------
# SQL helpers
# ------------------------------
SELECT_COLS = """
    id, state, confidence_score, user_ratings_total, business_status,
    is_probable_not_open_yet, last_verified_at, next_check_at
"""


async def _fetch_bootstrap_rows(limit: int) -> Sequence[Mapping[str, Any]]:
    sql = (
        f"""
        SELECT {SELECT_COLS}
        FROM locations
        WHERE next_check_at IS NULL
          AND state NOT IN ('RETIRED', 'SUSPENDED')
        ORDER BY COALESCE(last_verified_at, NOW()) ASC
        LIMIT $1
        """
    )
    rows = await fetch(sql, int(limit))
    return [dict(r) for r in rows]


async def _fetch_due_rows(limit: int) -> Sequence[Mapping[str, Any]]:
    sql = (
        f"""
        SELECT {SELECT_COLS}
        FROM locations
        WHERE next_check_at <= NOW()
          AND state NOT IN ('RETIRED', 'SUSPENDED')
        ORDER BY next_check_at ASC
        LIMIT $1
        """
    )
    rows = await fetch(sql, int(limit))
    return [dict(r) for r in rows]


# ------------------------------
# Kernroutines
# ------------------------------
async def bootstrap_missing_next_check(cfg: MonitorSettings) -> int:
    """
    Zet next_check_at voor records waar het NULL is (actieve staten).
    """
    total_updated = 0
    rows = await _fetch_bootstrap_rows(cfg.BOOTSTRAP_BATCH)
    if not rows:
        return 0

    for r in rows:
        nca = compute_next_check_at(r, cfg)
        total_updated += 1
        if not cfg.DRY_RUN:
            await execute(
                """
                UPDATE locations
                SET next_check_at = $1
                WHERE id = $2
                """,
                nca,
                int(r["id"]),
            )
    return total_updated


async def enqueue_verification_tasks(cfg: MonitorSettings) -> tuple[int, int]:
    """
    Voor due records: maak VERIFICATION-tasks en bump next_check_at.
    Return: (aantal_tasks, aantal_bumped)
    """
    made_tasks = 0
    bumped = 0
    due_rows = await _fetch_due_rows(cfg.MONITOR_MAX_PER_RUN)
    if not due_rows:
        return (0, 0)

    for r in due_rows:
        # Only enqueue verification tasks for VERIFIED locations
        if (r.get("state") or "").upper() != "VERIFIED":
            continue
        # 1) enqueue taak
        if not cfg.DRY_RUN:
            await execute(
                """
                INSERT INTO tasks (task_type, location_id, status, created_at)
                VALUES ('VERIFICATION', $1, 'PENDING', NOW())
                ON CONFLICT DO NOTHING
                """,
                int(r["id"]),
            )
        made_tasks += 1

        # 2) bump next_check_at volgens policy
        nca = compute_next_check_at(r, cfg)
        if not cfg.DRY_RUN:
            await execute(
                """
                UPDATE locations
                SET next_check_at = $1
                WHERE id = $2
                """,
                nca,
                int(r["id"]),
            )
        bumped += 1

    return (made_tasks, bumped)


async def stats_after() -> Mapping[str, Any]:
    older_rows = await fetch(
        """
        SELECT COUNT(*)::int AS cnt
        FROM locations
        WHERE next_check_at IS NOT NULL
          AND next_check_at < NOW() - INTERVAL '90 days'
        """
    )
    oldest_rows = await fetch(
        """
        SELECT MIN(next_check_at) AS oldest_due
        FROM locations
        WHERE next_check_at <= NOW()
          AND state NOT IN ('RETIRED', 'SUSPENDED')
        """
    )
    older_cnt = int((older_rows[0]["cnt"] if older_rows else 0) or 0)
    oldest_due = oldest_rows[0]["oldest_due"] if oldest_rows else None
    return {"older_than_90d": older_cnt, "oldest_due": oldest_due}


# ------------------------------
# CLI
# ------------------------------
async def main_async(limit: Optional[int], dry_run: Optional[bool], worker_run_id: Optional[UUID] = None) -> None:
    t0 = time.perf_counter()
    with with_run_id() as rid:
        logger.info("worker_started")
        await init_db_pool()
        
        # Auto-create worker_run if not provided
        if not worker_run_id:
            worker_run_id = await start_worker_run(bot="monitor_bot", city=None, category=None)
        
        if worker_run_id:
            await mark_worker_run_running(worker_run_id)
            await update_worker_run_progress(worker_run_id, 10)
        
        cfg = MonitorSettings.from_env()
        if limit is not None:
            cfg.MONITOR_MAX_PER_RUN = int(limit)
        if dry_run is not None:
            cfg.DRY_RUN = bool(dry_run)

        print(f"[MonitorBot] start DRY_RUN={cfg.DRY_RUN} limit={cfg.MONITOR_MAX_PER_RUN}")
        
        counters = {}
        try:
            # 1) Bootstrap ontbrekende next_check_at (actieve staten)
            boot = await bootstrap_missing_next_check(cfg)
            print(f"[MonitorBot] initialized next_check_at for {boot} records")
            
            if worker_run_id:
                await update_worker_run_progress(worker_run_id, 40)

            # 2) Verwerk due records in batch
            enq, bump = await enqueue_verification_tasks(cfg)
            print(f"[MonitorBot] enqueued={enq} bumped_next_check_at={bump}")
            
            if worker_run_id:
                await update_worker_run_progress(worker_run_id, 80)

            # 3) Sanity stats
            s = await stats_after()
            print(f"[MonitorBot] records >90d overdue (after run): {s['older_than_90d']}")
            print(f"[MonitorBot] oldest due next_check_at (after run): {s['oldest_due']}")
            
            counters = {
                "enqueued": enq,
                "bumped": bump,
                "bootstrapped": boot,
            }
            
            duration_ms = int((time.perf_counter() - t0) * 1000)
            logger.info("worker_finished", duration_ms=duration_ms)
            
            # Finalize worker run on success
            if worker_run_id:
                await finish_worker_run(worker_run_id, "finished", 100, counters, None)
        except Exception as e:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            logger.error("worker_failed", duration_ms=duration_ms, error=str(e))
            # Finalize worker run on error
            if worker_run_id:
                progress = 50  # Approximate progress at failure
                await finish_worker_run(worker_run_id, "failed", progress, counters, str(e))
            raise


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TDA-16 MonitorBot")
    p.add_argument("--limit", type=int, default=None, help="Max records per run (due batch)")
    p.add_argument("--dry-run", action="store_true", help="No writes")
    p.add_argument("--worker-run-id", type=_parse_worker_run_id, help="UUID of worker_runs record for progress tracking")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    worker_run_id: Optional[UUID] = getattr(args, "worker_run_id", None)
    asyncio.run(main_async(limit=args.limit, dry_run=args.dry_run, worker_run_id=worker_run_id))
