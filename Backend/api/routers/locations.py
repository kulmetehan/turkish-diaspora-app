# Backend/api/routers/locations.py
from __future__ import annotations

from typing import Any, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Gebruik de gedeelde async engine (zoals beschreven in TDA-10)
# services/db_service.py definieert async_engine
from services.db_service import async_engine  # noqa: F401

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])

# Lokale sessionmaker op basis van de gedeelde engine
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/ping")
async def ping(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """DB-aware ping: verifies DB connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"ok": True, "router": "locations", "db": True}
    except Exception:
        # reflect DB readiness accurately
        raise HTTPException(status_code=503, detail="database unavailable")

@router.get("/", response_model=List[dict])
async def list_locations(
    state: str = Query("VERIFIED", description="Filter op state (comma-separated for multiple)"),
    limit: int = Query(200, gt=1, le=2000, description="Max aantal records (2..2000)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Minimale, veilige listing:
    - Alleen kolommen waarvan we zeker weten dat ze bestaan (geen 'website').
    - Eenvoudige state-filter en limit.
    - Geen crash bij DB-fout: log & return [].
    """
    # Let op: geen 'website' selecteren (TDA-8 mapping gebruikt die kolom niet)
    # Support multiple states separated by comma
    states = [s.strip() for s in state.split(',')]
    state_placeholders = ','.join([f':state_{i}' for i in range(len(states))])
    
    sql = f"""
        SELECT
            id,
            name,
            lat,
            lng,
            category,
            rating,
            state,
            confidence_score
        FROM locations
        WHERE state IN ({state_placeholders})
        ORDER BY id DESC
        LIMIT :limit
    """
    params = {f"state_{i}": states[i] for i in range(len(states))}
    params["limit"] = limit

    try:
        result = await db.execute(text(sql), params)
        rows = [dict(r) for r in result.mappings().all()]
        # Normaliseer types die de frontend verwacht
        for r in rows:
            r["id"] = str(r.get("id"))
            # Zorg dat lat/lng numeriek zijn
            r["lat"] = float(r.get("lat")) if r.get("lat") is not None else None
            r["lng"] = float(r.get("lng")) if r.get("lng") is not None else None
            # Optionele velden die de frontend aankan
            if "rating" in r and r["rating"] is not None:
                r["rating"] = float(r["rating"])
        return rows
    except Exception as e:
        # Log and signal temporary unavailability so clients can retry/backoff
        print(f"[locations] query failed: {e}")  # plaatsvervanger voor structlog
        raise HTTPException(status_code=503, detail="database unavailable")
