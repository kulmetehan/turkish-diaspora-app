# api/routers/admin.py
from __future__ import annotations

from dataclasses import dataclass
import os
from datetime import datetime
from typing import Any, Dict, Optional, Set, List

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# Belangrijk: deze router krijgt /admin; jouw main.py hangt '/api/v1' erbovenop
router = APIRouter(prefix="/admin", tags=["admin"])

# === Dependencies ===
# Async engine uit jouw db-service (pad is in main.py al aan sys.path toegevoegd)
from services.db_service import async_engine  # type: ignore
try:
    from services.audit_service import audit_service  # type: ignore
except Exception:  # als audit_service (tijdelijk) niet bestaat, beschermen we calls
    audit_service = None  # type: ignore


# ---------- Security context (géén Pydantic!) ----------
@dataclass
class AdminContext:
    engine: AsyncEngine
    actor: str


def _require_admin(admin_key_in: Optional[str]) -> str:
    expected = os.environ.get("ADMIN_API_KEY", "")
    if not expected or admin_key_in != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return os.environ.get("ADMIN_ACTOR", "admin")


async def get_admin_ctx(
    x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")
) -> AdminContext:
    actor = _require_admin(x_admin_key)
    return AdminContext(engine=async_engine, actor=actor)


@router.get("/ping")
async def ping():
    return {"ok": True, "router": "admin"}


# ---------- Schemas ----------
class AdminLocationCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    address: str
    lat: float
    lng: float
    category: Optional[str] = None
    business_status: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    notes: Optional[str] = None
    is_probable_not_open_yet: Optional[bool] = None


class AdminLocationUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    category: Optional[str] = None
    business_status: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    notes: Optional[str] = None
    confidence_score: Optional[float] = None
    is_probable_not_open_yet: Optional[bool] = None
    state: Optional[str] = None


class AdminLocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    address: str
    lat: float
    lng: float
    category: Optional[str] = None
    business_status: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    confidence_score: Optional[float] = None
    state: str
    last_verified_at: Optional[datetime] = None
    notes: Optional[str] = None


# ---------- DB Helpers ----------
async def _table_columns(engine: AsyncEngine, table: str) -> Set[str]:
    sql = text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=:table
    """)
    async with engine.begin() as conn:
        rows = (await conn.execute(sql, {"table": table})).all()
    return {r[0] for r in rows}


async def _fetch_location(engine: AsyncEngine, location_id: int) -> Optional[Dict[str, Any]]:
    sql = text("SELECT * FROM locations WHERE id=:id")
    async with engine.begin() as conn:
        row = (await conn.execute(sql, {"id": location_id})).mappings().first()
    return dict(row) if row else None


async def _insert_training_gold(
    engine: AsyncEngine,
    location_id: int,
    category: Optional[str],
    actor: str,
    note_prefix: str,
) -> None:
    """
    Schrijf een 'gold' voorbeeld voor de LearningBot in training_data:
    - label_action = 'keep' (past bij jouw CHECK constraint)
    - is_gold_standard = true (als kolom bestaat)
    - input_data en expected_output als JSON-string (TEXT) indien kolommen bestaan
    """
    cols = await _table_columns(engine, "training_data")
    if not cols:
        return

    loc = await _fetch_location(engine, location_id) or {}
    import json as _json

    input_payload = {
        "name": loc.get("name"),
        "type": loc.get("category"),
        "address": loc.get("address"),
    }
    expected_payload = {
        "action": "keep",
        "reason": "gold: admin verified",
        "category": category,
        "confidence_score": 1.0,
    }

    wanted: Dict[str, Any] = {
        "location_id": location_id,
        "label_action": "keep",  # <- belangrijk
        "label_category": category,
        "notes": f"{note_prefix}; actor={actor}",
    }
    if "input_data" in cols:
        wanted["input_data"] = _json.dumps(input_payload, ensure_ascii=False)
    if "expected_output" in cols:
        wanted["expected_output"] = _json.dumps(expected_payload, ensure_ascii=False)
    if "is_gold_standard" in cols:
        wanted["is_gold_standard"] = True

    insertable = [k for k in wanted.keys() if k in cols]
    if not insertable:
        return

    sql = text(f"""
        INSERT INTO training_data ({", ".join(insertable)})
        VALUES ({", ".join(":" + k for k in insertable)})
    """)
    async with engine.begin() as conn:
        await conn.execute(sql, {k: wanted[k] for k in insertable})


# ---------- Endpoints ----------
@router.post("/locations", response_model=AdminLocationOut)
async def admin_create_location(payload: AdminLocationCreate, ctx: AdminContext = Depends(get_admin_ctx)):
    """
    Admin: maak nieuwe locatie, direct VERIFIED.
    - Insert alleen bestaande kolommen
    - Daarna losse updates voor state/source/score en timestamps
    - Schrijf gold training record
    """
    loc_cols = await _table_columns(ctx.engine, "locations")
    if not loc_cols:
        raise HTTPException(status_code=500, detail="locations table not found")

    # Voorzichtig inserten: alleen kolommen die bestaan en waarde hebben
    desired: Dict[str, Any] = {
        "name": payload.name,
        "address": payload.address,
        "lat": payload.lat,
        "lng": payload.lng,
        "category": payload.category,
        "business_status": payload.business_status,
        "rating": payload.rating,
        "user_ratings_total": payload.user_ratings_total,
        "notes": payload.notes,
        "is_probable_not_open_yet": payload.is_probable_not_open_yet,
    }
    insert_cols = [k for k, v in desired.items() if v is not None and k in loc_cols]
    if not insert_cols:
        # Minimale vereisten
        minimal_keys: List[str] = [k for k in ("name", "address", "lat", "lng") if k in loc_cols]
        if not all(k in minimal_keys for k in ("name", "address", "lat", "lng")):
            raise HTTPException(status_code=400, detail="No valid columns to insert.")
        insert_cols = minimal_keys
        desired = {k: desired[k] for k in insert_cols}

    sql_insert = text(f"""
        INSERT INTO locations ({", ".join(insert_cols)})
        VALUES ({", ".join(":" + c for c in insert_cols)})
        RETURNING id
    """)

    async with ctx.engine.begin() as conn:
        row = (await conn.execute(sql_insert, {c: desired[c] for c in insert_cols})).mappings().first()
        if not row:
            raise HTTPException(status_code=500, detail="Insert failed (no id returned)")
        new_id = row["id"]

        # Losse updates op basis van kolommen die bestaan
        if "source" in loc_cols:
            await conn.execute(text("UPDATE locations SET source='ADMIN' WHERE id=:id"), {"id": new_id})
        if "state" in loc_cols:
            await conn.execute(text("UPDATE locations SET state='VERIFIED' WHERE id=:id"), {"id": new_id})
        if "confidence_score" in loc_cols:
            await conn.execute(text("UPDATE locations SET confidence_score=1.0 WHERE id=:id"), {"id": new_id})
        if "first_seen_at" in loc_cols:
            await conn.execute(text("UPDATE locations SET first_seen_at=NOW() WHERE id=:id AND first_seen_at IS NULL"), {"id": new_id})
        if "last_seen_at" in loc_cols:
            await conn.execute(text("UPDATE locations SET last_seen_at=NOW() WHERE id=:id"), {"id": new_id})
        if "last_verified_at" in loc_cols:
            await conn.execute(text("UPDATE locations SET last_verified_at=NOW() WHERE id=:id"), {"id": new_id})

    # Audit (best-effort)
    try:
        if audit_service:
            after = await _fetch_location(ctx.engine, new_id)
            await audit_service.log(
                action_type="admin.create",
                actor=ctx.actor,
                location_id=new_id,
                before=None,
                after=after,
                is_success=True,
                meta={"reason": "manual create"},
            )
    except Exception as e:
        # Geen crash; audit is nice-to-have
        print("audit log failed:", repr(e))

    # Gold training record (label_action='keep', is_gold_standard=true)
    try:
        await _insert_training_gold(ctx.engine, new_id, payload.category, ctx.actor, "manual create -> verified")
    except Exception as e:
        print("training_data insert failed:", repr(e))

    # Teruglezen voor response
    want_back = [
        "id", "name", "address", "lat", "lng",
        "category", "business_status", "rating",
        "user_ratings_total", "confidence_score", "state",
        "last_verified_at", "notes",
    ]
    present = [c for c in want_back if c in loc_cols]
    select_sql = text(f"SELECT {', '.join(present)} FROM locations WHERE id=:id")
    async with ctx.engine.begin() as conn:
        out = (await conn.execute(select_sql, {"id": new_id})).mappings().first()
    if not out:
        raise HTTPException(status_code=500, detail="Failed to read created record")
    return out


@router.patch("/locations/{location_id}", response_model=AdminLocationOut)
async def admin_update_location(location_id: int, payload: AdminLocationUpdate, ctx: AdminContext = Depends(get_admin_ctx)):
    before = await _fetch_location(ctx.engine, location_id)
    if not before:
        raise HTTPException(status_code=404, detail="Location not found")

    cols = await _table_columns(ctx.engine, "locations")
    fields = payload.model_dump(exclude_unset=True)

    set_parts: List[str] = []
    params: Dict[str, Any] = {"id": location_id}
    for k, v in fields.items():
        if k in cols:
            set_parts.append(f"{k} = :{k}")
            params[k] = v

    # Als state -> VERIFIED: timestamps en evt. score ophogen
    if fields.get("state") == "VERIFIED" and "state" in cols:
        if "last_verified_at" in cols:
            set_parts.append("last_verified_at = NOW()")
        if "confidence_score" in cols and "confidence_score" not in params:
            prev = float(before.get("confidence_score") or 0.0)
            params["confidence_score"] = max(prev, 0.95)
            set_parts.append("confidence_score = :confidence_score")

    if "last_seen_at" in cols:
        set_parts.append("last_seen_at = NOW()")

    if not set_parts:
        return AdminLocationOut(**before)

    sql = text(f"UPDATE locations SET {', '.join(set_parts)} WHERE id=:id")
    async with ctx.engine.begin() as conn:
        await conn.execute(sql, params)

    after = await _fetch_location(ctx.engine, location_id)

    # Audit (best-effort)
    try:
        if audit_service:
            await audit_service.log(
                action_type="admin.update",
                actor=ctx.actor,
                location_id=location_id,
                before=before,
                after=after,
                is_success=True,
                meta={"reason": "manual update"},
            )
    except Exception as e:
        print("audit log failed:", repr(e))

    return AdminLocationOut(**(after or before))
