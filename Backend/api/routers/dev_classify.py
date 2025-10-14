# api/routers/dev_classify.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

# Let op: hier importeren we uit het top-level 'services' pakket
from services.db_service import async_engine, update_location_classification
from services.classify_service import ClassifyService  # <-- FIX HIER

router = APIRouter(prefix="/dev/ai", tags=["dev-ai"])

@router.get("/classify-one")
async def classify_one(id: int):
    q = text("SELECT id, name, address, category AS type FROM locations WHERE id=:id")
    async with async_engine.begin() as conn:
        row = (await conn.execute(q, {"id": id})).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="location not found")

    svc = ClassifyService()
    parsed, meta = svc.classify(
        name=row["name"], address=row["address"], typ=row["type"], location_id=row["id"]
    )
    return {"ok": True, "parsed": parsed.dict(), "meta": meta}

@router.post("/classify-apply")
async def classify_apply(id: int):
    q = text("SELECT id, name, address, category AS type FROM locations WHERE id=:id")
    async with async_engine.begin() as conn:
        row = (await conn.execute(q, {"id": id})).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="location not found")

    svc = ClassifyService()
    parsed, meta = svc.classify(
        name=row["name"], address=row["address"], typ=row["type"], location_id=row["id"]
    )

    await update_location_classification(
        id=row["id"],
        action=parsed.action,
        category=parsed.category,
        confidence_score=parsed.confidence_score,
        reason=parsed.reason,
    )
    return {"ok": True, "applied": parsed.dict()}
