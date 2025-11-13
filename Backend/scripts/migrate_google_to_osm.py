#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration script to replace legacy Google Places locations with matching OSM records.

Usage examples:
    python scripts/migrate_google_to_osm.py --dry-run --limit 50
    python scripts/migrate_google_to_osm.py --min-score 0.92
    python scripts/migrate_google_to_osm.py --validate-only
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from difflib import SequenceMatcher
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup so both `app.*` and `services.*` imports resolve when executed
# from the repository root or Backend/scripts.
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------------
# Imports from the application
# ---------------------------------------------------------------------------
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.core.request_id import with_run_id  # noqa: E402
from services.audit_service import audit_service  # noqa: E402
from services.db_service import (  # noqa: E402
    execute_with_conn,
    fetch,
    fetchrow,
    init_db_pool,
    run_in_transaction,
)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
configure_logging(service_name="migration")
logger = get_logger().bind(script="migrate_google_to_osm")

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
STATE_PRIORITY = {
    "CANDIDATE": 1,
    "PENDING_VERIFICATION": 2,
    "VERIFIED": 3,
    "SUSPENDED": 0,
    "RETIRED": -1,
}


@dataclass(frozen=True)
class LocationRow:
    id: int
    name: Optional[str]
    address: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    place_id: Optional[str]
    source: Optional[str]
    category: Optional[str]
    state: Optional[str]
    rating: Optional[float]
    user_ratings_total: Optional[int]
    confidence_score: Optional[float]
    notes: Optional[str]
    first_seen_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    last_verified_at: Optional[datetime]
    is_retired: Optional[bool]


@dataclass(frozen=True)
class MatchResult:
    osm: LocationRow
    score: float


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def normalize_name(value: Optional[str]) -> str:
    if not value:
        return ""
    condensed = " ".join(value.strip().lower().split())
    return condensed


def similarity_ratio(a: Optional[str], b: Optional[str]) -> float:
    a_norm = normalize_name(a)
    b_norm = normalize_name(b)
    if not a_norm or not b_norm:
        return 0.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def _to_float(value: Optional[Any]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float):
        return value
    if isinstance(value, (int, Decimal)):
        return float(value)
    try:
        return float(value)
    except Exception:  # pragma: no cover - defensive
        return None


def _to_int(value: Optional[Any]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    try:
        return int(value)
    except Exception:  # pragma: no cover - defensive
        return None


def _as_location_row(raw: Dict[str, Any]) -> LocationRow:
    return LocationRow(
        id=int(raw["id"]),
        name=raw.get("name"),
        address=raw.get("address"),
        lat=_to_float(raw.get("lat")),
        lng=_to_float(raw.get("lng")),
        place_id=raw.get("place_id"),
        source=raw.get("source"),
        category=raw.get("category"),
        state=(raw.get("state") or "").upper() or None,
        rating=_to_float(raw.get("rating")),
        user_ratings_total=_to_int(raw.get("user_ratings_total")),
        confidence_score=_to_float(raw.get("confidence_score")),
        notes=raw.get("notes"),
        first_seen_at=raw.get("first_seen_at"),
        last_seen_at=raw.get("last_seen_at"),
        last_verified_at=raw.get("last_verified_at"),
        is_retired=raw.get("is_retired"),
    )


def _location_summary(row: LocationRow) -> Dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "lat": row.lat,
        "lng": row.lng,
        "category": row.category,
        "state": row.state,
        "place_id": row.place_id,
        "rating": row.rating,
        "user_ratings_total": row.user_ratings_total,
        "confidence_score": row.confidence_score,
        "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
        "last_verified_at": row.last_verified_at.isoformat() if row.last_verified_at else None,
        "is_retired": row.is_retired,
    }


def _state_priority(value: Optional[str]) -> int:
    if not value:
        return 0
    return STATE_PRIORITY.get(value.upper(), 0)


def _format_migration_note(score: float) -> str:
    return f"[google_to_osm_migration] match_score={score:.3f}"


async def fetch_google_locations(limit: Optional[int]) -> List[LocationRow]:
    base_sql = """
        SELECT
            id, name, address, lat, lng, place_id, source, category, state,
            rating, user_ratings_total, confidence_score, notes,
            first_seen_at, last_seen_at, last_verified_at, is_retired
        FROM locations
        WHERE source = 'google_places'
        ORDER BY id
    """
    if limit is None:
        rows = await fetch(base_sql)
    else:
        rows = await fetch(base_sql + " LIMIT $1", int(limit))
    return [_as_location_row(dict(r)) for r in rows]


async def fetch_google_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    sql_google = "SELECT COUNT(*) AS c FROM locations WHERE source = 'google_places'"
    sql_osm = "SELECT COUNT(*) AS c FROM locations WHERE source = 'OSM_OVERPASS'"
    google_row = await fetchrow(sql_google)
    osm_row = await fetchrow(sql_osm)
    counts["google_remaining"] = int(dict(google_row or {}).get("c", 0))
    counts["osm_total"] = int(dict(osm_row or {}).get("c", 0))
    return counts


async def fetch_osm_candidates(lat: Optional[float], lng: Optional[float]) -> List[LocationRow]:
    if lat is None or lng is None:
        return []
    sql_exact = """
        SELECT
            id, name, address, lat, lng, place_id, source, category, state,
            rating, user_ratings_total, confidence_score, notes,
            first_seen_at, last_seen_at, last_verified_at, is_retired
        FROM locations
        WHERE source = 'OSM_OVERPASS'
          AND ROUND(CAST(lat AS numeric), 4) = ROUND(CAST($1 AS numeric), 4)
          AND ROUND(CAST(lng AS numeric), 4) = ROUND(CAST($2 AS numeric), 4)
    """
    rows = await fetch(sql_exact, float(lat), float(lng))
    if rows:
        return [_as_location_row(dict(r)) for r in rows]

    # Fallback: small bounding box (~1km)
    lat_min = float(lat) - 0.01
    lat_max = float(lat) + 0.01
    lng_min = float(lng) - 0.01
    lng_max = float(lng) + 0.01
    sql_bbox = """
        SELECT
            id, name, address, lat, lng, place_id, source, category, state,
            rating, user_ratings_total, confidence_score, notes,
            first_seen_at, last_seen_at, last_verified_at, is_retired
        FROM locations
        WHERE source = 'OSM_OVERPASS'
          AND lat BETWEEN $1 AND $2
          AND lng BETWEEN $3 AND $4
    """
    rows = await fetch(sql_bbox, lat_min, lat_max, lng_min, lng_max)
    return [_as_location_row(dict(r)) for r in rows]


async def find_best_osm_match(google_row: LocationRow, min_score: float) -> Optional[MatchResult]:
    candidates = await fetch_osm_candidates(google_row.lat, google_row.lng)
    best: Optional[MatchResult] = None
    for candidate in candidates:
        score = similarity_ratio(google_row.name, candidate.name)
        if best is None or score > best.score:
            best = MatchResult(osm=candidate, score=score)
    if best and best.score >= min_score:
        return best
    return None


def _choose_numeric_preference(
    osm_value: Optional[float], google_value: Optional[float], prefer_max: bool = True
) -> Optional[float]:
    values = [v for v in [osm_value, google_value] if v is not None]
    if not values:
        return None
    if prefer_max:
        return max(values)
    return values[0]


def _choose_state(osm_state: Optional[str], google_state: Optional[str]) -> Optional[str]:
    priority_pairs = [
        (osm_state, _state_priority(osm_state)),
        (google_state, _state_priority(google_state)),
    ]
    priority_pairs.sort(key=lambda item: item[1], reverse=True)
    return priority_pairs[0][0]


async def migrate_pair_in_transaction(
    *,
    google_row: LocationRow,
    match: MatchResult,
    min_score: float,
) -> Dict[str, Any]:
    osm_row = match.osm
    merged_details: Dict[str, Any] = {}

    async def _apply(conn) -> None:
        nonlocal merged_details
        osm_id = int(osm_row.id)
        google_id = int(google_row.id)

        # Repoint foreign keys
        await execute_with_conn(
            conn,
            "UPDATE tasks SET location_id = $1 WHERE location_id = $2",
            osm_id,
            google_id,
        )
        await execute_with_conn(
            conn,
            "UPDATE training_data SET location_id = $1 WHERE location_id = $2",
            osm_id,
            google_id,
        )
        await execute_with_conn(
            conn,
            "UPDATE ai_logs SET location_id = $1 WHERE location_id = $2",
            osm_id,
            google_id,
        )

        # Prepare merged metadata
        merged_category = osm_row.category or google_row.category
        merged_rating = _choose_numeric_preference(osm_row.rating, google_row.rating)
        merged_user_ratings = _choose_numeric_preference(
            _to_float(osm_row.user_ratings_total),
            _to_float(google_row.user_ratings_total),
        )
        if merged_user_ratings is not None:
            merged_user_ratings = int(merged_user_ratings)
        merged_confidence = _choose_numeric_preference(
            osm_row.confidence_score, google_row.confidence_score
        )
        merged_state = _choose_state(osm_row.state, google_row.state)
        merged_first_seen = min(
            dt for dt in [osm_row.first_seen_at, google_row.first_seen_at] if dt
        ) if any([osm_row.first_seen_at, google_row.first_seen_at]) else None
        merged_last_seen = max(
            dt for dt in [osm_row.last_seen_at, google_row.last_seen_at] if dt
        ) if any([osm_row.last_seen_at, google_row.last_seen_at]) else None
        merged_last_verified = max(
            dt for dt in [osm_row.last_verified_at, google_row.last_verified_at] if dt
        ) if any([osm_row.last_verified_at, google_row.last_verified_at]) else None
        merged_address = osm_row.address or google_row.address
        notes_addition_parts: List[str] = []
        if google_row.notes:
            notes_addition_parts.append(f"[google_notes] {google_row.notes.strip()}")
        notes_addition_parts.append(_format_migration_note(match.score))
        notes_addition = "\n".join(notes_addition_parts)

        merged_details = {
            "category": merged_category,
            "rating": merged_rating,
            "user_ratings_total": merged_user_ratings,
            "confidence_score": merged_confidence,
            "state": merged_state,
            "address": merged_address,
            "first_seen_at": merged_first_seen.isoformat()
            if merged_first_seen
            else None,
            "last_seen_at": merged_last_seen.isoformat() if merged_last_seen else None,
            "last_verified_at": merged_last_verified.isoformat()
            if merged_last_verified
            else None,
        }

        update_sql = """
            UPDATE locations
            SET
                category = COALESCE($1, category),
                rating = COALESCE($2, rating),
                user_ratings_total = COALESCE($3, user_ratings_total),
                confidence_score = COALESCE($4, confidence_score),
                state = COALESCE($5, state),
                address = COALESCE(address, $6),
                first_seen_at = COALESCE(
                    CASE
                        WHEN $7 IS NULL OR first_seen_at IS NULL THEN COALESCE(first_seen_at, $7)
                        ELSE LEAST(first_seen_at, $7)
                    END,
                    first_seen_at,
                    $7
                ),
                last_seen_at = COALESCE(
                    CASE
                        WHEN $8 IS NULL OR last_seen_at IS NULL THEN COALESCE(last_seen_at, $8)
                        ELSE GREATEST(last_seen_at, $8)
                    END,
                    last_seen_at,
                    $8
                ),
                last_verified_at = COALESCE(
                    CASE
                        WHEN $9 IS NULL OR last_verified_at IS NULL THEN COALESCE(last_verified_at, $9)
                        ELSE GREATEST(last_verified_at, $9)
                    END,
                    last_verified_at,
                    $9
                ),
                notes = CASE
                    WHEN $10 IS NULL OR $10 = '' THEN notes
                    WHEN notes IS NULL OR notes = '' THEN $10
                    ELSE notes || E'\n' || $10
                END
            WHERE id = $11
        """
        await execute_with_conn(
            conn,
            update_sql,
            merged_category,
            merged_rating,
            merged_user_ratings,
            merged_confidence,
            merged_state,
            merged_address,
            merged_first_seen,
            merged_last_seen,
            merged_last_verified,
            notes_addition,
            osm_id,
        )

        # Delete Google row
        await execute_with_conn(
            conn,
            "DELETE FROM locations WHERE id = $1",
            google_id,
        )

    async with run_in_transaction() as conn:
        await _apply(conn)

    return merged_details


ACTOR = "google_to_osm_migration_script"
ACTION_MIGRATION = "google_to_osm_migration"
ACTION_UNMATCHED = "google_to_osm_migration_unmatched"
ACTION_DRY_RUN = "google_to_osm_migration_dry_run"
ACTION_FAILURE = "google_to_osm_migration_failed"


async def log_migration_success(
    *,
    google_row: LocationRow,
    match: MatchResult,
    merged_details: Dict[str, Any],
    min_score: float,
) -> None:
    await audit_service.log(
        action_type=ACTION_MIGRATION,
        actor=ACTOR,
        location_id=int(match.osm.id),
        before={
            "google": _location_summary(google_row),
            "osm": _location_summary(match.osm),
        },
        after={
            "status": "migrated",
            "match_score": match.score,
            "merged_fields": merged_details,
        },
        is_success=True,
        meta={
            "min_score": min_score,
        },
    )


async def log_migration_failure(
    *,
    google_row: LocationRow,
    error: Exception,
    min_score: float,
) -> None:
    await audit_service.log(
        action_type=ACTION_FAILURE,
        actor=ACTOR,
        location_id=int(google_row.id),
        before={"google": _location_summary(google_row)},
        after={"status": "failed"},
        is_success=False,
        error_message=str(error),
        meta={"min_score": min_score},
    )


async def log_unmatched(
    *,
    google_row: LocationRow,
    min_score: float,
) -> None:
    await audit_service.log(
        action_type=ACTION_UNMATCHED,
        actor=ACTOR,
        location_id=int(google_row.id),
        before={"google": _location_summary(google_row)},
        after={"status": "unmatched"},
        is_success=False,
        meta={"min_score": min_score},
    )


async def log_dry_run_match(
    *,
    google_row: LocationRow,
    match: MatchResult,
    min_score: float,
) -> None:
    await audit_service.log(
        action_type=ACTION_DRY_RUN,
        actor=ACTOR,
        location_id=int(match.osm.id),
        before={
            "google": _location_summary(google_row),
            "osm": _location_summary(match.osm),
        },
        after={
            "status": "dry_run",
            "match_score": match.score,
        },
        is_success=True,
        meta={"min_score": min_score},
    )


async def run_migration(
    *,
    limit: Optional[int],
    min_score: float,
    dry_run: bool,
) -> Dict[str, Any]:
    counters: Dict[str, Any] = {
        "google_total": 0,
        "google_processed": 0,
        "matches_found": 0,
        "migrations_applied": 0,
        "unmatched": 0,
        "errors": 0,
    }

    google_rows = await fetch_google_locations(limit)
    counters["google_total"] = len(google_rows)
    logger.info("google_rows_loaded", count=len(google_rows))

    for google_row in google_rows:
        try:
            match = await find_best_osm_match(google_row, min_score)
            if not match:
                counters["unmatched"] += 1
                await log_unmatched(google_row=google_row, min_score=min_score)
                logger.info(
                    "google_location_unmatched",
                    google_id=google_row.id,
                    name=google_row.name,
                )
                counters["google_processed"] += 1
                continue

            counters["matches_found"] += 1
            logger.info(
                "google_location_matched",
                google_id=google_row.id,
                osm_id=match.osm.id,
                score=match.score,
            )

            if dry_run:
                await log_dry_run_match(
                    google_row=google_row,
                    match=match,
                    min_score=min_score,
                )
            else:
                merged_details = await migrate_pair_in_transaction(
                    google_row=google_row,
                    match=match,
                    min_score=min_score,
                )
                counters["migrations_applied"] += 1
                await log_migration_success(
                    google_row=google_row,
                    match=match,
                    merged_details=merged_details,
                    min_score=min_score,
                )

            counters["google_processed"] += 1
        except Exception as exc:  # pragma: no cover - defensive logging
            counters["errors"] += 1
            logger.exception(
                "migration_error",
                google_id=google_row.id,
                name=google_row.name,
                error=str(exc),
            )
            await log_migration_failure(
                google_row=google_row,
                error=exc,
                min_score=min_score,
            )

    post_counts = await fetch_google_counts()
    counters.update(post_counts)
    counters["dry_run"] = dry_run
    counters["min_score"] = min_score
    return counters


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate google_places locations to OSM-backed records."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of google_places rows to process (default: all).",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.9,
        help="Minimum similarity ratio (0..1) required to treat a match as valid.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migrations without performing any database writes.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only print remaining counts and exit without attempting migrations.",
    )
    return parser.parse_args()


async def main_async(args: argparse.Namespace) -> None:
    min_score = max(0.0, min(float(args.min_score), 1.0))
    await init_db_pool()

    if args.validate_only:
        counts = await fetch_google_counts()
        logger.info("validation_counts", counts=counts)
        print("Validation snapshot:", counts)
        return

    with with_run_id() as run_id:
        logger.info(
            "migration_started",
            limit=args.limit,
            min_score=min_score,
            dry_run=args.dry_run,
            run_id=str(run_id),
        )
        counters = await run_migration(
            limit=args.limit,
            min_score=min_score,
            dry_run=args.dry_run,
        )
        logger.info("migration_completed", counters=counters)
        print("Migration summary:", counters)


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:  # pragma: no cover - CLI convenience
        print("\nMigration interrupted by user.")


if __name__ == "__main__":
    main()
