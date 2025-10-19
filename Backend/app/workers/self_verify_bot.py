# Backend/app/workers/self_verify_bot.py
# Self-Verifying AI Loop (classify + verify/enrich + promote)
from __future__ import annotations

import argparse
import asyncio
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

# --- Logging zoals in jullie workers ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger().bind(worker="self_verify_bot")

# --- OpenAI service: bij jou staat die onder /Backend/services/openai_service.py ---
OpenAIService = None  # type: ignore
try:
    from services.openai_service import OpenAIService as _OAS  # type: ignore
    OpenAIService = _OAS
except Exception:
    pass
if OpenAIService is None:
    raise RuntimeError("services.openai_service.OpenAIService niet gevonden (verwacht /Backend/services/openai_service.py)")

# --- DB service: bij jou onder /Backend/services/db_service.py ---
db_upsert_location_state = None
async_engine = None
try:
    from services.db_service import upsert_location_state as db_upsert_location_state  # type: ignore
except Exception:
    pass
try:
    from services.db_service import async_engine as _engine  # type: ignore
    async_engine = _engine
except Exception:
    raise RuntimeError("services.db_service.async_engine niet gevonden")

# --- Optionele metrics (TDA-20) ---
metrics_service = None
try:
    from services import metrics_service as _metrics  # type: ignore
    metrics_service = _metrics
except Exception:
    pass

# --- Unified AI schema’s met robuuste fallbacks ---
AIClassification = None
AIVerificationResult = None
try:
    from app.models.ai import AIClassification as _AIC  # type: ignore
    AIClassification = _AIC
except Exception:
    try:
        from models.ai import AIClassification as _AIC2  # type: ignore
        AIClassification = _AIC2
    except Exception:
        from pydantic import BaseModel
        class _AIC3(BaseModel):
            action: str
            category: Optional[str] = None
            confidence_score: float
            reason: Optional[str] = None
        AIClassification = _AIC3

try:
    from app.models.ai import AIVerificationResult as _AIV  # type: ignore
    AIVerificationResult = _AIV
except Exception:
    try:
        from models.ai import AIVerificationResult as _AIV2  # type: ignore
        AIVerificationResult = _AIV2
    except Exception:
        from pydantic import BaseModel
        class _AIV3(BaseModel):
            confidence_score: float
            website: Optional[str] = None
            rating: Optional[float] = None
            user_ratings_total: Optional[int] = None
            business_status: Optional[str] = None
            evidence_urls: Optional[list[str]] = None
            reason: Optional[str] = None
        AIVerificationResult = _AIV3

from sqlalchemy import text

# -------------------------
# Config via .env
# -------------------------
DEFAULT_CONF = float(os.getenv("SELF_VERIFY_CONF_MIN", "0.80"))
DEFAULT_LIMIT = int(os.getenv("SELF_VERIFY_BATCH_LIMIT", "200"))
DEFAULT_CONC = int(os.getenv("SELF_VERIFY_CONCURRENCY", "5"))
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# -------------------------
# SQL fallbacks
# -------------------------
SELECT_CANDIDATES_SQL = """
SELECT id, name, address, category, confidence_score, state
FROM locations
WHERE state = 'CANDIDATE'
ORDER BY id DESC
LIMIT :limit
"""

UPDATE_LOCATION_PROMOTE_SQL = """
UPDATE locations
SET state='VERIFIED',
    category = COALESCE(:category, category),
    confidence_score = COALESCE(:confidence_score, confidence_score),
    last_verified_at = NOW()
WHERE id = :id
"""

UPDATE_LOCATION_RETIRED_SQL = """
UPDATE locations
SET state='RETIRED',
    notes = COALESCE(notes, '') || E'\\n[self_verify] auto-retired (ignore)'
WHERE id = :id
"""

UPDATE_LOCATION_CANDIDATE_NOT_PROMOTED_SQL = """
UPDATE locations
SET notes = COALESCE(notes,'') || E'\\n[self_verify] below threshold (conf=' || :conf || ')'
WHERE id = :id
"""

async def fetch_candidates(limit: int) -> list[dict[str, Any]]:
    async with async_engine.begin() as conn:  # type: ignore
        rows = (await conn.execute(text(SELECT_CANDIDATES_SQL), {"limit": limit})).mappings().all()
        return [dict(r) for r in rows]

async def promote_verified(id_: int, category: Optional[str], conf: Optional[float]) -> None:
    if db_upsert_location_state:
        await db_upsert_location_state(
            location_id=id_,
            new_state="VERIFIED",
            category=category,
            confidence_score=conf,
            note="[self_verify] promoted to VERIFIED",
        )
        return
    async with async_engine.begin() as conn:  # type: ignore
        await conn.execute(
            text(UPDATE_LOCATION_PROMOTE_SQL),
            {"id": id_, "category": category, "confidence_score": conf},
        )

async def retire_ignored(id_: int) -> None:
    if db_upsert_location_state:
        await db_upsert_location_state(
            location_id=id_,
            new_state="RETIRED",
            note="[self_verify] auto-retired (ignore)",
        )
        return
    async with async_engine.begin() as conn:  # type: ignore
        await conn.execute(text(UPDATE_LOCATION_RETIRED_SQL), {"id": id_})

async def mark_below_threshold(id_: int, conf: float) -> None:
    if db_upsert_location_state:
        await db_upsert_location_state(
            location_id=id_,
            note=f"[self_verify] below threshold (conf={conf:.2f})",
        )
        return
    async with async_engine.begin() as conn:  # type: ignore
        await conn.execute(text(UPDATE_LOCATION_CANDIDATE_NOT_PROMOTED_SQL), {"id": id_, "conf": conf})

# -------------------------
# AI calls via service-object (sync methods)
# -------------------------
@dataclass
class SelfVerifyService:
    svc: Any

    async def classify(self, payload: dict[str, Any]):
        # Probeer service.classify(...); anders generieke call(task="classify", input=...)
        if hasattr(self.svc, "classify"):
            raw, _meta = self.svc.classify(
                name=payload.get("name"),
                address=payload.get("address"),
                typ=payload.get("category_hint"),
                location_id=payload.get("id"),
            )
        else:
            raw, _meta = self.svc.call(task="classify", input=payload, action_type="self_verify.classify")  # type: ignore
        # Normaliseer
        if isinstance(raw, AIClassification):
            return raw
        if hasattr(raw, "model_dump"):
            return AIClassification(**raw.model_dump())  # type: ignore
        return AIClassification(**raw)  # type: ignore

    async def verify_enrich(self, payload: dict[str, Any]):
        # Probeer service.verify_enrich(...) → verify(...) → call(task="verify_enrich", ...)
        if hasattr(self.svc, "verify_enrich"):
            raw, _meta = self.svc.verify_enrich(
                name=payload.get("name"),
                address=payload.get("address"),
                category=payload.get("category"),
                location_id=payload.get("id"),
            )
        elif hasattr(self.svc, "verify"):
            raw, _meta = self.svc.verify(
                name=payload.get("name"),
                address=payload.get("address"),
                category=payload.get("category"),
                location_id=payload.get("id"),
            )
        else:
            raw, _meta = self.svc.call(task="verify_enrich", input=payload, action_type="self_verify.verify")  # type: ignore
        if isinstance(raw, AIVerificationResult):
            return raw
        if hasattr(raw, "model_dump"):
            return AIVerificationResult(**raw.model_dump())  # type: ignore
        return AIVerificationResult(**raw)  # type: ignore

# -------------------------
# Core processing
# -------------------------
class Counters:
    def __init__(self):
        self.processed = 0
        self.promoted = 0
        self.retired = 0
        self.skipped = 0
        self.below_threshold = 0
    def as_dict(self): return dict(processed=self.processed, promoted=self.promoted, retired=self.retired, skipped=self.skipped, below_threshold=self.below_threshold)

async def process_one(rec: dict[str, Any], conf_threshold: float, dry_run: bool, counters: Counters, sem: asyncio.Semaphore, svs: SelfVerifyService):
    async with sem:
        id_ = rec["id"]
        name = rec.get("name")

        classify_payload = {"id": id_, "name": name, "address": rec.get("address"), "category_hint": rec.get("category")}
        await asyncio.sleep(random.uniform(0.05, 0.25))

        try:
            cls = await svs.classify(classify_payload)
        except Exception as e:
            logger.error("classify_failed", id=id_, error=str(e))
            counters.skipped += 1
            return

        if cls.action == "ignore":
            if dry_run:
                logger.info("ignored_candidate_dry", id=id_, name=name)
            else:
                await retire_ignored(id_)
                logger.info("ignored_candidate", id=id_, name=name)
                counters.retired += 1
            counters.processed += 1
            return

        verify_payload = {"id": id_, "name": name, "address": rec.get("address"), "category": cls.category}
        await asyncio.sleep(random.uniform(0.1, 0.3))

        try:
            ver = await svs.verify_enrich(verify_payload)
        except Exception as e:
            logger.error("verify_failed", id=id_, error=str(e))
            counters.skipped += 1
            return

        final_conf = float(ver.confidence_score)
        if final_conf >= conf_threshold:
            if dry_run:
                logger.info("would_promote", id=id_, name=name, cat=cls.category, conf=final_conf)
            else:
                await promote_verified(id_, cls.category, final_conf)
                logger.info("promoted_verified", id=id_, name=name, cat=cls.category, conf=final_conf)
                counters.promoted += 1
        else:
            if dry_run:
                logger.info("below_threshold_dry", id=id_, conf=final_conf, threshold=conf_threshold)
            else:
                await mark_below_threshold(id_, final_conf)
                logger.info("below_threshold", id=id_, conf=final_conf, threshold=conf_threshold)
                counters.below_threshold += 1

        counters.processed += 1

async def run_self_verify(limit: int, conf_threshold: float, dry_run: bool, concurrency: int, model_override: Optional[str]) -> Counters:
    svc = OpenAIService(model=model_override or DEFAULT_MODEL)  # type: ignore
    svs = SelfVerifyService(svc=svc)

    with with_run_id(logger) as log:
        t0 = time.perf_counter()
        log.info("self_verify_start", limit=limit, conf_threshold=conf_threshold, dry_run=dry_run, concurrency=concurrency, model=model_override or DEFAULT_MODEL)

        records = await fetch_candidates(limit)
        log.info("self_verify_candidates", count=len(records))

        counters = Counters()
        sem = asyncio.Semaphore(concurrency)
        await asyncio.gather(*(process_one(rec, conf_threshold, dry_run, counters, sem, svs) for rec in records))

        if metrics_service and hasattr(metrics_service, "record_counts"):  # type: ignore
            try:
                await metrics_service.record_counts(  # type: ignore
                    source="self_verify_bot",
                    ts=datetime.now(timezone.utc).isoformat(),
                    **counters.as_dict(),
                )
            except Exception as e:
                log.warning("metrics_record_failed", error=str(e))

        duration_ms = int((time.perf_counter() - t0) * 1000)
        log.info("self_verify_done", duration_ms=duration_ms, **counters.as_dict())
        return counters

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("Self-Verifying AI Loop")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    p.add_argument("--min-confidence", type=float, default=DEFAULT_CONF)
    p.add_argument("--dry-run", action="store_true", default=False)
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONC)
    p.add_argument("--model", type=str, default=None, help="Override model (default via .env OPENAI_MODEL)")
    return p.parse_args()

def main():
    args = parse_args()
    counters = asyncio.run(
        run_self_verify(
            limit=args.limit,
            conf_threshold=args.min_confidence,
            dry_run=args.dry_run,
            concurrency=args.concurrency,
            model_override=args.model,
        )
    )
    print(f"✅ Loop completed – records verified: {counters.promoted}")

if __name__ == "__main__":
    main()
