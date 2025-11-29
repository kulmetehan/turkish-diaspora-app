"""
Reclassify 'other' Locations Worker

Purpose: Re-categorize locations with category='other' using the existing AI classification
stack (ClassifyService). Only accepts re-classifications where the AI returns a non-'other'
category with confidence_score >= min_confidence (default 0.8).

Uses the same AIClassification schema and update_location_classification() helper as
verify_locations.py and classify_bot.py.

Usage:
    python -m app.workers.reclassify_other --limit 200 --min-confidence 0.8
    python -m app.workers.reclassify_other --limit 50 --dry-run 1
    python -m app.workers.reclassify_other --limit 100 --source OSM_OVERPASS --state CANDIDATE
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID

# Load environment variables from .env file
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)

# ---------------------------------------------------------------------------
# Pathing zodat 'app.*' en 'services.*' werken
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent           # .../Backend/app
BACKEND_DIR = APP_DIR.parent                # .../Backend

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))    # .../Backend

# --- Uniform logging ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="reclassify_other")

# ---------------------------------------------------------------------------
# DB (asyncpg helpers)
# ---------------------------------------------------------------------------
from services.db_service import (
    init_db_pool,
    fetch,
    execute,
    update_location_classification,
    mark_last_verified,
)

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
from services.classify_service import ClassifyService
from services.ai_validation import validate_classification_payload
from services.audit_service import audit_service

# ---------------------------------------------------------------------------
# Worker Run Tracking
# ---------------------------------------------------------------------------
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    update_worker_run_progress,
    finish_worker_run,
)


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc

# ---------------------------------------------------------------------------
# Worker Logic
# ---------------------------------------------------------------------------
async def fetch_other_candidates(
    *,
    limit: int,
    source: Optional[str] = None,
    state: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch locations with category='other' that are candidates for re-classification.
    
    Filters:
    - category = 'other'
    - is_retired = false OR is_retired IS NULL
    - Optional: source filter
    - Optional: state filter
    
    Returns list of location dicts with id, name, address, category, state, etc.
    """
    filters = [
        "category = 'other'",
        "(is_retired = false OR is_retired IS NULL)",
    ]
    params: List[Any] = []
    param_idx = 1
    
    if state is not None:
        filters.append(f"state = ${param_idx}")
        params.append(state)
        param_idx += 1
    
    if source is not None:
        filters.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1
    
    where_clause = " AND ".join(filters)
    limit_param = param_idx
    params.append(int(limit))
    
    sql = f"""
        SELECT id,
               name,
               address,
               category,
               state,
               confidence_score,
               source,
               last_verified_at,
               notes
        FROM locations
        WHERE {where_clause}
        ORDER BY first_seen_at ASC
        LIMIT ${limit_param}
    """
    
    rows = await fetch(sql, *params)
    return [dict(r) for r in rows]


async def process_location(
    location: Dict[str, Any],
    classify_service: ClassifyService,
    min_confidence: float,
    dry_run: bool
) -> Dict[str, Any]:
    """
    Process a single location through classification and re-categorization.
    
    Returns dict with:
    - id, name, success, old_category, new_category, confidence, reason, error
    """
    location_id = location["id"]
    name = location["name"]
    address = location.get("address")
    old_category = location.get("category", "other")
    
    result = {
        "id": location_id,
        "name": name,
        "old_category": old_category,
        "new_category": None,
        "confidence": None,
        "reason": None,
        "success": False,
        "error": None,
        "skip_reason": None,
    }
    
    try:
        # 1. Classify using existing service
        classification_result, meta = classify_service.classify(
            name=name,
            address=address,
            typ=old_category,
            location_id=location_id
        )
        
        # 2. Validate using existing validation
        validated_classification = validate_classification_payload(
            classification_result.model_dump()
        )
        
        action = validated_classification.action.value
        category_result = validated_classification.category.value if validated_classification.category else None
        confidence = float(validated_classification.confidence_score)
        reason = validated_classification.reason
        
        result.update({
            "new_category": category_result,
            "confidence": confidence,
            "reason": reason,
        })
        
        # 3. Acceptance logic: only accept if category != "other" AND confidence >= min_confidence
        if category_result == "other":
            result["skip_reason"] = "still_other"
            result["success"] = True  # Successfully classified, but skipped
            return result
        
        if confidence < min_confidence:
            result["skip_reason"] = "low_confidence"
            result["success"] = True  # Successfully classified, but skipped
            return result
        
        # 4. If action is "ignore", we still skip (don't update category)
        if action == "ignore":
            result["skip_reason"] = "action_ignore"
            result["success"] = True
            return result
        
        # 5. Apply re-classification via central helper
        if not dry_run:
            await update_location_classification(
                id=int(location_id),
                action=action,
                category=category_result,
                confidence_score=float(confidence),
                reason=reason or "reclassify_other: re-categorized from 'other'",
            )
        
        result.update({
            "success": True,
        })
        
        if not dry_run:
            await audit_service.log(
                action_type="reclassify_other.classified",
                actor="reclassify_other_bot",
                location_id=location_id,
                before={"category": old_category},
                after={"category": category_result, "confidence_score": confidence},
                is_success=True,
                meta={
                    "confidence_threshold": min_confidence,
                    "old_category": old_category,
                }
            )
    
    except Exception as e:
        result["error"] = str(e)
        logger.error("process_location_error", location_id=location_id, error=str(e))
        # Edge: stamp so we don't retry forever in a tight loop
        try:
            if not dry_run:
                await mark_last_verified(location_id, note="skipped by reclassify_other: error during classification")
        except Exception:
            pass
    
    return result


async def run_reclassify(
    limit: int,
    min_confidence: float,
    dry_run: bool,
    model: Optional[str],
    source: Optional[str] = None,
    state: Optional[str] = None,
    worker_run_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """
    Main reclassification logic.
    
    Fetches locations with category='other', classifies them via AI, and updates
    those that get a non-'other' category with confidence >= min_confidence.
    """
    classify_service = ClassifyService(model=model)
    last_progress = -1
    
    # Fetch candidates
    candidates = await fetch_other_candidates(
        limit=limit,
        source=source,
        state=state,
    )
    
    if not candidates:
        counters: Dict[str, Any] = {
            "total_fetched": 0,
            "total_attempted": 0,
            "total_reclassified": 0,
            "total_skipped_low_conf": 0,
            "total_skipped_still_other": 0,
            "total_errors": 0,
        }
        if worker_run_id:
            await finish_worker_run(worker_run_id, "finished", 100, counters, None)
        return counters
    
    print(f"[ReclassifyOtherBot] Processing {len(candidates)} locations with category='other'...")
    
    total_fetched = len(candidates)
    total_attempted = 0
    total_reclassified = 0
    total_skipped_low_conf = 0
    total_skipped_still_other = 0
    total_errors = 0
    
    total_candidates = len(candidates)
    
    async def report_progress(index: int) -> None:
        nonlocal last_progress
        if not worker_run_id or total_candidates <= 0:
            return
        percent = min(99, max(0, int((index * 100) / total_candidates)))
        if percent != last_progress:
            await update_worker_run_progress(worker_run_id, percent)
            last_progress = percent
    
    try:
        for idx, location in enumerate(candidates, start=1):
            total_attempted += 1
            
            result = await process_location(
                location=location,
                classify_service=classify_service,
                min_confidence=min_confidence,
                dry_run=dry_run
            )
            
            # Print result and update counters
            if result["error"]:
                total_errors += 1
                print(f"[ERROR] id={result['id']} name={result['name']!r} -> {result['error']}")
            elif result["skip_reason"] == "still_other":
                total_skipped_still_other += 1
                print(f"[SKIP_STILL_OTHER] id={result['id']} name={result['name']!r} -> AI returned 'other'")
            elif result["skip_reason"] == "low_confidence":
                total_skipped_low_conf += 1
                print(f"[SKIP_LOW_CONF] id={result['id']} name={result['name']!r} -> conf={result['confidence']:.2f} < {min_confidence:.2f}")
            elif result["skip_reason"] == "action_ignore":
                total_skipped_still_other += 1
                print(f"[SKIP_IGNORE] id={result['id']} name={result['name']!r} -> action=ignore")
            elif result["success"] and result["new_category"] and result["new_category"] != "other":
                total_reclassified += 1
                print(f"[RECLASSIFIED] id={result['id']} name={result['name']!r} "
                      f"-> {result['old_category']} -> {result['new_category']} conf={result['confidence']:.2f}")
            
            await report_progress(idx)
    
    except Exception as exc:
        if worker_run_id:
            progress_snapshot = last_progress if last_progress >= 0 else 0
            await finish_worker_run(worker_run_id, "failed", progress_snapshot, None, str(exc))
        raise
    
    counters = {
        "total_fetched": total_fetched,
        "total_attempted": total_attempted,
        "total_reclassified": total_reclassified,
        "total_skipped_low_conf": total_skipped_low_conf,
        "total_skipped_still_other": total_skipped_still_other,
        "total_errors": total_errors,
    }
    
    if worker_run_id:
        await finish_worker_run(worker_run_id, "finished", 100, counters, None)
    
    return counters

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ReclassifyOtherBot — re-categorize locations with category='other'")
    ap.add_argument("--limit", type=int, default=200, help="Max items to process")
    ap.add_argument("--min-confidence", type=float, default=0.8, help="Minimum confidence for re-classification (0..1)")
    ap.add_argument("--dry-run", type=int, default=0, help="Dry run mode (1=yes, 0=no)")
    ap.add_argument("--model", help="Override AI model")
    ap.add_argument("--source", help="Filter by source (e.g., OSM_OVERPASS, GOOGLE_PLACES)")
    ap.add_argument("--state", help="Filter by state (e.g., CANDIDATE, PENDING_VERIFICATION, VERIFIED)")
    ap.add_argument("--worker-run-id", type=_parse_worker_run_id, help="UUID van worker_runs record voor progress rapportage")
    return ap.parse_args()


async def main_async():
    t0 = time.perf_counter()
    with with_run_id() as rid:
        logger.info("worker_started")
        args = parse_args()
        worker_run_id: Optional[UUID] = getattr(args, "worker_run_id", None)
        
        print(f"\n[ReclassifyOtherBot] Configuration:")
        print(f"  Limit: {args.limit}")
        print(f"  Min confidence: {args.min_confidence}")
        print(f"  Source filter: {args.source or 'none'}")
        print(f"  State filter: {args.state or 'none'}")
        print(f"  Dry run: {bool(args.dry_run)}")
        print(f"  Model: {args.model or 'default'}\n")
        
        # Ensure DB pool is ready
        await init_db_pool()
        
        # Auto-create worker_run if not provided
        if not worker_run_id:
            worker_run_id = await start_worker_run(bot="reclassify_other", city=None, category=None)
        
        if worker_run_id:
            await mark_worker_run_running(worker_run_id)
        
        try:
            result = await run_reclassify(
                limit=args.limit,
                min_confidence=args.min_confidence,
                dry_run=bool(args.dry_run),
                model=args.model,
                source=args.source,
                state=args.state,
                worker_run_id=worker_run_id,
            )
        except Exception as e:
            # run_reclassify already handles finish_worker_run on error, but we log here too
            duration_ms = int((time.perf_counter() - t0) * 1000)
            logger.error("worker_failed", duration_ms=duration_ms, error=str(e))
            raise
        
        # Summary
        print(f"\nReclassify 'other' summary:")
        print(f"  fetched: {result['total_fetched']}")
        print(f"  attempted: {result['total_attempted']}")
        print(f"  reclassified (non-'other', conf >= {args.min_confidence:.2f}): {result['total_reclassified']}")
        print(f"  skipped (still 'other'): {result['total_skipped_still_other']}")
        print(f"  skipped (low confidence): {result['total_skipped_low_conf']}")
        print(f"  errors: {result['total_errors']}")
        print(f"  Dry run: {bool(args.dry_run)}")
        
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("worker_finished", 
                   duration_ms=duration_ms,
                   total_fetched=result['total_fetched'],
                   total_attempted=result['total_attempted'],
                   total_reclassified=result['total_reclassified'],
                   total_skipped_still_other=result['total_skipped_still_other'],
                   total_skipped_low_conf=result['total_skipped_low_conf'],
                   total_errors=result['total_errors'])


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[ReclassifyOtherBot] Interrupted by user.")
    except Exception as e:
        print(f"\n[ReclassifyOtherBot] ERROR: {e}")
        raise


if __name__ == "__main__":
    main()

