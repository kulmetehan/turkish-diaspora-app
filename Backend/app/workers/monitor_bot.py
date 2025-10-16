# Backend/app/workers/monitor_bot.py
# TDA-16: MonitorBot & Freshness Policy Engine
# - Selecteert due records (next_check_at <= NOW()) voor actieve locaties
# - Enqueue't VERIFICATION-taken in tasks-queue
# - (Re)calculeert next_check_at volgens Freshness Policy
# - CLI: python -m app.workers.monitor_bot --limit 200 --dry-run

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, Field
from sqlalchemy import text, bindparam

# Hergebruik de bestaande async engine uit jullie project
from services.db_service import async_engine

UTC = timezone.utc
TERMINAL_STATES: tuple[str, ...] = ("RETIRED", "SUSPENDED")


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
    LOW_CONF_DAYS_FAST: int = 3
    LOW_CONF_DAYS_SLOW: int = 7
    NEW_HIGH_CONF_DAYS: int = 14
    PROBABLE_NOT_OPEN_YET_DAYS: int = 14
    VERIFIED_FEW_REVIEWS_DAYS: int = 30
    VERIFIED_MEDIUM_REVIEWS_DAYS: int = 60
    VERIFIED_MANY_REVIEWS_MIN: int = 100
    VERIFIED_MANY_REVIEWS_DAYS: int = 90
    TEMP_CLOSED_MIN_DAYS: int = 7
    TEMP_CLOSED_MAX_DAYS: int = 14
    ABS_MAX_DAYS: int = 90  # harde cap – nooit ouder dan 90 dagen

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

        return cls(
            MONITOR_MAX_PER_RUN=_i("MONITOR_MAX_PER_RUN", 200),
            BOOTSTRAP_BATCH=_i("MONITOR_BOOTSTRAP_BATCH", 2000),
            DRY_RUN=_b("MONITOR_DRY_RUN", False),
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

    # Temporarily closed → kort-cyclisch
    if business_status and "TEMPORARILY_CLOSED" in business_status:
        days = cfg.TEMP_CLOSED_MIN_DAYS
    # Nog niet open → sneller terugkomen
    elif probable_not_open:
        days = cfg.PROBABLE_NOT_OPEN_YET_DAYS
    # Verified → afhankelijk van volume reviews
    elif state == "VERIFIED":
        if urt >= cfg.VERIFIED_MANY_REVIEWS_MIN:
            days = cfg.VERIFIED_MANY_REVIEWS_DAYS
        elif urt >= 10:
            days = cfg.VERIFIED_MEDIUM_REVIEWS_DAYS
        else:
            days = cfg.VERIFIED_FEW_REVIEWS_DAYS
    # Candidate/pending → confidence-gestuurd
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
    # BELANGRIJK: gebruik bindparam(expanding=True) voor NOT IN (…) met parameters
    query = (
        text(
            f"""
            SELECT {SELECT_COLS}
            FROM locations
            WHERE next_check_at IS NULL
              AND state NOT IN :terminal
            ORDER BY COALESCE(last_verified_at, NOW()) ASC
            LIMIT :lim
            """
        )
        .bindparams(bindparam("terminal", expanding=True))
    )
    async with async_engine.begin() as conn:
        rows = (
            await conn.execute(
                query,
                {"terminal": list(TERMINAL_STATES), "lim": limit},
            )
        ).mappings().all()
    return rows


async def _fetch_due_rows(limit: int) -> Sequence[Mapping[str, Any]]:
    query = (
        text(
            f"""
            SELECT {SELECT_COLS}
            FROM locations
            WHERE next_check_at <= NOW()
              AND state NOT IN :terminal
            ORDER BY next_check_at ASC
            LIMIT :lim
            """
        )
        .bindparams(bindparam("terminal", expanding=True))
    )
    async with async_engine.begin() as conn:
        rows = (
            await conn.execute(
                query,
                {"terminal": list(TERMINAL_STATES), "lim": limit},
            )
        ).mappings().all()
    return rows


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

    async with async_engine.begin() as conn:
        for r in rows:
            nca = compute_next_check_at(r, cfg)
            total_updated += 1
            if not cfg.DRY_RUN:
                await conn.execute(
                    text(
                        """
                        UPDATE locations
                        SET next_check_at = :nca
                        WHERE id = :id
                        """
                    ),
                    {"nca": nca, "id": r["id"]},
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

    async with async_engine.begin() as conn:
        for r in due_rows:
            # 1) enqueue taak
            if not cfg.DRY_RUN:
                await conn.execute(
                    text(
                        """
                        INSERT INTO tasks (task_type, location_id, status, created_at)
                        VALUES ('VERIFICATION', :loc_id, 'PENDING', NOW())
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"loc_id": r["id"]},
                )
            made_tasks += 1

            # 2) bump next_check_at volgens policy
            nca = compute_next_check_at(r, cfg)
            if not cfg.DRY_RUN:
                await conn.execute(
                    text(
                        """
                        UPDATE locations
                        SET next_check_at = :nca
                        WHERE id = :id
                        """
                    ),
                    {"nca": nca, "id": r["id"]},
                )
            bumped += 1

    return (made_tasks, bumped)


async def stats_after() -> Mapping[str, Any]:
    async with async_engine.begin() as conn:
        older = (
            await conn.execute(
                text(
                    """
                    SELECT COUNT(*)::int AS cnt
                    FROM locations
                    WHERE next_check_at IS NOT NULL
                      AND next_check_at < NOW() - INTERVAL '90 days'
                    """
                )
            )
        ).mappings().first()
        oldest_due = (
            await conn.execute(
                text(
                    """
                    SELECT MIN(next_check_at) AS oldest_due
                    FROM locations
                    WHERE next_check_at <= NOW()
                      AND state NOT IN :terminal
                    """
                ).bindparams(bindparam("terminal", expanding=True)),
                {"terminal": list(TERMINAL_STATES)},
            )
        ).mappings().first()
    return {"older_than_90d": older["cnt"], "oldest_due": oldest_due["oldest_due"]}


# ------------------------------
# CLI
# ------------------------------
async def main_async(limit: Optional[int], dry_run: Optional[bool]) -> None:
    cfg = MonitorSettings.from_env()
    if limit is not None:
        cfg.MONITOR_MAX_PER_RUN = int(limit)
    if dry_run is not None:
        cfg.DRY_RUN = bool(dry_run)

    print(f"[MonitorBot] start DRY_RUN={cfg.DRY_RUN} limit={cfg.MONITOR_MAX_PER_RUN}")

    # 1) Bootstrap ontbrekende next_check_at (actieve staten)
    boot = await bootstrap_missing_next_check(cfg)
    print(f"[MonitorBot] initialized next_check_at for {boot} records")

    # 2) Verwerk due records in batch
    enq, bump = await enqueue_verification_tasks(cfg)
    print(f"[MonitorBot] enqueued={enq} bumped_next_check_at={bump}")

    # 3) Sanity stats
    s = await stats_after()
    print(f"[MonitorBot] records >90d overdue (after run): {s['older_than_90d']}")
    print(f"[MonitorBot] oldest due next_check_at (after run): {s['oldest_due']}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TDA-16 MonitorBot")
    p.add_argument("--limit", type=int, default=None, help="Max records per run (due batch)")
    p.add_argument("--dry-run", action="store_true", help="No writes")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main_async(limit=args.limit, dry_run=args.dry_run))
