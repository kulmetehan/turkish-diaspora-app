# app/workers/classify_bot.py
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from typing import Optional, Any, Dict
from uuid import UUID

# --- Uniform logging voor workers ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="classify_bot")

"""
STATE MACHINE (canonical):
- CANDIDATE: raw discovered location, unreviewed.
- PENDING_VERIFICATION: AI thinks it's Turkish (confidence >=0.80) but not yet promoted.
- VERIFIED: approved and visible in the app.
- RETIRED: explicitly considered not relevant / no longer valid.
Only VERIFIED locations are sent to the frontend.
"""

# jouw bestaande services (toplevel 'services' package)
from services.db_service import (
    fetch_candidates_for_classification,
    update_location_classification,
    execute,
)
from services.classify_service import ClassifyService

# Unified AI schema entrypoints via services (met structlog)
from services.ai_validation import validate_classification_payload
from app.models.ai import AIClassification

# Worker run tracking
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

# ---- Category normalization helpers ----
# Map raw model outputs / heuristics to our canonical categories.
# Keys should all be lowercase.
CATEGORY_NORMALIZATION_MAP = {
    # --- BUTCHER / MEAT SHOPS ---
    "butcher": "butcher",
    "butchery": "butcher",
    "halal butcher": "butcher",
    "halal butchery": "butcher",
    "slager": "butcher",
    "slagerij": "butcher",
    "vleeshandel": "butcher",
    # Turkish variants
    "kasap": "butcher",
    "kasaplar": "butcher",
    "etçi": "butcher",
    "etci": "butcher",
    "et dükkânı": "butcher",
    "et dukkanı": "butcher",
    "et dukkani": "butcher",
    "et market": "butcher",

    # --- SUPERMARKET / GROCERY / BAKKAL ---
    "supermarket": "supermarket",
    "supermarkt": "supermarket",
    "supermarkt (halal)": "supermarket",
    "market": "supermarket",
    "mini market": "supermarket",
    "minimarket": "supermarket",
    "mini-market": "supermarket",
    "grocery": "supermarket",
    "grocery store": "supermarket",
    "halal shop": "supermarket",
    "halal supermarkt": "supermarket",
    "bakkal": "supermarket",
    "şarküteri": "supermarket",
    "sarkuteri": "supermarket",
    "gıda": "supermarket",
    "gida": "supermarket",

    # --- BAKERY / PATISSERIE ---
    "bakery": "bakery",
    "baker": "bakery",
    "bakkerij": "bakery",
    "patisserie": "bakery",
    "pâtisserie": "bakery",
    "baklava shop": "bakery",
    "baklava": "bakery",
    "baklavacı": "bakery",
    "baklavaci": "bakery",
    "simitçi": "bakery",
    "simitci": "bakery",
    "simit bakery": "bakery",
    "pastane": "bakery",
    "pasta & börek": "bakery",
    "börekçi": "bakery",
    "borekci": "bakery",
    "börek": "bakery",
    "borek": "bakery",

    # --- RESTAURANT / EATERY ---
    "restaurant": "restaurant",
    "grill": "restaurant",
    "grillroom": "restaurant",
    "kebab": "restaurant",
    "kebap": "restaurant",
    "doner": "restaurant",
    "döner": "restaurant",
    "doner kebab": "restaurant",
    "shawarma": "restaurant",
    "pide salonu": "restaurant",
    "pide": "restaurant",
    "lahmacun": "restaurant",
    "ocakbaşı": "restaurant",
    "ocakbasi": "restaurant",
    "meze bar": "restaurant",
    "lokanta": "restaurant",
    "sofrasi": "restaurant",
    "sofrası": "restaurant",
    "antep cuisine": "restaurant",
    "gaziantep cuisine": "restaurant",
    "adana grill": "restaurant",
    "adana kebap": "restaurant",
    "bakery & restaurant": "restaurant",

    # --- BARBER / HAIR ---
    "barbershop": "barber",
    "barber": "barber",
    "barber shop": "barber",
    "barbier": "barber",
    "kapper": "barber",
    "kappers": "barber",
    "kapsalon": "barber",
    "hairdresser": "barber",
    "hair salon": "barber",
    "salon": "barber",
    # Turkish
    "berber": "barber",
    "kuaför": "barber",
    "kuafor": "barber",
    "erkek kuaförü": "barber",
    "erkek kuaforu": "barber",
    "bayan kuaförü": "barber",
    "bayan kuaforu": "barber",

    # --- MOSQUE / RELIGIOUS / COMMUNITY ---
    "mosque": "mosque",
    "masjid": "mosque",
    "camii": "mosque",
    "cami": "mosque",
    "moskee": "mosque",
    "islamitisch centrum": "mosque",
    "islamic center": "mosque",
    "diyanet": "mosque",
    "alevi cultural center": "mosque",
    "cemevi": "mosque",
    "alevi gemeenschap": "mosque",
    "kulturzentrum": "mosque",

    # --- TRAVEL AGENCY / TICKETS ---
    "travel agency": "travel_agency",
    "reisbureau": "travel_agency",
    "reis kantoor": "travel_agency",
    "reizbüro": "travel_agency",
    "uçak bileti": "travel_agency",
    "bilet acentası": "travel_agency",
    "bilet acentasi": "travel_agency",
    "acente": "travel_agency",
    "acenta": "travel_agency",

    # fallback
    "other": "other",
}

def normalize_category(raw_cat: str) -> str:
    """
    Take a raw category guess from the AI ("butcher", "kasap", "berber", etc)
    and normalize it using CATEGORY_NORMALIZATION_MAP.
    If we don't know it, just pass it through lowercase.
    If it's empty/None, return "other".
    """
    if not raw_cat:
        return "other"
    key = raw_cat.strip().lower()
    mapped = CATEGORY_NORMALIZATION_MAP.get(key)
    if mapped:
        return mapped
    # not in map, just use the model's lowercase guess
    return key


def should_force_promote(row: dict, auto_promote_conf: float = 0.90) -> Optional[dict]:
    diaspora_cats = {"bakery", "butcher", "barber", "mosque", "supermarket", "restaurant", "travel_agency"}
    state = str(row.get("state") or "")
    conf = row.get("confidence_score")
    is_retired = row.get("is_retired")
    category_raw = row.get("category") or ""
    normalized_category = normalize_category(category_raw)

    if state not in ("PENDING_VERIFICATION", "CANDIDATE"):
        return None
    try:
        if conf is None or float(conf) < float(auto_promote_conf):
            return None
    except Exception:
        return None
    if is_retired is True:
        return None
    if normalized_category not in diaspora_cats:
        return None

    text = f"{row.get('name') or ''} \n {row.get('notes') or ''}"
    low = text.lower()
    turkish_hits = [
        "turk", "turks", "turkse", "diyanet", "ulu", "cami", "camii", "moskee", "islamitisch centrum", "islamic center", "cemevi", "alevi",
        "simit", "firin", "firini", "kapadokya", "avrasya", "tetik", "korfez", "usta", "anadolu", "yufka", "saray", "öz", "oz"
    ]
    if any(k in low for k in turkish_hits):
        return {
            "action": "keep",
            "category": normalized_category,
            "confidence": float(conf),
            "reason": "auto-promotion: high score + turkish heuristic",
        }
    return None


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


def classify_location_with_ai(*, name: str, address: str, existing_category: str, model: Optional[str]) -> Dict[str, Any]:
    svc = ClassifyService(model=model)
    raw_payload, _meta = svc.classify(
        name=name,
        address=address,
        typ=existing_category,
        location_id=None,
    )

    # Prefer validated model, but gracefully fallback if enum mismatches (e.g., 'barber', 'kasap').
    try:
        if isinstance(raw_payload, AIClassification):
            parsed = raw_payload
        else:
            if hasattr(raw_payload, "model_dump"):
                raw_dict: Dict[str, Any] = raw_payload.model_dump()  # type: ignore[attr-defined]
            else:
                raw_dict = dict(raw_payload) if isinstance(raw_payload, dict) else {"__raw__": raw_payload}
            parsed = validate_classification_payload(raw_dict)
        action = parsed.action.value
        category = parsed.category.value
        confidence = float(parsed.confidence_score or 0.0)
        reason = parsed.reason or ""
        return {"action": action, "category": category, "confidence": confidence, "reason": reason}
    except Exception:
        # Fallback: extract best-effort fields without enforcing enum
        if isinstance(raw_payload, dict):
            raw_dict = raw_payload
        elif hasattr(raw_payload, "model_dump"):
            raw_dict = raw_payload.model_dump()  # type: ignore[attr-defined]
        else:
            raw_dict = {}
        action = str(raw_dict.get("action", "ignore")).lower()
        category = str(raw_dict.get("category", "other"))
        confidence = float(raw_dict.get("confidence_score") or raw_dict.get("confidence") or 0.0)
        reason = str(raw_dict.get("reason") or "")
        return {"action": action, "category": category, "confidence": confidence, "reason": reason}


async def run(
    limit: int,
    min_conf: float,
    dry_run: bool,
    model: str,
    args,
    worker_run_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """
    Batch-classifier:
      - haalt CANDIDATE records op
      - laat LLM classificeren via ClassifyService
      - valideert payload met unified schema (AIClassification)
      - past min_conf toe
      - schrijft resultaat naar DB (tenzij --dry-run)
    """
    svc = ClassifyService(model=model)
    last_progress = -1
    if worker_run_id:
        await mark_worker_run_running(worker_run_id)
    
    # Use new filtering logic if args provided, otherwise fall back to original
    if args:
        from services.db_service import fetch

        lat_min, lat_max, lng_min, lng_max = _bbox(args)
        filters = [
            "state = 'CANDIDATE'",
            "(lat BETWEEN $1 AND $2)",
            "(lng BETWEEN $3 AND $4)",
        ]
        params = [lat_min, lat_max, lng_min, lng_max]

        if getattr(args, "source", None):
            filters.append("source = $5")
            params.append(args.source)

        where_sql = " AND ".join(filters)

        limit_param_index = len(params) + 1
        params.append(limit)

        sql = f"""
            SELECT id, name, address, category, source, state, lat, lng, confidence_score, is_retired, notes
            FROM locations
            WHERE {where_sql}
            ORDER BY first_seen_at DESC
            LIMIT ${limit_param_index}
        """

        raw_rows = await fetch(sql, *params)
        rows = [dict(r) for r in raw_rows]
    else:
        # Fallback: pull recent candidates/pending with required fields
        from services.db_service import fetch as _fetch
        sql = (
            """
            SELECT id, name, address, category, source, state, lat, lng, confidence_score, is_retired, notes
            FROM locations
            WHERE state IN ('CANDIDATE','PENDING_VERIFICATION')
            ORDER BY first_seen_at DESC
            LIMIT $1
            """
        )
        raw_rows = await _fetch(sql, limit)
        rows = [dict(r) for r in raw_rows]

    if not rows:
        print("No candidates found (state=CANDIDATE & confidence_score IS NULL).")
        counters: Dict[str, Any] = {
            "classified": 0,
            "keep": 0,
            "ignore": 0,
            "skipped_low_conf": 0,
            "autopromoted": 0,
        }
        if worker_run_id:
            await finish_worker_run(worker_run_id, "finished", 100, counters, None)
        return counters

    keep_cnt = ignore_cnt = skipped_low_conf = 0
    autopromoted_cnt = 0
    total_processed = 0
    keep_conf_sum = 0.0
    total_rows = len(rows)

    async def report_progress(current_index: int) -> None:
        nonlocal last_progress
        if not worker_run_id or total_rows <= 0:
            return
        percent = min(99, max(0, int((current_index * 100) / total_rows)))
        if percent != last_progress:
            await update_worker_run_progress(worker_run_id, percent)
            last_progress = percent

    try:
        for idx, r in enumerate(rows, start=1):
            total_processed = idx

            name = r.get("name") or ""
            address = r.get("address") or ""
            existing_cat = r.get("category") or r.get("type") or ""

            # Auto-promotion path before LLM
            promo = should_force_promote(r)
            if promo:
                autopromoted_cnt += 1
                print(f"[autopromote] id={r['id']} name='{name}' -> category={promo['category']} conf={promo['confidence']:.2f}")
                if not dry_run:
                    await update_location_classification(
                        id=r["id"],
                        action="keep",
                        category=promo["category"],
                        confidence_score=promo["confidence"],
                        reason=promo["reason"],
                    )
                await report_progress(idx)
                continue

            result = classify_location_with_ai(
                name=name,
                address=address,
                existing_category=existing_cat,
                model=model,
            )

            action = result["action"]
            raw_category = result["category"]
            final_category = normalize_category(raw_category)
            conf = float(result["confidence"])

            if conf < min_conf:
                skipped_low_conf += 1
                print(
                    f"[skip <{min_conf:.2f}] id={r['id']} name={r['name']!r} "
                    f"-> {action}/{final_category} conf={conf:.2f}"
                )
                await report_progress(idx)
                continue

            if action == "keep":
                keep_cnt += 1
                keep_conf_sum += conf
            elif action == "ignore":
                ignore_cnt += 1

            print(f"[apply] id={r['id']} -> action={action} category={final_category} conf={conf:.2f}")

            # 4) Persist (tenzij dry-run)
            if not dry_run:
                await update_location_classification(
                    id=r["id"],
                    action=action,
                    category=final_category,
                    confidence_score=conf,
                    reason=result.get("reason", ""),
                )
            await report_progress(idx)
    except Exception as exc:
        if worker_run_id:
            progress_snapshot = last_progress if last_progress >= 0 else 0
            await finish_worker_run(worker_run_id, "failed", progress_snapshot, None, str(exc))
        raise

    avg_keep_conf = (keep_conf_sum / keep_cnt) if keep_cnt else 0.0
    print(
        f"\nSummary: classified={total_processed}  keep={keep_cnt}  ignore={ignore_cnt}  "
        f"skipped_low_conf={skipped_low_conf} avg_conf(keep)={avg_keep_conf:.2f}  dry_run={dry_run}"
    )
    counters = {
        "classified": total_processed,
        "keep": keep_cnt,
        "ignore": ignore_cnt,
        "skipped_low_conf": skipped_low_conf,
        "autopromoted": autopromoted_cnt,
        "avg_keep_conf": avg_keep_conf,
    }

    if worker_run_id:
        await finish_worker_run(worker_run_id, "finished", 100, counters, None)

    return counters


async def main_async():
    t0 = time.perf_counter()
    with with_run_id() as rid:
        logger.info("worker_started")
        p = argparse.ArgumentParser(description="Batch classify candidates")
        p.add_argument("--limit", type=int, default=50, help="Max items to classify")

        # Pre-parse to check if --min-confidence was explicitly provided
        pre_args, _ = p.parse_known_args()
        explicit_min_conf = hasattr(pre_args, 'min_confidence') and '--min-confidence' in sys.argv
        
        # Default: try config, then env, then hard-coded
        default_conf = 0.80
        if not explicit_min_conf:
            try:
                from services.db_service import init_db_pool
                from services.ai_config_service import get_threshold_for_bot
                await init_db_pool()
                config_threshold = await get_threshold_for_bot("classify_bot")
                if config_threshold is not None:
                    default_conf = config_threshold
                else:
                    env_val = os.getenv("CLASSIFY_MIN_CONF")
                    if env_val:
                        default_conf = float(env_val)
            except Exception as e:
                logger.warning("failed_to_load_config", error=str(e), fallback_to_env=True)
                env_val = os.getenv("CLASSIFY_MIN_CONF")
                if env_val:
                    default_conf = float(env_val)
        
        p.add_argument(
            "--min-confidence",
            type=float,
            default=default_conf,
            help="Minimale confidence score (0..1). Precedence: CLI > config > env > default"
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
        p.add_argument("--worker-run-id", type=_parse_worker_run_id, help="UUID van worker_runs record voor progress rapportage")
        args = p.parse_args()

        worker_run_id: Optional[UUID] = getattr(args, "worker_run_id", None)
        
        # Auto-create worker_run if not provided
        if not worker_run_id:
            from services.db_service import init_db_pool
            await init_db_pool()
            worker_run_id = await start_worker_run(bot="classify_bot", city=getattr(args, "city", None), category=None)
        
        await run(
            args.limit,
            args.min_confidence,
            args.dry_run,
            args.model,
            args,
            worker_run_id,
        )
        
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("worker_finished", duration_ms=duration_ms)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
