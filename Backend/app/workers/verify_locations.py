# -*- coding: utf-8 -*-
"""
VerifyLocationsBot — Classify and promote CANDIDATE locations to VERIFIED
- Fetches CANDIDATE rows from locations table
- Classifies each using existing ClassifyService
- Validates using existing AI validation
- Promotes eligible rows to VERIFIED state
- Logs all actions via AuditService

Usage:
    python -m app.workers.verify_locations --city rotterdam --limit 200 --dry-run 0
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# Load environment variables from .env file
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)

# --- Uniform logging ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="verify_locations")

# ---------------------------------------------------------------------------
# Pathing zodat 'app.*' en 'services.*' werken
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent           # .../Backend/app
BACKEND_DIR = APP_DIR.parent                # .../Backend

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))    # .../Backend

# ---------------------------------------------------------------------------
# DB (async)
# ---------------------------------------------------------------------------
def _resolve_database_url() -> str:
    for key in ("DATABASE_URL", "DB_URL"):
        v = os.getenv(key)
        if v:
            return v
    try:
        from app.config import settings  # type: ignore
        for attr in ("DATABASE_URL", "database_url", "DB_URL"):
            if hasattr(settings, attr):
                val = getattr(settings, attr)
                if isinstance(val, str) and val:
                    return val
    except Exception:
        pass
    try:
        from app.config import Config  # type: ignore
        for attr in ("DATABASE_URL", "database_url", "DB_URL"):
            if hasattr(Config, attr):
                val = getattr(Config, attr)
                if isinstance(val, str) and val:
                    return val
    except Exception:
        pass
    raise RuntimeError("DATABASE_URL ontbreekt (env of config).")

DATABASE_URL = _resolve_database_url()
def _normalize_database_url(raw: str) -> str:
    s = (raw or "").strip().strip('"').strip("'")
    if not s:
        raise RuntimeError("DATABASE_URL is empty")
    if s.startswith("postgresql://"):
        s = s.replace("postgresql://", "postgresql+asyncpg://", 1)
    u = urlparse(s)
    q = dict(parse_qsl(u.query, keep_blank_values=True))
    if "sslmode" in q:
        q.pop("sslmode", None)
        q["ssl"] = "true"
    if ("pooler.supabase.com" in (u.hostname or "")) and "ssl" not in q:
        q["ssl"] = "true"
    return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(q), u.fragment))

DATABASE_URL = _normalize_database_url(DATABASE_URL)

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.pool import NullPool

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    poolclass=NullPool,
)
Session = async_sessionmaker(engine, expire_on_commit=False)

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
    limit: int,
    offset: int = 0,
    city: Optional[str] = None,
    source: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Fetch CANDIDATE locations that need verification."""
    filters = ["state = 'CANDIDATE'", "is_retired = false"]
    params = {"limit": limit, "offset": offset}
    
    if city:
        # Note: city column may not exist in current schema, so we'll skip this filter
        # filters.append("LOWER(city) = LOWER(:city)")
        # params["city"] = city
        pass
    
    if source:
        filters.append("source = :source")
        params["source"] = source
    
    where_clause = " AND ".join(filters)
    
    sql = text(f"""
        SELECT id, name, address, category, source, state, lat, lng, 
               confidence_score, first_seen_at, last_seen_at
        FROM locations
        WHERE {where_clause}
        ORDER BY first_seen_at ASC
        LIMIT :limit OFFSET :offset
    """)
    
    async with engine.begin() as conn:
        result = await conn.execute(sql, params)
        rows = result.mappings().all()
        return [dict(row) for row in rows]

async def update_location_to_verified(
    location_id: int,
    category: str,
    confidence_score: float,
    reason: Optional[str] = None,
    dry_run: bool = False
) -> bool:
    """Update location to VERIFIED state with audit logging."""
    if dry_run:
        return True
    
    now = datetime.now(timezone.utc)
    
    # Update the location
    update_sql = text("""
        UPDATE locations
        SET 
            state = 'VERIFIED',
            category = :category,
            confidence_score = :confidence_score,
            last_verified_at = :last_verified_at
        WHERE id = :id
    """)
    
    params = {
        "id": location_id,
        "category": category,
        "confidence_score": confidence_score,
        "last_verified_at": now
    }
    
    async with engine.begin() as conn:
        result = await conn.execute(update_sql, params)
        return result.rowcount > 0

async def retire_location(
    location_id: int,
    reason: Optional[str] = None,
    dry_run: bool = False
) -> bool:
    """Mark a location as retired and annotate notes; noop when dry_run."""
    if dry_run:
        return True
    now = datetime.now(timezone.utc)
    sql = text(
        """
        UPDATE locations
        SET is_retired = true,
            last_verified_at = :now,
            notes = COALESCE(notes, '') || :suffix
        WHERE id = :id
        """
    )
    params = {
        "id": location_id,
        "now": now,
        "suffix": f"\nretired: {reason or 'not_turkish'} @ {now.isoformat()}"
    }
    async with engine.begin() as conn:
        res = await conn.execute(sql, params)
        return res.rowcount > 0

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
        
        # 3. Check if eligible for promotion (Turkish-only enforcement)
        if action == "keep" and confidence >= min_confidence:
            # Update to VERIFIED (only Turkish businesses)
            success = await update_location_to_verified(
                location_id=location_id,
                category=category_result,
                confidence_score=confidence,
                reason=reason,
                dry_run=dry_run
            )
            
            if success:
                result.update({
                    "new_state": "VERIFIED",
                    "success": True
                })
                
                # Log audit entry
                if not dry_run:
                    await audit_service.log(
                        action_type="verify_locations.promote",
                        actor="verify_locations_bot",
                        location_id=location_id,
                        before={"state": "CANDIDATE"},
                        after={"state": "VERIFIED", "category": category_result, "confidence_score": confidence},
                        is_success=True,
                        meta={
                            "classification_result": classification_result.model_dump(),
                            "confidence_threshold": min_confidence,
                            "turkish_verification": "enforced"
                        }
                    )
            else:
                result["error"] = "Failed to update location"
        else:
            # Not eligible for promotion
            if action != "keep":
                # Retire clear non-Turkish candidates to reduce backlog noise
                retired = await retire_location(location_id, reason="not_turkish", dry_run=dry_run)
                result["new_state"] = "CANDIDATE"
                result["reason"] = "Not Turkish business"
                result["success"] = retired or result["success"]

                # Audit
                if not dry_run:
                    await audit_service.log(
                        action_type="verify_locations.retire_not_turkish",
                        actor="verify_locations_bot",
                        location_id=location_id,
                        before={"state": "CANDIDATE"},
                        after={"state": "CANDIDATE", "retired": True},
                        is_success=True,
                        meta={
                            "classification_result": classification_result.model_dump(),
                            "reason": "not_turkish"
                        }
                    )
            else:
                result["new_state"] = "CANDIDATE"  # Keep as candidate
                result["reason"] = f"Confidence {confidence:.2f} < {min_confidence:.2f}"
            
            result["success"] = True  # Processing succeeded, just not promoted
            
    except Exception as e:
        result["error"] = str(e)
        logger.error("process_location_error", location_id=location_id, error=str(e))
    
    return result

async def run_verification(
    limit: int,
    offset: int,
    city: Optional[str],
    source: Optional[str],
    min_confidence: float,
    dry_run: bool,
    model: Optional[str]
) -> Dict[str, Any]:
    """Main verification logic."""
    classify_service = ClassifyService(model=model)
    
    # Fetch candidates
    candidates = await fetch_candidates(
        limit=limit,
        offset=offset,
        city=city,
        source=source
    )
    
    if not candidates:
        return {
            "total_processed": 0,
            "promoted": 0,
            "skipped": 0,
            "errors": 0,
            "results": []
        }
    
    print(f"[VerifyLocationsBot] Processing {len(candidates)} candidates...")
    
    results = []
    promoted = 0
    skipped = 0
    errors = 0
    
    for location in candidates:
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
            else:
                skipped += 1
                print(f"[SKIP] id={result['id']} name={result['name']!r} "
                      f"-> {result['reason']}")
        else:
            errors += 1
            print(f"[ERROR] id={result['id']} name={result['name']!r} "
                  f"-> {result['error']}")
    
    return {
        "total_processed": len(candidates),
        "promoted": promoted,
        "skipped": skipped,
        "errors": errors,
        "results": results
    }

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="VerifyLocationsBot — classify and promote CANDIDATE locations")
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
    return ap.parse_args()

async def main_async():
    t0 = time.perf_counter()
    with with_run_id() as rid:
        logger.info("worker_started")
        args = parse_args()
        
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
        
        result = await run_verification(
            limit=actual_limit,
            offset=actual_offset,
            city=args.city,
            source=args.source,
            min_confidence=args.min_confidence,
            dry_run=bool(args.dry_run),
            model=args.model
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
