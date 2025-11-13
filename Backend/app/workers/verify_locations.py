from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
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
logger = logger.bind(worker="verify_locations")

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


async def mark_worker_run_running(run_id: UUID) -> None:
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


async def update_worker_run_progress(run_id: UUID, progress: int) -> None:
    clamped = max(0, min(100, int(progress)))
    await execute(
        """
        UPDATE worker_runs
        SET progress = $1
        WHERE id = $2
        """,
        clamped,
        run_id,
    )


async def finalize_worker_run(
    run_id: UUID,
    status: str,
    progress: int,
    counters: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> None:
    counters_json = (
        json.dumps(counters, ensure_ascii=False) if counters is not None else None
    )
    await execute(
        """
        UPDATE worker_runs
        SET status = $1,
            progress = $2,
            counters = CASE WHEN $3 IS NULL THEN NULL ELSE CAST($3 AS JSONB) END,
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


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
from services.classify_service import ClassifyService
from services.ai_validation import validate_classification_payload
from services.audit_service import audit_service

# ---------------------------------------------------------------------------
# Worker Logic
# ---------------------------------------------------------------------------
async def fetch_candidates(
    *,
    limit: int,
    min_confidence: float,
) -> List[Dict[str, Any]]:
    """Fetch locations that are worth sending to OpenAI per cost-aware rules."""
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
          AND (confidence_score IS NULL OR confidence_score < $1)
          AND (is_retired = false OR is_retired IS NULL)
          AND (
                last_verified_at IS NULL
                OR last_verified_at < NOW() - INTERVAL '24 hours'
              )
        ORDER BY first_seen_at DESC
        LIMIT $2
        """
    )
    rows = await fetch(sql, float(min_confidence), int(limit))
    return [dict(r) for r in rows]

async def _apply_classification(
    *,
    location_id: int,
    action: str,
    category: str,
    confidence: float,
    reason: Optional[str],
    dry_run: bool,
) -> None:
    if dry_run:
        return
    await update_location_classification(
        id=int(location_id),
        action=action,
        category=category,
        confidence_score=float(confidence),
        reason=reason or "verify_locations: applied",
    )

async def process_location(
    location: Dict[str, Any],
    classify_service: ClassifyService,
    min_confidence: float,
    dry_run: bool
) -> Dict[str, Any]:
    """Process a single location through classification and validation."""
    location_id = location["id"]
    name = location["name"]
    address = location.get("address")
    category = location.get("category")
    
    result = {
        "id": location_id,
        "name": name,
        "old_state": location["state"],
        "new_state": None,
        "action": None,
        "category": None,
        "confidence": None,
        "reason": None,
        "success": False,
        "error": None
    }
    
    try:
        # 1. Classify using existing service
        classification_result, meta = classify_service.classify(
            name=name,
            address=address,
            typ=category,
            location_id=location_id
        )

        # 2. Validate using existing validation
        validated_classification = validate_classification_payload(
            classification_result.model_dump()
        )

        action = validated_classification.action.value
        category_result = validated_classification.category.value
        confidence = float(validated_classification.confidence_score)
        reason = validated_classification.reason

        result.update({
            "action": action,
            "category": category_result,
            "confidence": confidence,
            "reason": reason
        })

        # Apply via central helper (handles state computation + stamping)
        await _apply_classification(
            location_id=location_id,
            action=action,
            category=category_result,
            confidence=confidence,
            reason=reason,
            dry_run=dry_run,
        )

        result.update({
            "new_state": None,  # state is computed centrally; keep for logs
            "success": True,
        })

        if not dry_run:
            await audit_service.log(
                action_type="verify_locations.classified",
                actor="verify_locations_bot",
                location_id=location_id,
                before=None,
                after={"action": action, "category": category_result, "confidence_score": confidence},
                is_success=True,
                meta={
                    "confidence_threshold": min_confidence
                }
            )

    except Exception as e:
        result["error"] = str(e)
        logger.error("process_location_error", location_id=location_id, error=str(e))
        # Edge: stamp so we don't retry forever in a tight loop
        try:
            if not dry_run:
                await mark_last_verified(location_id, note="skipped by verify_locations: insufficient data or error")
        except Exception:
            pass
    
    return result

async def run_verification(
    limit: int,
    offset: int,
    city: Optional[str],
    source: Optional[str],
    min_confidence: float,
    dry_run: bool,
    model: Optional[str],
    worker_run_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """Main verification logic."""
    classify_service = ClassifyService(model=model)
    last_progress = -1
    
    # Fetch candidates
    candidates = await fetch_candidates(limit=limit, min_confidence=min_confidence)
    
    if not candidates:
        counters: Dict[str, Any] = {
            "total_processed": 0,
            "promoted": 0,
            "skipped": 0,
            "errors": 0,
            "results": []
        }
        if worker_run_id:
            storage_counters = {k: v for k, v in counters.items() if k != "results"}
            await finalize_worker_run(worker_run_id, "finished", 100, storage_counters, None)
        return counters
    
    print(f"[VerifyLocationsBot] Processing {len(candidates)} pending verifications...")
    
    results = []
    promoted = 0
    skipped = 0
    errors = 0
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
            result = await process_location(
                location=location,
                classify_service=classify_service,
                min_confidence=min_confidence,
                dry_run=dry_run
            )
            
            results.append(result)
            
            # Print result
            if result["success"]:
                if result["new_state"] == "VERIFIED":
                    promoted += 1
                    print(f"[PROMOTE] id={result['id']} name={result['name']!r} "
                          f"-> {result['category']} conf={result['confidence']:.2f}")
                elif result["new_state"] == "RETIRED":
                    skipped += 1
                    print(f"[RETIRE] id={result['id']} name={result['name']!r} "
                          f"-> reason={result.get('reason') or 'not_keep_or_low_conf'}")
            else:
                errors += 1
                print(f"[ERROR] id={result['id']} name={result['name']!r} "
                      f"-> {result['error']}")
            await report_progress(idx)
    except Exception as exc:
        if worker_run_id:
            progress_snapshot = last_progress if last_progress >= 0 else 0
            await finalize_worker_run(worker_run_id, "failed", progress_snapshot, None, str(exc))
        raise

    counters = {
        "total_processed": len(candidates),
        "promoted": promoted,
        "skipped": skipped,
        "errors": errors,
        "results": results
    }
    if worker_run_id:
        storage_counters = {k: v for k, v in counters.items() if k != "results"}
        await finalize_worker_run(worker_run_id, "finished", 100, storage_counters, None)
    return counters

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="VerifyLocationsBot — promote PENDING_VERIFICATION to VERIFIED or RETIRED")
    ap.add_argument("--city", help="Filter by city (if supported by schema)")
    ap.add_argument("--source", help="Filter by source (e.g., OSM_OVERPASS, GOOGLE_PLACES)")
    ap.add_argument("--limit", type=int, default=200, help="Max items to process")
    ap.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    ap.add_argument("--chunks", type=int, default=1, help="Total chunks (for sharding)")
    ap.add_argument("--chunk-index", type=int, default=0, help="Which chunk to process (0-based)")
    ap.add_argument("--dry-run", type=int, default=0, help="Dry run mode (1=yes, 0=no)")
    ap.add_argument("--log-json", type=int, default=0, help="Use JSON logging (1=yes, 0=no)")
    ap.add_argument("--min-confidence", type=float, default=0.8, help="Minimum confidence for promotion")
    ap.add_argument("--model", help="Override AI model")
    ap.add_argument("--worker-run-id", type=_parse_worker_run_id, help="UUID van worker_runs record voor progress rapportage")
    return ap.parse_args()

async def main_async():
    t0 = time.perf_counter()
    with with_run_id() as rid:
        logger.info("worker_started")
        args = parse_args()
        worker_run_id: Optional[UUID] = getattr(args, "worker_run_id", None)
        
        # Calculate actual limit and offset based on chunking
        if args.chunks > 1:
            chunk_size = (args.limit + args.chunks - 1) // args.chunks
            actual_offset = args.chunk_index * chunk_size
            actual_limit = min(chunk_size, args.limit - actual_offset)
        else:
            actual_limit = args.limit
            actual_offset = args.offset
        
        print(f"\n[VerifyLocationsBot] Configuration:")
        print(f"  City filter: {args.city or 'none'}")
        print(f"  Source filter: {args.source or 'none'}")
        print(f"  Limit: {actual_limit} (offset: {actual_offset})")
        print(f"  Chunks: {args.chunks} (index: {args.chunk_index})")
        print(f"  Min confidence: {args.min_confidence}")
        print(f"  Dry run: {bool(args.dry_run)}")
        print(f"  Model: {args.model or 'default'}\n")
        
        # Ensure DB pool is ready
        await init_db_pool()
        if worker_run_id:
            await mark_worker_run_running(worker_run_id)
        result = await run_verification(
            limit=actual_limit,
            offset=actual_offset,
            city=args.city,
            source=args.source,
            min_confidence=args.min_confidence,
            dry_run=bool(args.dry_run),
            model=args.model,
            worker_run_id=worker_run_id,
        )
        
        # Summary
        print(f"\n[VerifyLocationsBot] Summary:")
        print(f"  Total processed: {result['total_processed']}")
        print(f"  Promoted to VERIFIED: {result['promoted']}")
        print(f"  Skipped: {result['skipped']}")
        print(f"  Errors: {result['errors']}")
        print(f"  Dry run: {bool(args.dry_run)}")
        
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("worker_finished", 
                   duration_ms=duration_ms,
                   total_processed=result['total_processed'],
                   promoted=result['promoted'],
                   skipped=result['skipped'],
                   errors=result['errors'])

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[VerifyLocationsBot] Interrupted by user.")
    except Exception as e:
        print(f"\n[VerifyLocationsBot] ERROR: {e}")
        raise

if __name__ == "__main__":
    main()
