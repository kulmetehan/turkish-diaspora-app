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


@router.get("/stats")
async def locations_stats(
    state: str = Query("VERIFIED", description="Filter op state (comma-separated for multiple)"),
    recent_limit: int = Query(100, gt=10, le=2000, description="Aantal recente records om te groeperen"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Simpele statistieken t.b.v. verificatie/monitoring:
    - totaal aantal VERIFIED (of opgegeven states)
    - aantallen per category
    - distinct categories
    - recent_per_category: recente voorbeelden (max 5 per category) uit de laatste `recent_limit` records
    """
    states = [s.strip() for s in state.split(',')]
    state_placeholders = ','.join([f':state_{i}' for i in range(len(states))])

    try:
        # Total
        sql_total = text(f"SELECT COUNT(*) AS c FROM locations WHERE state IN ({state_placeholders})")
        params = {f"state_{i}": states[i] for i in range(len(states))}
        total_row = (await db.execute(sql_total, params)).mappings().first()
        total_verified = int(total_row["c"]) if total_row and total_row.get("c") is not None else 0

        # By category
        sql_by_cat = text(
            f"""
            SELECT COALESCE(category, 'unknown') AS category, COUNT(*) AS c
            FROM locations
            WHERE state IN ({state_placeholders})
            GROUP BY category
            ORDER BY c DESC
            """
        )
        by_cat_rows = (await db.execute(sql_by_cat, params)).mappings().all()
        by_category = [{"category": r["category"], "count": int(r["c"]) } for r in by_cat_rows]

        # Distinct categories
        distinct_categories = [r["category"] for r in by_cat_rows if r.get("category")] 

        # Recent sample to show examples per category
        sql_recent = text(
            f"""
            SELECT id, name, COALESCE(category, 'unknown') AS category
            FROM locations
            WHERE state IN ({state_placeholders})
            ORDER BY id DESC
            LIMIT :lim
            """
        )
        recent_params = {**params, "lim": recent_limit}
        recent_rows = (await db.execute(sql_recent, recent_params)).mappings().all()

        # Group top 5 examples per category
        recent_per_category: dict[str, list[dict[str, Any]]] = {}
        for r in recent_rows:
            cat = r["category"]
            bucket = recent_per_category.setdefault(cat, [])
            if len(bucket) < 5:
                bucket.append({"id": int(r["id"]), "name": r["name"]})

        return {
            "total_verified": total_verified,
            "by_category": by_category,
            "distinct_categories": distinct_categories,
            "recent_per_category": recent_per_category,
        }
    except Exception as e:
        print(f"[locations.stats] query failed: {e}")
        raise HTTPException(status_code=503, detail="database unavailable")
