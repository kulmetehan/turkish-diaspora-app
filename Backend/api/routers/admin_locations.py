from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.admin_locations import (
    AdminLocationDetail,
    AdminLocationListItem,
    AdminLocationUpdateRequest,
)
from services.audit_service import audit_admin_action
from services.db_service import fetch, execute


router = APIRouter(
    prefix="/admin/locations",
    tags=["admin-locations"],
)


@router.get("", response_model=Dict[str, Any])
async def list_admin_locations(
    search: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, Any]:
    # filters
    search_val = (search or "").strip()
    state_val = (state or "").strip().upper()

    sql_rows = (
        """
        SELECT id, name, category, state, confidence_score, last_verified_at
        FROM locations
        WHERE ($1::text IS NULL OR $1 = '' OR name ILIKE '%' || $1 || '%' OR address ILIKE '%' || $1 || '%')
          AND (
            $2::text IS NULL OR $2 = '' OR state = $2::location_state
          )
        ORDER BY id DESC
        LIMIT $3 OFFSET $4
        """
    )
    rows = await fetch(sql_rows, search_val, state_val, int(limit), int(offset))
    data = [AdminLocationListItem(**dict(r)).model_dump() for r in rows]

    sql_count = (
        """
        SELECT COUNT(1) AS total
        FROM locations
        WHERE ($1::text IS NULL OR $1 = '' OR name ILIKE '%' || $1 || '%' OR address ILIKE '%' || $1 || '%')
          AND (
            $2::text IS NULL OR $2 = '' OR state = $2::location_state
          )
        """
    )
    total_rows = await fetch(sql_count, search_val, state_val)
    total = int(dict(total_rows[0]).get("total", 0)) if total_rows else 0
    return {"rows": data, "total": total}


@router.get("/", response_model=Dict[str, Any])
async def list_admin_locations_slash(
    search: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, Any]:
    return await list_admin_locations(search=search, state=state, limit=limit, offset=offset, admin=admin)


@router.get("/{location_id}", response_model=AdminLocationDetail)
async def get_admin_location(
    location_id: int,
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminLocationDetail:
    sql = (
        """
        SELECT
            id, name, category, state, confidence_score, last_verified_at,
            address, notes, business_status, rating, user_ratings_total, is_probable_not_open_yet
        FROM locations
        WHERE id = $1
        LIMIT 1
        """
    )
    rows = await fetch(sql, int(location_id))
    if not rows:
        raise HTTPException(status_code=404, detail="location not found")
    return AdminLocationDetail(**dict(rows[0]))


@router.put("/{location_id}", response_model=AdminLocationDetail)
async def update_admin_location(
    location_id: int,
    body: AdminLocationUpdateRequest,
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminLocationDetail:
    # 1) Before
    before_sql = (
        """
        SELECT id, name, address, category, state, notes, business_status,
               is_probable_not_open_yet, confidence_score, last_verified_at,
               rating, user_ratings_total
        FROM locations WHERE id = $1 LIMIT 1
        """
    )
    before_rows = await fetch(before_sql, int(location_id))
    if not before_rows:
        raise HTTPException(status_code=404, detail="location not found")
    before = dict(before_rows[0])

    # 2) Update only allowed columns that are provided
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if patch:
        columns = []
        values: List[Any] = []
        idx = 1
        for key, val in patch.items():
            columns.append(f"{key} = ${idx}")
            values.append(val)
            idx += 1
        # Always stamp last_verified_at for admin updates
        columns.append("last_verified_at = NOW()")
        set_clause = ", ".join(columns)
        sql = f"UPDATE locations SET {set_clause} WHERE id = ${idx}"
        values.append(int(location_id))
        await execute(sql, *values)

    # 3) After
    after_rows = await fetch(before_sql, int(location_id))
    after = dict(after_rows[0]) if after_rows else None

    # 4) Audit
    await audit_admin_action(admin.email, int(location_id), "admin_update", before, after)

    # 5) Return full detail
    detail_sql = (
        """
        SELECT
            id, name, category, state, confidence_score, last_verified_at,
            address, notes, business_status, rating, user_ratings_total, is_probable_not_open_yet
        FROM locations
        WHERE id = $1
        LIMIT 1
        """
    )
    rows = await fetch(detail_sql, int(location_id))
    return AdminLocationDetail(**dict(rows[0]))


@router.delete("/{location_id}", response_model=Dict[str, bool])
async def retire_admin_location(
    location_id: int,
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, bool]:
    # Before
    before_rows = await fetch("SELECT * FROM locations WHERE id = $1 LIMIT 1", int(location_id))
    before = dict(before_rows[0]) if before_rows else None

    # Soft retire + note
    sql = (
        """
        UPDATE locations
        SET state = 'RETIRED',
            notes = COALESCE(notes, '')
                   || CASE WHEN notes IS NULL OR notes = '' THEN '' ELSE E'\\n' END
                   || $1
        WHERE id = $2
        """
    )
    note = f"[manual retire by {admin.email}]"
    await execute(sql, note, int(location_id))

    # After
    after_rows = await fetch("SELECT * FROM locations WHERE id = $1 LIMIT 1", int(location_id))
    after = dict(after_rows[0]) if after_rows else None

    # Audit
    await audit_admin_action(admin.email, int(location_id), "admin_retire", before, after)

    return {"ok": True}