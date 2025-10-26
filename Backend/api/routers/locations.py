from __future__ import annotations

from typing import Any, List
from fastapi import APIRouter, HTTPException, Query

from services.db_service import fetch
from app.services.category_map import normalize_category

router = APIRouter(
    prefix="/api/v1/locations",
    tags=["locations"],
)

@router.get("/ping")
async def ping() -> dict[str, Any]:
    """
    Health check that also verifies DB connectivity.
    """
    try:
        await fetch("SELECT 1")
        return {"ok": True, "router": "locations", "db": True}
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")


@router.get("", response_model=List[dict])
async def list_locations(
    state: str = Query(
        "VERIFIED",
        description="Client hint only. Server enforces its own visibility rules.",
    ),
    limit: int = Query(
        200,
        gt=1,
        le=2000,
        description="Max number of records to return (2..2000)",
    ),
):
    """
    Public list of diaspora locations for the map.

    Visibility rules:
    - Always include rows that are already VERIFIED and not retired,
      with confidence_score >= 0.80.
    - ALSO include high-confidence (>=0.90) rows that are still
      PENDING_VERIFICATION or CANDIDATE and not retired.
      These are auto-surfaced “almost certainly Turkish” places.

    We never return RETIRED and we skip anything with low/null confidence.

    NOTE: we are using asyncpg via services.db_service.fetch(), not SQLAlchemy.
    """

    sql = """
        SELECT
            id,
            name,
            address,
            lat,
            lng,
            category,
            rating,
            state,
            confidence_score
        FROM locations
        WHERE (
            state = 'VERIFIED'
            AND (confidence_score IS NOT NULL AND confidence_score >= 0.80)
            AND (is_retired = false OR is_retired IS NULL)
        ) OR (
            state IN ('PENDING_VERIFICATION', 'CANDIDATE')
            AND (confidence_score IS NOT NULL AND confidence_score >= 0.90)
            AND (is_retired = false OR is_retired IS NULL)
        )
        ORDER BY id DESC
        LIMIT $1
    """

    try:
        data = await fetch(sql, limit)
        rows = [dict(r) for r in data]

        # Normalize field types for the frontend
        for r in rows:
            # force id to string for React key stability
            r["id"] = str(r.get("id"))

            # lat / lng to floats
            if r.get("lat") is not None:
                try:
                    r["lat"] = float(r["lat"])
                except Exception:
                    r["lat"] = None
            else:
                r["lat"] = None

            if r.get("lng") is not None:
                try:
                    r["lng"] = float(r["lng"])
                except Exception:
                    r["lng"] = None
            else:
                r["lng"] = None

            # numeric fields that might come back as Decimal / str
            if r.get("rating") is not None:
                try:
                    r["rating"] = float(r["rating"])
                except Exception:
                    r["rating"] = None

            if r.get("confidence_score") is not None:
                try:
                    r["confidence_score"] = float(r["confidence_score"])
                except Exception:
                    pass

            # Category normalization enrichment for frontend
            try:
                cat_info = normalize_category(str(r.get("category") or ""))
                r["category_raw"] = cat_info.get("category_raw")
                r["category_key"] = cat_info.get("category_key")
                r["category_label"] = cat_info.get("category_label")
            except Exception:
                # Best-effort fallback to raw values if normalization fails
                raw = r.get("category")
                r["category_raw"] = raw
                r["category_key"] = str(raw).strip().lower().replace("/", "_").replace(" ", "_") if raw else "other"
                # Simple labelization
                try:
                    tmp = str(raw or "").replace("/", " ").replace("_", " ").strip()
                    r["category_label"] = " ".join([t[:1].upper() + t[1:].lower() for t in tmp.split()]) or "Overig"
                except Exception:
                    r["category_label"] = "Overig"

        return rows

    except Exception as e:
        print(f"[locations] query failed: {e}")
        raise HTTPException(status_code=503, detail="database unavailable")


@router.get("/", response_model=List[dict])
async def list_locations_slash(
    state: str = Query(
        "VERIFIED",
        description="Client hint only. Server enforces its own visibility rules.",
    ),
    limit: int = Query(
        200,
        gt=1,
        le=2000,
        description="Max number of records to return (2..2000)",
    ),
):
    return await list_locations(state=state, limit=limit)
