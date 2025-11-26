from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.admin_locations import (
    AdminLocationDetail,
    AdminLocationListItem,
    AdminLocationUpdateRequest,
    AdminLocationsBulkUpdateRequest,
    AdminLocationsBulkUpdateResponse,
    AdminLocationsBulkUpdateError,
)
from app.core.logging import get_logger
from app.models.categories import get_all_categories
from services.audit_service import audit_admin_action
from services.db_service import (
    execute,
    execute_with_conn,
    fetch,
    fetchrow,
    fetchrow_with_conn,
    DEFAULT_QUERY_TIMEOUT_MS,
    run_in_transaction,
    update_location_classification,
)

logger = get_logger()

DEFAULT_TIMEOUT_S = DEFAULT_QUERY_TIMEOUT_MS / 1000


router = APIRouter(
    prefix="/admin/locations",
    tags=["admin-locations"],
)


class AdminLocationCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    address: str = Field(..., min_length=1, max_length=1000)
    lat: float = Field(..., description="Latitude in WGS84 degrees")
    lng: float = Field(..., description="Longitude in WGS84 degrees")
    category: str = Field(..., min_length=1)
    notes: Optional[str] = Field(default=None, max_length=5000)
    evidence_urls: Optional[List[str]] = None

    @validator("lat")
    def _validate_lat(cls, value: float) -> float:  # noqa: N805
        try:
            lat = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("lat must be numeric") from exc
        if not (-90 <= lat <= 90):
            raise ValueError("lat must be between -90 and 90 degrees")
        return lat

    @validator("lng")
    def _validate_lng(cls, value: float) -> float:  # noqa: N805
        try:
            lng = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("lng must be numeric") from exc
        if not (-180 <= lng <= 180):
            raise ValueError("lng must be between -180 and 180 degrees")
        return lng

    @validator("evidence_urls", each_item=True)
    def _clean_evidence_urls(cls, value: Optional[str]) -> Optional[str]:  # noqa: N805
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


def _clamp_confidence(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


@router.get("", response_model=Dict[str, Any])
async def list_admin_locations(
    search: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    confidence_min: Optional[float] = Query(default=None),
    confidence_max: Optional[float] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    sort_direction: Optional[str] = Query(default="desc"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, Any]:
    search_val = (search or "").strip()
    state_val = (state or "").strip().upper()
    category_val = (category or "").strip()

    sort_val = sort if sort in {"latest_added", "latest_verified"} else None
    direction_val = "asc" if (sort_direction or "").lower() == "asc" else "desc"

    conf_min_val = _clamp_confidence(confidence_min)
    conf_max_val = _clamp_confidence(confidence_max)
    if conf_min_val is not None and conf_max_val is not None and conf_min_val > conf_max_val:
        conf_min_val, conf_max_val = conf_max_val, conf_min_val

    filters = [
        "($1::text IS NULL OR $1 = '' OR l.name ILIKE '%' || $1 || '%' OR l.address ILIKE '%' || $1 || '%')",
        "($2::text IS NULL OR $2 = '' OR l.state = $2::location_state)",
    ]
    params: List[Any] = [search_val, state_val]

    if category_val:
        placeholder = len(params) + 1
        filters.append(f"(l.category = ${placeholder})")
        params.append(category_val)

    confidence_conditions: List[str] = []
    if conf_min_val is not None:
        placeholder = len(params) + 1
        confidence_conditions.append(f"l.confidence_score >= ${placeholder}")
        params.append(conf_min_val)
    if conf_max_val is not None:
        placeholder = len(params) + 1
        confidence_conditions.append(f"l.confidence_score <= ${placeholder}")
        params.append(conf_max_val)

    if confidence_conditions:
        filters.append("(l.confidence_score IS NOT NULL)")
        filters.extend(confidence_conditions)

    where_clause = " AND ".join(filters)
    where_sql = f"WHERE {where_clause}" if where_clause else ""

    if sort_val == "latest_added":
        order_clause = f"ORDER BY l.first_seen_at {direction_val}, l.id DESC"
    elif sort_val == "latest_verified":
        order_clause = f"ORDER BY l.last_verified_at {direction_val} NULLS LAST, l.id DESC"
    else:
        order_clause = "ORDER BY l.id DESC"

    limit_placeholder = len(params) + 1
    offset_placeholder = len(params) + 2

    rows_sql = f"""
        SELECT l.id, l.name, l.category, l.state, l.confidence_score, l.last_verified_at, l.is_retired
        FROM locations AS l
        {where_sql}
        {order_clause}
        LIMIT ${limit_placeholder} OFFSET ${offset_placeholder}
    """

    rows_params = [*params, int(limit), int(offset)]
    rows = await fetch(rows_sql, *rows_params)
    data = [AdminLocationListItem(**dict(r)).model_dump() for r in rows]

    count_sql = f"""
        SELECT COUNT(1) AS total
        FROM locations AS l
        {where_sql}
    """
    total_row = await fetchrow(count_sql, *params)
    total = int(dict(total_row).get("total", 0)) if total_row else 0
    return {"rows": data, "total": total}


@router.get("/location-states", response_model=Dict[str, Any])
async def list_location_states(
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, Any]:
    """
    Return all values of the location_state enum for admin dropdowns.
    """
    rows = await fetch(
        "SELECT unnest(enum_range(NULL::location_state))::text AS value"
    )

    def to_label(value: str) -> str:
        return value.replace("_", " ").title()

    states = [{"value": rec["value"], "label": to_label(rec["value"])} for rec in rows]
    return {"states": states}


@router.get("/", response_model=Dict[str, Any])
async def list_admin_locations_slash(
    search: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    confidence_min: Optional[float] = Query(default=None),
    confidence_max: Optional[float] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    sort_direction: Optional[str] = Query(default="desc"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, Any]:
    return await list_admin_locations(
        search=search,
        state=state,
        category=category,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        sort=sort,
        sort_direction=sort_direction,
        limit=limit,
        offset=offset,
        admin=admin,
    )


def _validate_category_key(category: str) -> str:
    allowed = {cat.key for cat in get_all_categories()}
    normalized = (category or "").strip()
    if not normalized or normalized not in allowed:
        raise HTTPException(status_code=400, detail="invalid category")
    return normalized


def _normalize_evidence_urls(urls: Optional[List[Optional[str]]]) -> Optional[List[str]]:
    if not urls:
        return None
    cleaned: List[str] = []
    for entry in urls:
        trimmed = (entry or "").strip()
        if trimmed:
            cleaned.append(trimmed)
    return cleaned or None


@router.post("", response_model=AdminLocationDetail, status_code=201)
async def create_admin_location(
    body: AdminLocationCreateRequest,
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminLocationDetail:
    category = _validate_category_key(body.category)
    evidence_urls = _normalize_evidence_urls(body.evidence_urls)
    place_id = f"admin_manual/{uuid4()}"

    after: Optional[Dict[str, Any]] = None
    async with run_in_transaction() as conn:
        insert_sql = """
            INSERT INTO locations (
                place_id,
                source,
                name,
                address,
                lat,
                lng,
                category,
                notes,
                evidence_urls,
                state,
                confidence_score,
                first_seen_at,
                last_seen_at,
                is_retired
            ) VALUES (
                $1,
                'ADMIN_MANUAL',
                $2,
                $3,
                $4,
                $5,
                $6,
                $7,
                $8,
                'CANDIDATE',
                NULL,
                NOW(),
                NOW(),
                FALSE
            )
            RETURNING id
        """
        inserted = await fetchrow_with_conn(
            conn,
            insert_sql,
            place_id,
            body.name.strip(),
            body.address.strip(),
            float(body.lat),
            float(body.lng),
            category,
            body.notes.strip() if body.notes else None,
            evidence_urls,
        )
        if inserted is None:
            raise HTTPException(status_code=500, detail="failed to insert location")
        location_id = int(inserted["id"])

        reason = f"[manual add by {admin.email}]"
        await update_location_classification(
            id=location_id,
            action="keep",
            category=category,
            confidence_score=0.9,
            reason=reason,
            conn=conn,
        )

        detail_row = await fetchrow_with_conn(
            conn,
            """
            SELECT
                id, name, category, state, confidence_score, last_verified_at,
                address, notes, business_status, rating, user_ratings_total,
                is_probable_not_open_yet, is_retired
            FROM locations
            WHERE id = $1
            """,
            location_id,
            timeout=DEFAULT_TIMEOUT_S,
        )
        after = dict(detail_row) if detail_row else None
        await audit_admin_action(
            admin.email,
            location_id,
            "admin_location_create",
            None,
            after,
            conn=conn,
        )

    if after is None:
        raise HTTPException(status_code=500, detail="failed to load created location")
    return AdminLocationDetail(**after)


@router.get("/{location_id}", response_model=AdminLocationDetail)
async def get_admin_location(
    location_id: int,
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminLocationDetail:
    sql = (
        """
        SELECT
            id, name, category, state, confidence_score, last_verified_at,
            address, notes, business_status, rating, user_ratings_total, is_probable_not_open_yet, is_retired
        FROM locations
        WHERE id = $1
        LIMIT 1
        """
    )
    row = await fetchrow(sql, int(location_id))
    if row is None:
        raise HTTPException(status_code=404, detail="location not found")
    return AdminLocationDetail(**dict(row))


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
               is_probable_not_open_yet, is_retired, confidence_score, last_verified_at,
               rating, user_ratings_total
        FROM locations WHERE id = $1 LIMIT 1
        """
    )
    before_row = await fetchrow(before_sql, int(location_id))
    if before_row is None:
        raise HTTPException(status_code=404, detail="location not found")
    before = dict(before_row)

    # 2) Update only allowed columns that are provided
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    force_flag = bool(patch.pop("force", False))
    requested_state_raw = patch.get("state")
    requested_state = (
        requested_state_raw.upper()
        if isinstance(requested_state_raw, str)
        else None
    )
    if requested_state is not None:
        patch["state"] = requested_state

    verifying = requested_state == "VERIFIED"
    was_retired = ((before.get("state") or "").upper() == "RETIRED") or bool(before.get("is_retired"))
    if verifying and was_retired and not force_flag:
        raise HTTPException(
            status_code=400,
            detail="Cannot verify a retired location without force flag.",
        )

    after: Optional[Dict[str, Any]] = None
    async with run_in_transaction() as conn:
        direct_updates: Dict[str, Any] = {}
        for key, val in patch.items():
            if verifying and key in {"state", "category", "confidence_score"}:
                continue
            direct_updates[key] = val

        if direct_updates:
            columns: List[str] = []
            values: List[Any] = []
            idx = 1
            for key, val in direct_updates.items():
                columns.append(f"{key} = ${idx}")
                values.append(val)
                idx += 1
            columns.append("last_verified_at = NOW()")
            set_clause = ", ".join(columns)
            sql = f"UPDATE locations SET {set_clause} WHERE id = ${idx}"
            values.append(int(location_id))
            await execute_with_conn(conn, sql, *values, timeout=DEFAULT_TIMEOUT_S)

        if verifying:
            category_override = patch.get("category", before.get("category"))
            confidence_override = (
                patch.get("confidence_score")
                if "confidence_score" in patch
                else before.get("confidence_score")
            )
            if confidence_override is None or float(confidence_override) < 0.9:
                confidence_override = 0.9
            reason_suffix = " (force)" if force_flag and was_retired else ""
            await update_location_classification(
                id=int(location_id),
                action="keep",
                category=category_override or "other",
                confidence_score=float(confidence_override),
                reason=f"admin verify{reason_suffix}",
                conn=conn,
                allow_resurrection=force_flag,
            )

        after_row = await fetchrow_with_conn(
            conn,
            """
            SELECT id, name, address, category, state, notes, business_status,
                   is_probable_not_open_yet, is_retired, confidence_score, last_verified_at,
                   rating, user_ratings_total
            FROM locations WHERE id = $1 LIMIT 1
            """,
            int(location_id),
            timeout=DEFAULT_TIMEOUT_S,
        )
        after = dict(after_row) if after_row else None

        await audit_admin_action(
            admin.email,
            int(location_id),
            "admin_update",
            before,
            after,
            conn=conn,
        )

    # 5) Return full detail
    detail_sql = (
        """
        SELECT
            id, name, category, state, confidence_score, last_verified_at,
            address, notes, business_status, rating, user_ratings_total, is_probable_not_open_yet, is_retired
        FROM locations
        WHERE id = $1
        LIMIT 1
        """
    )
    detail_row = await fetchrow(detail_sql, int(location_id))
    if detail_row is None:
        raise HTTPException(status_code=404, detail="location not found")
    return AdminLocationDetail(**dict(detail_row))


@router.patch("/bulk-update", response_model=AdminLocationsBulkUpdateResponse)
async def bulk_update_admin_locations(
    body: AdminLocationsBulkUpdateRequest,
    admin: AdminUser = Depends(verify_admin_user),
) -> AdminLocationsBulkUpdateResponse:
    """
    Apply a bulk mutation to multiple locations in a single request.

    Supports the following actions:
    - verify: promote locations to VERIFIED via update_location_classification helper
    - retire: set state to RETIRED and stamp last_verified_at = NOW()
    - adjust_confidence: update confidence_score (clamped to 0..1, rounded to 2 decimals)
    """

    if not body.ids:
        raise HTTPException(status_code=400, detail="provide at least one id")

    updated: List[int] = []
    errors: List[AdminLocationsBulkUpdateError] = []

    before_sql = """
        SELECT id, name, address, category, state, notes, business_status,
               is_probable_not_open_yet, is_retired, confidence_score, last_verified_at,
               rating, user_ratings_total
        FROM locations
        WHERE id = $1
        LIMIT 1
    """

    after_sql = """
        SELECT id, name, address, category, state, notes, business_status,
               is_probable_not_open_yet, is_retired, confidence_score, last_verified_at,
               rating, user_ratings_total
        FROM locations
        WHERE id = $1
        LIMIT 1
    """

    for location_id in body.ids:
        try:
            before_row = await fetchrow(
                before_sql,
                int(location_id),
                timeout=DEFAULT_TIMEOUT_S,
            )
        except (asyncio.TimeoutError, asyncpg.QueryCanceledError) as exc:
            errors.append(
                AdminLocationsBulkUpdateError(
                    id=int(location_id),
                    detail=f"timeout before snapshot: {str(exc)[:120]}",
                )
            )
            continue
        except Exception as exc:
            errors.append(
                AdminLocationsBulkUpdateError(
                    id=int(location_id),
                    detail=str(exc)[:180],
                )
            )
            continue

        if before_row is None:
            errors.append(
                AdminLocationsBulkUpdateError(
                    id=int(location_id),
                    detail="location not found",
                )
            )
            continue

        before = dict(before_row)
        allow_resurrection = False  # Initialize for logging access
        try:
            async with run_in_transaction() as conn:
                if body.action.type == "verify":
                    existing_conf = before.get("confidence_score")
                    confidence = (
                        float(existing_conf) if existing_conf is not None else 0.95
                    )
                    if confidence < 0.9:
                        confidence = 0.9
                    category = before.get("category") or "other"

                    force_flag = bool(getattr(body.action, "force", False))
                    clear_retired_flag = bool(getattr(body.action, "clear_retired", False))
                    allow_resurrection = force_flag or clear_retired_flag
                    was_retired = (
                        (before.get("state") or "").upper() == "RETIRED"
                        or bool(before.get("is_retired"))
                    )

                    await update_location_classification(
                        id=int(location_id),
                        action="keep",
                        category=category,
                        confidence_score=confidence,
                        reason="admin bulk verify" + (" (force)" if allow_resurrection and was_retired else ""),
                        conn=conn,
                        allow_resurrection=allow_resurrection,
                    )
                elif body.action.type == "retire":
                    await execute_with_conn(
                        conn,
                        """
                        UPDATE locations
                        SET state = 'RETIRED',
                            last_verified_at = NOW(),
                            is_retired = true
                        WHERE id = $1
                        """,
                        int(location_id),
                        timeout=DEFAULT_TIMEOUT_S,
                    )
                elif body.action.type == "adjust_confidence":
                    raw_value = float(body.action.value)
                    clamped = max(0.0, min(1.0, raw_value))
                    rounded = float(
                        Decimal(clamped).quantize(
                            Decimal("0.01"),
                            rounding=ROUND_HALF_UP,
                        )
                    )
                    await execute_with_conn(
                        conn,
                        """
                        UPDATE locations
                        SET confidence_score = $1,
                            last_verified_at = NOW()
                        WHERE id = $2
                        """,
                        rounded,
                        int(location_id),
                        timeout=DEFAULT_TIMEOUT_S,
                    )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"unsupported action: {body.action.type}",
                    )

                after_row = await fetchrow_with_conn(
                    conn,
                    after_sql,
                    int(location_id),
                    timeout=DEFAULT_TIMEOUT_S,
                )
                after = dict(after_row) if after_row else None

                action_name_map = {
                    "verify": "bulk_verify",
                    "retire": "bulk_retire",
                    "adjust_confidence": "bulk_adjust_confidence",
                }
                await audit_admin_action(
                    admin.email,
                    int(location_id),
                    action_name_map.get(
                        body.action.type, f"bulk_{body.action.type}"
                    ),
                    before,
                    after,
                    conn=conn,
                )
                updated.append(int(location_id))
        except (asyncio.TimeoutError, asyncpg.QueryCanceledError) as exc:
            logger.warning(
                "bulk_update_timeout",
                extra={
                    "location_id": int(location_id),
                    "action_type": body.action.type,
                    "allow_resurrection": allow_resurrection if body.action.type == "verify" else None,
                }
            )
            errors.append(
                AdminLocationsBulkUpdateError(
                    id=int(location_id),
                    detail=f"timeout during update: {str(exc)[:120]}",
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "bulk_update_error",
                extra={
                    "location_id": int(location_id),
                    "action_type": body.action.type,
                    "allow_resurrection": allow_resurrection if body.action.type == "verify" else None,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)[:200],
                }
            )
            errors.append(
                AdminLocationsBulkUpdateError(
                    id=int(location_id),
                    detail=str(exc)[:180],
                )
            )

    if updated or not errors:
        return AdminLocationsBulkUpdateResponse(
            ok=len(errors) == 0,
            updated=updated,
            errors=errors,
        )

    raise HTTPException(
        status_code=504,
        detail={
            "updated": updated,
            "errors": [err.model_dump() for err in errors],
        },
    )


@router.delete("/{location_id}", response_model=Dict[str, bool])
async def retire_admin_location(
    location_id: int,
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, bool]:
    # Before
    try:
        before_row = await fetchrow(
            "SELECT * FROM locations WHERE id = $1 LIMIT 1",
            int(location_id),
            timeout=DEFAULT_TIMEOUT_S,
        )
    except (asyncio.TimeoutError, asyncpg.QueryCanceledError):
        raise HTTPException(status_code=504, detail="retire before snapshot timed out")
    before = dict(before_row) if before_row else None

    # Soft retire + note
    sql = (
        """
        UPDATE locations
        SET state = 'RETIRED',
            is_retired = true,
            last_verified_at = NOW(),
            notes = COALESCE(notes, '')
                   || CASE WHEN notes IS NULL OR notes = '' THEN '' ELSE E'\\n' END
                   || $1
        WHERE id = $2
        """
    )
    note = f"[manual retire by {admin.email}]"
    try:
        async with run_in_transaction() as conn:
            await execute_with_conn(
                conn,
                sql,
                note,
                int(location_id),
                timeout=DEFAULT_TIMEOUT_S,
            )
            after_row = await fetchrow_with_conn(
                conn,
                "SELECT * FROM locations WHERE id = $1 LIMIT 1",
                int(location_id),
                timeout=DEFAULT_TIMEOUT_S,
            )
            after = dict(after_row) if after_row else None
            await audit_admin_action(
                admin.email,
                int(location_id),
                "admin_retire",
                before,
                after,
                conn=conn,
            )
    except (asyncio.TimeoutError, asyncpg.QueryCanceledError):
        raise HTTPException(status_code=504, detail="retire operation timed out")

    return {"ok": True}