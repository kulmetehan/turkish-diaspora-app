# -*- coding: utf-8 -*-
"""
Reset and prepare for re-verification (canonical pipeline)

This script performs a safe reset of location states so we can re-run the
canonical pipeline (classify_bot -> PENDING_VERIFICATION, then verify_locations
-> VERIFIED/RETIRED) with a clean slate and a strict confidence threshold (>=0.80).

What it does:
- Resets all rows in states VERIFIED or PENDING_VERIFICATION back to CANDIDATE
  and clears confidence-related fields and scheduling fields
- Clears notes for all CANDIDATE rows (to remove low-confidence or legacy noise)
- Leaves RETIRED rows untouched

How to run (from Backend directory):
    python -m scripts.reset_and_prepare_reverify

Environment:
- Uses the shared async engine from services.db_service (DATABASE_URL, etc.)
"""

from __future__ import annotations

import asyncio
from typing import Optional

from sqlalchemy import text

try:
    # Standard project import (same as workers)
    from services.db_service import async_engine
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Could not import services.db_service.async_engine. Run this via 'python -m scripts.reset_and_prepare_reverify' from Backend."
    ) from e


SQL_RESET_VERIFIED_AND_PENDING = text(
    """
    UPDATE locations
    SET
        state = 'CANDIDATE',
        confidence_score = NULL,
        last_verified_at = NULL,
        next_check_at = NULL
    WHERE state IN ('VERIFIED', 'PENDING_VERIFICATION');
    """
)


SQL_CLEAR_NOTES_FOR_CANDIDATE = text(
    """
    UPDATE locations
    SET
        notes = NULL
    WHERE state = 'CANDIDATE';
    """
)


async def _run_reset() -> tuple[Optional[int], Optional[int]]:
    """Execute the two reset steps inside a single transaction.

    Returns a tuple of affected row counts: (affected_step1, affected_step2)
    Note: rowcount presence depends on driver; may be None on some backends.
    """
    async with async_engine.begin() as conn:
        res1 = await conn.execute(SQL_RESET_VERIFIED_AND_PENDING)
        affected1 = getattr(res1, "rowcount", None)

        res2 = await conn.execute(SQL_CLEAR_NOTES_FOR_CANDIDATE)
        affected2 = getattr(res2, "rowcount", None)

    return affected1, affected2


async def main() -> None:
    print("\n[RESET] Turkish Diaspora App — Clean Reset & Prepare Re-Verify")
    print("[WARN] This will:")
    print("       - Reset all locations in VERIFIED and PENDING_VERIFICATION back to CANDIDATE")
    print("       - Clear confidence_score, last_verified_at, next_check_at on those rows")
    print("       - Clear notes on all CANDIDATE rows")
    print("       - Leave RETIRED rows untouched")
    print("\nType 'YES' to proceed, anything else to abort.")

    try:
        confirm = input(
            "Confirm reset (type YES): "
        ).strip()
    except EOFError:
        confirm = ""

    if confirm != "YES":
        print("[ABORT] No changes made.")
        return

    print("\n[RUN] Executing reset SQL statements...")
    try:
        affected1, affected2 = await _run_reset()
        print(f"[OK] Step 1 — Reset VERIFIED/PENDING_VERIFICATION -> CANDIDATE (rows: {affected1 if affected1 is not None else 'unknown'})")
        print(f"[OK] Step 2 — Clear notes on CANDIDATE (rows: {affected2 if affected2 is not None else 'unknown'})")
    except Exception as e:
        print(f"[ERROR] Failed to execute reset: {e}")
        raise

    print("\n[NEXT] Re-run the canonical pipeline with 0.80 confidence:")
    print("  Step 1 — Classify CANDIDATE to PENDING_VERIFICATION (>= 0.80):")
    print("    python -m app.workers.classify_bot --limit 2000 --min-confidence 0.80")
    print("\n  Step 2 — Verify PENDING_VERIFICATION to VERIFIED/RETIRED (>= 0.80):")
    print("    python -m app.workers.verify_locations --limit 2000 --min-confidence 0.80")
    print("\n  Step 3 — (Optional) Let the scheduled task_verifier continue re-checking VERIFIED over time.")
    print("\n[DONE] Reset completed. Proceed with the NEXT steps above.")


if __name__ == "__main__":
    asyncio.run(main())


