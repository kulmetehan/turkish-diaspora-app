from __future__ import annotations

import os
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, Body

from services.db_service import execute, fetch, fetchrow, update_location_classification

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


def _ensure_local_admin() -> None:
    """
    Very basic protection so this isn't usable in prod.
    If ENVIRONMENT isn't 'local'/'dev', we refuse.
    """
    if os.getenv("ENVIRONMENT", "local") not in ("local", "dev", "development"):
        raise HTTPException(status_code=403, detail="admin endpoints disabled")


@router.get("/locations", response_model=List[dict])
async def admin_list_locations(
    limit: int = Query(
        200,
        gt=1,
        le=2000,
        description="How many rows to inspect (2..2000)",
    ),
):
    """
    Admin inspection: show latest locations regardless of VERIFIED/PENDING/etc.
    This helps check what the classifier just did.

    NOTE: This returns raw state, confidence_score, notes, etc.
    """
    _ensure_local_admin()

    sql = """
        SELECT
            id,
            name,
            address,
            lat,
            lng,
            category,
            state,
            confidence_score,
            is_retired,
            notes,
            first_seen_at
        FROM locations
        ORDER BY first_seen_at DESC
        LIMIT $1
    """

    try:
        data = await fetch(sql, limit)
        rows = [dict(r) for r in data]

        # normalize a couple types so JSON is stable
        for r in rows:
            r["id"] = str(r.get("id"))

            if r.get("lat") is not None:
                try:
                    r["lat"] = float(r["lat"])
                except Exception:
                    r["lat"] = None

            if r.get("lng") is not None:
                try:
                    r["lng"] = float(r["lng"])
                except Exception:
                    r["lng"] = None

            if r.get("confidence_score") is not None:
                try:
                    r["confidence_score"] = float(r["confidence_score"])
                except Exception:
                    pass

        return rows
    except Exception as e:
        print(f"[admin.locations] query failed: {e}")
        raise HTTPException(status_code=503, detail="database unavailable")


@router.post("/locations/{location_id}/override")
async def admin_override_location(
    location_id: int,
    new_state: str = Body(
        ...,
        embed=True,
        description="One of VERIFIED, PENDING_VERIFICATION, CANDIDATE, RETIRED",
    ),
    new_category: Optional[str] = Body(None, embed=True),
    new_confidence: Optional[float] = Body(None, embed=True),
    note: Optional[str] = Body(None, embed=True),
):
    """
    Force-update a single location's moderation outcome.

    This is our manual moderation / 'human in the loop' hook.

    Behavior:
    - If you send new_state + new_category + new_confidence,
      we'll call update_location_classification() the same way
      the classifier does — which also updates state consistently
      (VERIFIED, RETIRED, etc.).
    - If you ONLY want to tweak state directly, we'll issue a raw UPDATE
      that sets state but won't erase category/confidence.
      (This is useful if Supabase UI was auto-reverting you.)
    """
    _ensure_local_admin()

    # 1. If you provided category/confidence, go through the same helper
    #    our classifier uses, so we don't accidentally violate enum rules.
    if new_category is not None or new_confidence is not None:
        final_category = new_category if new_category is not None else "other"
        final_conf = new_confidence if new_confidence is not None else 0.0
        final_reason = note if note is not None else "admin override"

        # map desired state -> action for update_location_classification
        if new_state == "VERIFIED":
            action = "keep"
        elif new_state == "RETIRED":
            action = "ignore"
        else:
            action = "keep"

        try:
            await update_location_classification(
                id=location_id,
                action=action,
                category=final_category,
                confidence_score=final_conf,
                reason=final_reason,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update via classification helper: {e}",
            )

    # 2. Force-set state if caller explicitly asked for it.
    #    This lets you do: "this is VERIFIED now, period."
    try:
        sql_force = """
            UPDATE locations
            SET state = $1
            WHERE id = $2
        """
        await execute(sql_force, new_state, int(location_id))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to force state: {e}",
        )

    # 3. Return the latest row so UI can refresh
    sql_return = """
        SELECT
            id,
            name,
            address,
            lat,
            lng,
            category,
            state,
            confidence_score,
            is_retired,
            notes,
            first_seen_at
        FROM locations
        WHERE id = $1
        LIMIT 1
    """
    row = await fetchrow(sql_return, int(location_id))
    row = dict(row) if row else None
    if not row:
        raise HTTPException(status_code=404, detail="location not found (post-update)")

    # normalize types for response
    row["id"] = str(row.get("id"))

    if row.get("lat") is not None:
        try:
            row["lat"] = float(row["lat"])
        except Exception:
            row["lat"] = None

    if row.get("lng") is not None:
        try:
            row["lng"] = float(row["lng"])
        except Exception:
            row["lng"] = None

    if row.get("confidence_score") is not None:
        try:
            row["confidence_score"] = float(row["confidence_score"])
        except Exception:
            pass

    return {"ok": True, "location": row}