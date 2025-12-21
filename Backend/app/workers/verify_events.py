"""
Verify Events Bot

Automatically classifies and promotes events_candidate records based on AI classification.
Similar to verify_locations.py but for events.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import UUID

# Load environment variables
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)

# Pathing
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent
BACKEND_DIR = APP_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.db_service import init_db_pool, fetch, execute
from services.event_classification_service import EventClassificationService
from services.event_candidate_service import update_event_candidate_state
from services.audit_service import audit_service
from app.models.ai import AIQuotaExceededError, AIEventClassification
from app.models.event_categories import EventCategory
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    update_worker_run_progress,
    finish_worker_run,
)

configure_logging(service_name="worker")
logger = get_logger().bind(worker="verify_events")


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


async def fetch_candidate_events(
    *,
    limit: int,
    min_confidence: float = 0.80,
) -> List[Dict[str, Any]]:
    """Fetch candidate events that need classification."""
    rows = await fetch(
        """
        SELECT
            ec.id,
            ec.event_raw_id,
            ec.title,
            ec.description,
            ec.location_text,
            ec.source_key,
            ec.state,
            ec.duplicate_of_id
        FROM events_candidate ec
        WHERE ec.state = 'candidate'
          AND ec.duplicate_of_id IS NULL
        ORDER BY ec.created_at ASC
        LIMIT $1
        """,
        max(0, int(limit)),
    )
    return [dict(row) for row in rows or []]


async def process_event(
    event: Dict[str, Any],
    classify_service: EventClassificationService,
    min_confidence: float,
    dry_run: bool,
) -> Dict[str, Any]:
    """Process a single event through classification."""
    event_id = event["id"]
    title = event["title"]
    description = event.get("description")
    location_text = event.get("location_text")
    source_key = event.get("source_key")
    
    result = {
        "id": event_id,
        "title": title,
        "old_state": event["state"],
        "new_state": None,
        "action": None,
        "category": None,
        "confidence": None,
        "reason": None,
        "success": False,
        "error": None,
    }
    
    try:
        # 1. Classify using EventClassificationService
        classification_result, meta = classify_service.classify_event(
            title=title,
            description=description,
            location_text=location_text,
            source_key=source_key,
            event_raw_id=event.get("event_raw_id"),
        )
        
        # 2. Validate - classification_result is already AIEventClassification
        # No need for validate_classification_payload since we're using AIEventClassification directly
        action = classification_result.action.value
        category = classification_result.category.value if classification_result.category else None
        confidence = float(classification_result.confidence_score)
        reason = classification_result.reason
        
        result.update({
            "action": action,
            "category": category,
            "confidence": confidence,
            "reason": reason,
        })
        
        # 3. Determine new state based on action and confidence
        if action == "keep" and confidence >= min_confidence:
            new_state = "verified"
            result["new_state"] = new_state
            
            if not dry_run:
                await update_event_candidate_state(
                    candidate_id=event_id,
                    new_state=new_state,
                    actor_email="verify_events_bot",
                    event_category=category,  # Save event_category when promoting to verified
                )
                
                await audit_service.log(
                    action_type="verify_events.classified",
                    actor="verify_events_bot",
                    location_id=None,  # Events don't have location_id, use meta instead
                    before={"state": event["state"]},
                    after={
                        "state": new_state,
                        "action": action,
                        "category": category,
                        "confidence_score": confidence,
                    },
                    is_success=True,
                    meta={
                        "event_candidate_id": event_id,
                        "reason": reason,
                        "classification_meta": meta,
                    },
                )
            
            result["success"] = True
            logger.info(
                "event_verified",
                event_id=event_id,
                title=title[:50],
                action=action,
                category=category,
                confidence=confidence,
                new_state=new_state,
            )
        else:
            # Keep in candidate state (or could reject if action=ignore and very low confidence)
            result["new_state"] = event["state"]  # No change
            result["success"] = True
            logger.info(
                "event_kept_candidate",
                event_id=event_id,
                title=title[:50],
                action=action,
                confidence=confidence,
                reason="below threshold or ignore",
            )
            
    except AIQuotaExceededError:
        raise
    except Exception as e:
        result["error"] = str(e)
        logger.error("process_event_error", event_id=event_id, error=str(e))
    
    return result


async def run_verification(
    limit: int,
    offset: int,
    min_confidence: float,
    dry_run: bool,
    model: Optional[str],
    worker_run_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """Main verification logic."""
    await init_db_pool()
    
    classify_service = EventClassificationService(model=model)
    
    events = await fetch_candidate_events(limit=limit, min_confidence=min_confidence)
    
    if not events:
        logger.info("verify_events_no_candidates")
        return {
            "processed": 0,
            "verified": 0,
            "kept_candidate": 0,
            "errors": 0,
        }
    
    verified = 0
    kept_candidate = 0
    errors = 0
    
    for idx, event in enumerate(events, start=1):
        if worker_run_id:
            progress = min(99, int(idx * 100 / len(events)))
            await update_worker_run_progress(worker_run_id, progress)
        
        try:
            result = await process_event(
                event=event,
                classify_service=classify_service,
                min_confidence=min_confidence,
                dry_run=dry_run,
            )
            
            if result.get("success"):
                if result.get("new_state") == "verified":
                    verified += 1
                    print(f"[VERIFIED] id={result['id']} {result['title'][:50]} → {result['category']} (conf={result['confidence']:.2f})")
                else:
                    kept_candidate += 1
                    print(f"[KEEP CANDIDATE] id={result['id']} {result['title'][:50]} → {result['action']} (conf={result['confidence']:.2f})")
            else:
                errors += 1
                print(f"[ERROR] id={result['id']} {result.get('error', 'unknown')}")
                
        except AIQuotaExceededError:
            logger.error("verify_events_quota_exceeded")
            raise
        except Exception as e:
            errors += 1
            logger.error("verify_events_processing_error", event_id=event.get("id"), error=str(e))
    
    return {
        "processed": len(events),
        "verified": verified,
        "kept_candidate": kept_candidate,
        "errors": errors,
    }


async def main_async() -> int:
    parser = argparse.ArgumentParser(description="Verify Events Bot — classify and promote events.")
    parser.add_argument("--limit", type=int, default=200, help="Max events to process.")
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination.")
    parser.add_argument("--min-confidence", type=float, default=0.80, help="Min confidence for verification.")
    parser.add_argument("--dry-run", type=int, default=0, help="1=dry run, 0=real writes.")
    parser.add_argument("--model", type=str, default=None, help="OpenAI model override.")
    parser.add_argument("--worker-run-id", type=_parse_worker_run_id, default=None, help="Worker run UUID.")
    
    args = parser.parse_args()
    
    with with_run_id():
        run_id = args.worker_run_id or await start_worker_run(
            bot="verify_events",
            city=None,
            category=None,
        )
        await mark_worker_run_running(run_id)
        
        try:
            stats = await run_verification(
                limit=args.limit,
                offset=args.offset,
                min_confidence=args.min_confidence,
                dry_run=bool(args.dry_run),
                model=args.model,
                worker_run_id=run_id,
            )
            
            await finish_worker_run(run_id, "finished", 100, stats, None)
            logger.info("verify_events_complete", **stats)
            return 0
        except Exception as exc:
            await finish_worker_run(run_id, "failed", 0, None, str(exc))
            logger.error("verify_events_failed", error=str(exc))
            return 1


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

