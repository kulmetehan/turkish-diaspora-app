# app/workers/classify_bot.py
from __future__ import annotations

import argparse
import asyncio
import math
import os
import time
from typing import Optional, Any, Dict

# --- Uniform logging voor workers ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="classify_bot")

# jouw bestaande services (toplevel 'services' package)
from services.db_service import (
    fetch_candidates_for_classification,
    update_location_classification,
)
from services.classify_service import ClassifyService

# Unified AI schema entrypoints via services (met structlog)
from services.ai_validation import validate_classification_payload
from app.models.ai import AIClassification


def _bbox(args):
    # build bbox from center+radius if not explicitly provided
    if all(v is not None for v in (args.lat_min, args.lat_max, args.lng_min, args.lng_max)):
        return args.lat_min, args.lat_max, args.lng_min, args.lng_max
    if all(v is not None for v in (args.center_lat, args.center_lng, args.radius_m)):
        lat_pad = args.radius_m / 111000.0
        lng_pad = args.radius_m / (111000.0 * max(math.cos(math.radians(args.center_lat)), 0.2))
        return args.center_lat - lat_pad, args.center_lat + lat_pad, args.center_lng - lng_pad, args.center_lng + lng_pad
    # default: centrum Rotterdam
    center_lat, center_lng = 51.9244, 4.4777
    return center_lat - 0.02, center_lat + 0.02, center_lng - 0.03, center_lng + 0.03


async def run(limit: int, min_conf: float, dry_run: bool, model: Optional[str], args=None) -> None:
    """
    Batch-classifier:
      - haalt CANDIDATE records op
      - laat LLM classificeren via ClassifyService
      - valideert payload met unified schema (AIClassification)
      - past min_conf toe
      - schrijft resultaat naar DB (tenzij --dry-run)
    """
    svc = ClassifyService(model=model)
    
    # Use new filtering logic if args provided, otherwise fall back to original
    if args:
        from services.db_service import async_engine
        from sqlalchemy import text
        
        lat_min, lat_max, lng_min, lng_max = _bbox(args)
        params = {
            "limit": limit,
            "lat_min": lat_min, "lat_max": lat_max,
            "lng_min": lng_min, "lng_max": lng_max,
        }
        filters = ["state='CANDIDATE'",
                   "(lat BETWEEN :lat_min AND :lat_max)",
                   "(lng BETWEEN :lng_min AND :lng_max)"]
        if args.source:
            filters.append("source = :source")
            params["source"] = args.source
        # Note: city column doesn't exist in current schema, skipping city filter
        # if args.city:
        #     filters.append("lower(city) = lower(:city)")
        #     params["city"] = args.city

        where = " AND ".join(filters)
        sql = f"""
            SELECT id, name, address, category, source, state, lat, lng
            FROM locations
            WHERE {where}
            ORDER BY first_seen_at DESC
            LIMIT :limit
        """
        
        async with async_engine.begin() as conn:
            q = await conn.execute(text(sql), params)
            rows = [dict(r) for r in q.mappings().all()]
    else:
        rows = await fetch_candidates_for_classification(limit=limit)

    if not rows:
        print("No candidates found (state=CANDIDATE & confidence_score IS NULL).")
        return

    keep_cnt = ignore_cnt = skipped_low_conf = 0
    total = 0
    keep_conf_sum = 0.0

    for r in rows:
        total += 1

        # 1) Vraag classificatie op bij de service
        raw_payload, _meta = svc.classify(
            name=r["name"],
            address=r.get("address"),
            typ=r.get("type"),
            location_id=r["id"],
        )

        # 2) Valideer via unified schema (accepteert dict of model)
        if isinstance(raw_payload, AIClassification):
            parsed = raw_payload
        else:
            # best-effort dict
            if hasattr(raw_payload, "model_dump"):
                raw_dict: Dict[str, Any] = raw_payload.model_dump()  # type: ignore[attr-defined]
            else:
                raw_dict = dict(raw_payload) if isinstance(raw_payload, dict) else {"__raw__": raw_payload}
            parsed = validate_classification_payload(raw_dict)

        # 3) Gebruik enums veilig (.value) en min_conf-drempel
        action = parsed.action.value
        category = parsed.category.value
        conf = float(parsed.confidence_score or 0.0)

        if conf < min_conf:
            skipped_low_conf += 1
            print(
                f"[skip <{min_conf:.2f}] id={r['id']} name={r['name']!r} "
                f"-> {action}/{category} conf={conf:.2f}"
            )
            continue

        if action == "keep":
            keep_cnt += 1
            keep_conf_sum += conf
        elif action == "ignore":
            ignore_cnt += 1

        print(f"[apply] id={r['id']} -> action={action} category={category} conf={conf:.2f}")

        # 4) Persist (tenzij dry-run)
        if not dry_run:
            await update_location_classification(
                id=r["id"],
                action=action,
                category=category,
                confidence_score=conf,
                reason=parsed.reason,
            )

    avg_keep_conf = (keep_conf_sum / keep_cnt) if keep_cnt else 0.0
    print(
        f"\nSummary: classified={total}  keep={keep_cnt}  ignore={ignore_cnt}  "
        f"skipped_low_conf={skipped_low_conf} avg_conf(keep)={avg_keep_conf:.2f}  dry_run={dry_run}"
    )


def main():
    t0 = time.perf_counter()
    with with_run_id() as rid:
        logger.info("worker_started")
        p = argparse.ArgumentParser(description="Batch classify candidates")
        p.add_argument("--limit", type=int, default=50, help="Max items to classify")

        default_conf = float(os.getenv("CLASSIFY_MIN_CONF", "0.80"))
        p.add_argument(
            "--min-confidence",
            type=float,
            default=default_conf,
            help="Minimale confidence score (0..1)"
        )

        p.add_argument("--dry-run", action="store_true", help="Don't write to DB")
        p.add_argument("--model", type=str, default=None, help="Override model name")
        
        # NEW filters
        p.add_argument("--source", type=str, help="Filter by source (e.g. OSM_OVERPASS, GOOGLE_PLACES)")
        p.add_argument("--city", type=str, help="Filter by city")
        p.add_argument("--lat-min", type=float)
        p.add_argument("--lat-max", type=float)
        p.add_argument("--lng-min", type=float)
        p.add_argument("--lng-max", type=float)
        p.add_argument("--center-lat", type=float)
        p.add_argument("--center-lng", type=float)
        p.add_argument("--radius-m", type=float)
        args = p.parse_args()

        asyncio.run(run(args.limit, args.min_confidence, args.dry_run, args.model, args))
        
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("worker_finished", duration_ms=duration_ms)


if __name__ == "__main__":
    main()
