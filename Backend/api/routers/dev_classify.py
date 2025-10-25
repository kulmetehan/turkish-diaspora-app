# api/routers/dev_classify.py
from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException

# Nieuwe asyncpg-helpers i.p.v. SQLAlchemy engine
from services.db_service import fetch, update_location_classification, init_db_pool
from services.classify_service import ClassifyService

router = APIRouter(prefix="/dev/ai", tags=["dev-ai"])


@router.on_event("startup")
async def _init_pool_once() -> None:
    # Zorg dat de asyncpg pool bestaat wanneer deze router gebruikt wordt
    await init_db_pool()


def _ensure_local() -> None:
    # Basic gating: alleen lokaal/dev toestaan
    if os.getenv("ENVIRONMENT", "local") not in ("local", "dev", "development"):
        raise HTTPException(status_code=403, detail="dev endpoints disabled")

@router.get("/classify-one")
async def classify_one(id: int):
    _ensure_local()
    sql = (
        """
        SELECT id, name, address, category AS type
        FROM locations
        WHERE id = $1
        """
    )
    rows = await fetch(sql, id)
    row = dict(rows[0]) if rows else None
    if not row:
        raise HTTPException(status_code=404, detail="location not found")

    svc = ClassifyService()
    parsed, meta = svc.classify(
        name=row["name"], address=row["address"], typ=row["type"], location_id=row["id"]
    )
    return {"ok": True, "parsed": parsed.dict(), "meta": meta}

@router.post("/classify-apply")
async def classify_apply(id: int):
    _ensure_local()
    sql = (
        """
        SELECT id, name, address, category AS type
        FROM locations
        WHERE id = $1
        """
    )
    rows = await fetch(sql, id)
    row = dict(rows[0]) if rows else None
    if not row:
        raise HTTPException(status_code=404, detail="location not found")

    svc = ClassifyService()
    parsed, meta = svc.classify(
        name=row["name"], address=row["address"], typ=row["type"], location_id=row["id"]
    )

    await update_location_classification(
        id=row["id"],
        action=parsed.action if hasattr(parsed, "action") else "ignore",
        category=parsed.category if hasattr(parsed, "category") else (row.get("type") or "other"),
        confidence_score=float(parsed.confidence_score) if hasattr(parsed, "confidence_score") else 0.0,
        reason=getattr(parsed, "reason", "dev classify apply"),
    )
    return {"ok": True, "applied": parsed.dict()}
