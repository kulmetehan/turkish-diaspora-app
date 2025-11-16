from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
import os
from typing import Any, Dict, List, Optional, Tuple, Callable, Awaitable

import asyncpg
import yaml

from services.db_service import fetch
from app.models.metrics import (
    CityProgress,
    CityProgressData,
    CityProgressRotterdam,
    Discovery,
    Latency,
    MetricsSnapshot,
    Quality,
    WeeklyCandidatesItem,
    WorkerStatus,
    WorkerRunStatus,
)
# Import shared filter definition (single source of truth for Admin metrics and public API)
from app.core.location_filters import get_verified_filter_sql
from app.core.logging import get_logger

# Import load_cities_config from discovery_bot
try:
    from app.workers.discovery_bot import load_cities_config
except ImportError:
    # Fallback if import fails
    def load_cities_config() -> Dict[str, Any]:
        path = "Infra/config/cities.yml"
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config niet gevonden: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict) or "cities" not in data:
            raise ValueError("cities.yml is ongeldig: mist 'cities' root-key.")
        return data

WORKER_WINDOW_MINUTES = 60
DISCOVERY_STALE_HOURS = 6
VERIFY_STALE_HOURS = 2
VERIFICATION_CONSUMER_STALE_HOURS = 2
MONITOR_STALE_HOURS = 6
ALERT_ERR_RATE_THRESHOLD = 0.10
ALERT_GOOGLE_THRESHOLD = 5

logger = get_logger()


def _compute_city_bbox(city_key: str) -> Optional[Tuple[float, float, float, float]]:
    """
    Compute union bounding box from all districts for a given city.
    
    Returns (lat_min, lat_max, lng_min, lng_max) or None if city/districts not found.
    """
    try:
        cfg = load_cities_config()
        cities = cfg.get("cities", {})
        city_def = cities.get(city_key)
        
        if not city_def:
            return None
        
        districts = city_def.get("districts", {})
        if not districts:
            return None
        
        # Compute union bbox from all districts
        lat_mins = []
        lat_maxs = []
        lng_mins = []
        lng_maxs = []
        
        for district_name, district_data in districts.items():
            if isinstance(district_data, dict):
                if "lat_min" in district_data and "lat_max" in district_data:
                    lat_mins.append(float(district_data["lat_min"]))
                    lat_maxs.append(float(district_data["lat_max"]))
                if "lng_min" in district_data and "lng_max" in district_data:
                    lng_mins.append(float(district_data["lng_min"]))
                    lng_maxs.append(float(district_data["lng_max"]))
        
        if not lat_mins or not lat_maxs or not lng_mins or not lng_maxs:
            return None
        
        return (min(lat_mins), max(lat_maxs), min(lng_mins), max(lng_maxs))
    except Exception as e:
        logger.warning("failed_to_compute_city_bbox", city_key=city_key, error=str(e))
        return None


def _load_rotterdam_bbox():
    """
    Returns (lat_min, lat_max, lng_min, lng_max) for Rotterdam.

    In production we read Infra/config/cities.yml.
    In local development, that file may not exist,
    which currently crashes /admin/metrics/snapshot with FileNotFoundError.

    This fallback ensures the endpoint still works locally
    by returning a hardcoded Rotterdam bounding box if the file is missing.
    """
    bbox = _compute_city_bbox("rotterdam")
    if bbox:
        return bbox
    
    # Local dev fallback bbox for Rotterdam (approximate city extent)
    lat_min = 51.85
    lat_max = 51.98
    lng_min = 4.35
    lng_max = 4.55
    return (lat_min, lat_max, lng_min, lng_max)


async def _task_error_rate(window_minutes: int) -> float:
    sql_total = (
        """
        SELECT COUNT(*) AS n
        FROM ai_logs
        WHERE created_at >= NOW() - (($1::int || ' minutes')::interval)
        """
    )
    rows_total = await fetch(sql_total, int(window_minutes))
    total = int(rows_total[0]["n"]) if rows_total else 0

    sql_errors = (
        """
        SELECT COUNT(*) AS n
        FROM ai_logs
        WHERE created_at >= NOW() - (($1::int || ' minutes')::interval)
          AND (is_success = false OR error_message IS NOT NULL)
        """
    )
    rows_err = await fetch(sql_errors, int(window_minutes))
    err = int(rows_err[0]["n"]) if rows_err else 0

    if total == 0:
        return 0.0
    return float(err) / float(total)


async def _google429_bursts(window_minutes: int) -> int:
    sql = (
        """
        SELECT COUNT(*) AS n
        FROM ai_logs
        WHERE created_at >= NOW() - (($1::int || ' minutes')::interval)
          AND (
                error_message ILIKE '%429%'
             OR (raw_response ? 'statusCode' AND (raw_response->>'statusCode')::int = 429)
             OR (raw_response ? 'error' AND (raw_response->'error'->>'code') = 'RESOURCE_EXHAUSTED')
          )
        """
    )
    rows = await fetch(sql, int(window_minutes))
    return int(rows[0]["n"]) if rows else 0


async def _latency_stats(window_minutes: int) -> Tuple[int, int, int]:
    sql = (
        """
        WITH d AS (
          SELECT
            COALESCE(
              NULLIF((validated_output->>'duration_ms'), '')::int,
              NULLIF((raw_response->>'duration_ms'), '')::int
            ) AS dur
          FROM ai_logs
          WHERE created_at >= NOW() - (($1::int || ' minutes')::interval)
        )
        SELECT
          COALESCE(CAST(percentile_cont(0.5) WITHIN GROUP (ORDER BY dur) AS int), 0) AS p50,
          COALESCE(CAST(AVG(dur) AS int), 0) AS avg,
          COALESCE(CAST(MAX(dur) AS int), 0) AS max
        FROM d
        WHERE dur IS NOT NULL
        """
    )
    rows = await fetch(sql, int(window_minutes))
    if not rows:
        return (0, 0, 0)
    r = dict(rows[0])
    return (int(r.get("p50", 0)), int(r.get("avg", 0)), int(r.get("max", 0)))


async def _conversion_rate_14d() -> float:
    sql_total = (
        """
        SELECT COUNT(*) AS n
        FROM locations
        WHERE first_seen_at >= NOW() - INTERVAL '14 days'
        """
    )
    rows_total = await fetch(sql_total)
    total = int(rows_total[0]["n"]) if rows_total else 0

    sql_verified = (
        """
        SELECT COUNT(*) AS n
        FROM locations
        WHERE first_seen_at >= NOW() - INTERVAL '14 days'
          AND state = 'VERIFIED'
        """
    )
    rows_ver = await fetch(sql_verified)
    ver = int(rows_ver[0]["n"]) if rows_ver else 0

    if total == 0:
        return 0.0
    return float(ver) / float(total)


async def _weekly_candidates_series(weeks: int = 8) -> List[WeeklyCandidatesItem]:
    sql = (
        """
        SELECT (date_trunc('week', first_seen_at))::date AS week_start, COUNT(*)::int AS count
        FROM locations
        WHERE state = 'CANDIDATE'
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT $1
        """
    )
    rows = await fetch(sql, int(weeks))
    # Reverse to ascending by week
    items: List[WeeklyCandidatesItem] = []
    for r in reversed(rows or []):
        d = dict(r)
        items.append(WeeklyCandidatesItem(week_start=d["week_start"], count=int(d["count"])) )
    return items


async def _city_progress(city_key: str) -> Optional[CityProgressData]:
    """
    Calculate city progress metrics using shared verified filter definition.
    
    This function uses the same filters as the public locations API (see
    app.core.location_filters.get_verified_filter_sql) to maintain parity
    between Admin metrics and frontend map counts.
    
    Returns None if city bbox cannot be computed (no districts).
    """
    bbox = _compute_city_bbox(city_key)
    if not bbox:
        return None
    
    lat_min, lat_max, lng_min, lng_max = bbox
    bbox_tuple = (lat_min, lat_max, lng_min, lng_max)
    
    # Use shared filter definition (single source of truth)
    # This ensures Admin verified count matches public API count
    verified_filter_sql, verified_params = get_verified_filter_sql(bbox=bbox_tuple)
    
    # Count verified locations using shared filter
    sql_verified = f"SELECT COUNT(*)::int AS verified_count FROM locations WHERE {verified_filter_sql}"
    rows_verified = await fetch(sql_verified, *verified_params)
    verified = int(dict(rows_verified[0]).get("verified_count", 0)) if rows_verified else 0
    
    # Count candidates (still using bbox only for candidate count)
    sql_candidates = (
        """
        SELECT COUNT(*)::int AS candidate_count
        FROM locations
        WHERE state = 'CANDIDATE'
          AND lat BETWEEN $1 AND $2 AND lng BETWEEN $3 AND $4
        """
    )
    rows_candidates = await fetch(sql_candidates, float(lat_min), float(lat_max), float(lng_min), float(lng_max))
    candidates = int(dict(rows_candidates[0]).get("candidate_count", 0)) if rows_candidates else 0
    
    denom = verified + candidates
    coverage = (float(verified) / float(denom)) if denom > 0 else 0.0

    # Weekly growth: compare VERIFIED in current week vs prior week based on last_verified_at
    # Apply same shared filter to weekly growth query
    sql_weekly = f"""
        SELECT
          SUM(CASE WHEN last_verified_at >= date_trunc('week', NOW()) THEN 1 ELSE 0 END)::int AS cur,
          SUM(CASE WHEN last_verified_at < date_trunc('week', NOW())
                    AND last_verified_at >= date_trunc('week', NOW()) - INTERVAL '7 days'
                   THEN 1 ELSE 0 END)::int AS prev
        FROM locations
        WHERE {verified_filter_sql}
        """
    rows2 = await fetch(sql_weekly, *verified_params)
    cur = int(dict(rows2[0]).get("cur", 0)) if rows2 else 0
    prev = int(dict(rows2[0]).get("prev", 0)) if rows2 else 0
    growth = 0.0
    if prev > 0:
        growth = (float(cur - prev) / float(prev)) * 100.0
    elif cur > 0:
        growth = 100.0

    return CityProgressData(
        verified_count=verified,
        candidate_count=candidates,
        coverage_ratio=coverage,
        growth_weekly=growth,
    )


async def _rotterdam_progress() -> CityProgressRotterdam:
    """
    Calculate Rotterdam progress metrics using shared verified filter definition.
    
    This function uses the same filters as the public locations API (see
    app.core.location_filters.get_verified_filter_sql) to maintain parity
    between Admin metrics and frontend map counts.
    
    Maintained for backward compatibility.
    """
    progress = await _city_progress("rotterdam")
    if not progress:
        # Fallback to zero values if bbox cannot be computed
        return CityProgressRotterdam(
            verified_count=0,
            candidate_count=0,
            coverage_ratio=0.0,
            growth_weekly=0.0,
        )
    
    return CityProgressRotterdam(
        verified_count=progress.verified_count,
        candidate_count=progress.candidate_count,
        coverage_ratio=progress.coverage_ratio,
        growth_weekly=progress.growth_weekly,
    )


def _build_notes(lines: List[str]) -> Optional[str]:
    cleaned = [line for line in lines if line]
    return "\n".join(cleaned) if cleaned else None


def _compute_diagnosis_code(
    worker_id: str,
    status: str,
    last_run: Optional[datetime],
    metrics: Dict[str, Any]
) -> Optional[str]:
    """
    Compute machine-readable diagnosis code based on worker status and metrics.
    
    Args:
        worker_id: Worker identifier (e.g., "discovery_bot", "verify_locations_bot")
        status: Current status ("ok", "warning", "error", "unknown")
        last_run: Last run timestamp or None
        metrics: Dictionary with worker-specific metrics (quota_info, processed_count, error_count, etc.)
    
    Returns:
        Diagnosis code string or None if status is OK
    """
    if status == "ok":
        return "OK"
    
    if last_run is None and status == "unknown":
        return "NEVER_RAN"
    
    # Worker-specific diagnosis logic
    if worker_id == "discovery_bot":
        overpass_errors = metrics.get("overpass_error_count_last_60m", 0)
        if overpass_errors and overpass_errors > 10:
            return "OSM_ERROR_RATE_HIGH"
        
        # Check for no inserts in last 30 days (if metrics include this)
        total_inserted_30d = metrics.get("total_inserted_30d", None)
        total_runs_30d = metrics.get("total_runs_30d", None)
        if total_inserted_30d is not None and total_runs_30d is not None:
            if total_inserted_30d == 0 and total_runs_30d > 0:
                return "NO_NEW_INSERTS_LAST_30_DAYS"
    
    elif worker_id == "verify_locations_bot":
        processed = metrics.get("processed_count", 0) or 0
        error_count = metrics.get("error_count", 0) or 0
        if processed > 0:
            error_ratio = error_count / processed if processed else 0.0
            if error_ratio >= 0.5 and processed >= 4:
                return "AI_ERROR_RATE_HIGH"
    
    elif worker_id == "verification_consumer":
        processed = metrics.get("processed_count", 0) or 0
        error_count = metrics.get("error_count", 0) or 0
        if processed > 0:
            error_ratio = error_count / processed if processed else 0.0
            if error_ratio >= 0.5 and processed >= 4:
                return "AI_ERROR_RATE_HIGH"
    
    elif worker_id == "monitor_bot":
        pending = metrics.get("pending_queue", 0) or 0
        processing = metrics.get("processing_queue", 0) or 0
        if pending > 500 and pending > 2 * processing:
            return "TASK_QUEUE_BACKLOG"
    
    elif worker_id == "alert_bot":
        err_rate = metrics.get("error_rate", 0.0)
        if err_rate >= ALERT_ERR_RATE_THRESHOLD * 2:
            return "AI_ERROR_RATE_HIGH"
        g429 = metrics.get("google429_last_60m", 0) or 0
        if g429 >= ALERT_GOOGLE_THRESHOLD:
            return "AI_ERROR_RATE_HIGH"
    
    # Check for missing metrics data (table missing case)
    if "METRICS_DATA_MISSING" in str(metrics.get("notes", "")):
        return "METRICS_DATA_MISSING"
    
    # Fallback for unknown status
    if status == "unknown":
        return "UNKNOWN"
    
    # Default fallback
    return None


async def _discovery_worker_status() -> WorkerStatus:
    sql_latest_run = """
        SELECT
            id,
            started_at,
            finished_at,
            counters
        FROM discovery_runs
        ORDER BY COALESCE(finished_at, started_at) DESC
        LIMIT 1
    """
    now = datetime.now(timezone.utc)
    quota_info: Dict[str, Optional[int]] = {}

    try:
        rows = await fetch(sql_latest_run)

        sql_overpass = """
            SELECT
                COALESCE(COUNT(*) FILTER (
                    WHERE status_code = 429
                ), 0)::int AS overpass_429_last_60m,
                COALESCE(COUNT(*) FILTER (
                    WHERE (status_code >= 500 OR status_code IS NULL OR error_message IS NOT NULL)
                ), 0)::int AS overpass_error_count_last_60m
            FROM overpass_calls
            WHERE ts >= NOW() - (($1::int || ' minutes')::interval)
        """
        overpass_rows = await fetch(sql_overpass, int(WORKER_WINDOW_MINUTES))
        if overpass_rows:
            overpass_data = dict(overpass_rows[0])
            quota_info = {
                "overpass_429_last_60m": int(overpass_data.get("overpass_429_last_60m") or 0),
                "overpass_error_count_last_60m": int(overpass_data.get("overpass_error_count_last_60m") or 0),
            }

        # Check for 30-day insert statistics
        sql_30d = """
            SELECT 
                COALESCE(SUM((counters->>'inserted')::int), 0)::int AS total_inserted,
                COUNT(*)::int AS total_runs
            FROM discovery_runs
            WHERE started_at >= NOW() - INTERVAL '30 days'
        """
        rows_30d = await fetch(sql_30d)
        total_inserted_30d = 0
        total_runs_30d = 0
        if rows_30d:
            row_30d = dict(rows_30d[0])
            total_inserted_30d = int(row_30d.get("total_inserted") or 0)
            total_runs_30d = int(row_30d.get("total_runs") or 0)

        if not rows:
            metrics = {
                "overpass_error_count_last_60m": quota_info.get("overpass_error_count_last_60m", 0),
                "total_inserted_30d": total_inserted_30d,
                "total_runs_30d": total_runs_30d,
            }
            diagnosis_code = _compute_diagnosis_code("discovery_bot", "unknown", None, metrics)
            return WorkerStatus(
                id="discovery_bot",
                label="DiscoveryBot",
                last_run=None,
                duration_seconds=None,
                processed_count=None,
                error_count=None,
                status="unknown",
                window_label="last run",
                quota_info=quota_info or None,
                notes="No discovery runs recorded yet.",
                diagnosis_code=diagnosis_code,
            )

        record = dict(rows[0])
        started_at = record.get("started_at")
        finished_at = record.get("finished_at")
        counters_raw = record.get("counters") or {}
        counters = counters_raw if isinstance(counters_raw, dict) else {}

        processed = int(counters.get("discovered") or counters.get("inserted") or 0)
        errors = int(counters.get("failed") or 0)
        last_run = finished_at or started_at

        duration_seconds: Optional[float] = None
        if isinstance(started_at, datetime) and isinstance(finished_at, datetime):
            duration_seconds = max((finished_at - started_at).total_seconds(), 0.0)

        status = "ok"
        notes: List[str] = ["Processed count uses discovery_runs.counters.discovered."]

        if last_run is None:
            status = "unknown"
            notes.append("Run timestamp unavailable.")
        else:
            if (now - last_run) > timedelta(hours=DISCOVERY_STALE_HOURS):
                status = "warning"
                notes.append(f"Last run more than {DISCOVERY_STALE_HOURS}h ago.")
            if processed == 0:
                notes.append("No locations discovered in last run.")
                if status == "ok":
                    status = "warning"
            if errors > 0:
                notes.append(f"{errors} failures recorded in last run.")
                status = "error"

        # Compute diagnosis code
        metrics = {
            "overpass_error_count_last_60m": quota_info.get("overpass_error_count_last_60m", 0),
            "total_inserted_30d": total_inserted_30d,
            "total_runs_30d": total_runs_30d,
            "processed_count": processed,
            "error_count": errors,
        }
        diagnosis_code = _compute_diagnosis_code("discovery_bot", status, last_run, metrics)

        return WorkerStatus(
            id="discovery_bot",
            label="DiscoveryBot",
            last_run=last_run,
            duration_seconds=duration_seconds,
            processed_count=processed,
            error_count=errors,
            status=status,  # type: ignore[arg-type]
            window_label="last run",
            quota_info=quota_info or None,
            notes=_build_notes(notes),
            diagnosis_code=diagnosis_code,
        )
    except asyncpg.exceptions.UndefinedTableError as exc:
        logger.warning(
            "worker_status_table_missing",
            worker_id="discovery_bot",
            table="discovery_runs",
            error=str(exc),
        )
        metrics = {"notes": "METRICS_DATA_MISSING"}
        diagnosis_code = _compute_diagnosis_code("discovery_bot", "unknown", None, metrics)
        return WorkerStatus(
            id="discovery_bot",
            label="DiscoveryBot",
            last_run=None,
            duration_seconds=None,
            processed_count=None,
            error_count=None,
            status="unknown",
            window_label=None,
            quota_info=None,
            notes="discovery_runs table is missing; run migrations to enable DiscoveryBot metrics.",
            diagnosis_code=diagnosis_code,
        )


async def _verify_locations_status() -> WorkerStatus:
    now = datetime.now(timezone.utc)

    sql_last_run = """
        SELECT MAX(created_at) AS last_run
        FROM ai_logs
        WHERE action_type = 'verify_locations.classified'
    """
    sql_window = """
        SELECT
            COALESCE(COUNT(*), 0)::int AS processed_count,
            COALESCE(COUNT(*) FILTER (WHERE COALESCE(is_success, true) = false OR error_message IS NOT NULL), 0)::int AS error_count,
            MIN(created_at) AS first_ts,
            MAX(created_at) AS last_ts
        FROM ai_logs
        WHERE action_type = 'verify_locations.classified'
          AND created_at >= NOW() - (($1::int || ' minutes')::interval)
    """

    last_run_rows = await fetch(sql_last_run)
    last_run = None
    if last_run_rows:
        last_run = last_run_rows[0].get("last_run")

    window_rows = await fetch(sql_window, int(WORKER_WINDOW_MINUTES))
    processed_recent = 0
    error_recent = 0
    first_ts = None
    last_ts = None
    if window_rows:
        row = window_rows[0]
        processed_recent = int(row.get("processed_count") or 0)
        error_recent = int(row.get("error_count") or 0)
        first_ts = row.get("first_ts")
        last_ts = row.get("last_ts")

    duration_seconds: Optional[float] = None
    if isinstance(first_ts, datetime) and isinstance(last_ts, datetime) and first_ts != last_ts:
        duration_seconds = max((last_ts - first_ts).total_seconds(), 0.0)

    status = "ok"
    notes: List[str] = ["Counts derived from ai_logs (action_type='verify_locations.classified')."]

    if last_run is None:
        status = "unknown"
        notes.append("No verification runs recorded yet.")
    else:
        if (now - last_run) > timedelta(hours=VERIFY_STALE_HOURS):
            status = "warning"
            notes.append(f"Last verification more than {VERIFY_STALE_HOURS}h ago.")
    if processed_recent == 0:
        notes.append("0 items processed in the last 60 minutes.")
        if status == "ok":
            status = "warning"
    else:
        error_ratio = error_recent / processed_recent if processed_recent else 0.0
        if error_recent >= processed_recent // 2 and processed_recent >= 4:
            status = "error"
            notes.append(f"High failure ratio ({error_recent}/{processed_recent}) in the last 60 minutes.")
        elif error_recent > 0:
            status = "warning"
            notes.append(f"{error_recent} failures in the last 60 minutes.")

    # Compute diagnosis code
    metrics = {
        "processed_count": processed_recent,
        "error_count": error_recent,
    }
    diagnosis_code = _compute_diagnosis_code("verify_locations_bot", status, last_run, metrics)

    return WorkerStatus(
        id="verify_locations_bot",
        label="VerifyLocationsBot",
        last_run=last_run,
        duration_seconds=duration_seconds,
        processed_count=processed_recent,
        error_count=error_recent,
        status=status,  # type: ignore[arg-type]
        window_label=f"last {WORKER_WINDOW_MINUTES} min",
        quota_info=None,
        notes=_build_notes(notes),
        diagnosis_code=diagnosis_code,
    )


async def _task_verifier_status() -> WorkerStatus:
    sql = """
        SELECT
            MAX(last_verified_at) AS last_run,
            COALESCE(COUNT(*) FILTER (
                WHERE last_verified_at >= NOW() - (($1::int || ' minutes')::interval)
                  AND notes ILIKE '%task_verifier%'
            ), 0)::int AS processed_recent,
            COALESCE(COUNT(*) FILTER (
                WHERE last_verified_at >= NOW() - (($1::int || ' minutes')::interval)
                  AND notes ILIKE '%not auto-promoted%'
            ), 0)::int AS skipped_recent,
            COALESCE(COUNT(*) FILTER (
                WHERE last_verified_at >= NOW() - (($1::int || ' minutes')::interval)
                  AND notes ILIKE '%auto by task_verifier heuristic%'
            ), 0)::int AS promoted_recent
        FROM locations
        WHERE notes ILIKE '%task_verifier%'
    """
    rows = await fetch(sql, int(WORKER_WINDOW_MINUTES))

    last_run = None
    processed_recent = 0
    skipped_recent = 0
    promoted_recent = 0
    if rows:
        rec = rows[0]
        last_run = rec.get("last_run")
        processed_recent = int(rec.get("processed_recent") or 0)
        skipped_recent = int(rec.get("skipped_recent") or 0)
        promoted_recent = int(rec.get("promoted_recent") or 0)

    status = "ok"
    notes: List[str] = ["Derived from locations.notes entries created by task_verifier."]

    if last_run is None:
        status = "unknown"
        notes.append("No task_verifier activity detected.")
    else:
        if processed_recent == 0:
            status = "warning"
            notes.append("0 candidates processed in the last 60 minutes.")
        if skipped_recent > 0 and promoted_recent == 0:
            status = "warning"
            notes.append("All recent checks resulted in non-promotions.")

    # Compute diagnosis code
    metrics = {
        "processed_count": processed_recent,
        "error_count": skipped_recent,
    }
    diagnosis_code = _compute_diagnosis_code("task_verifier_bot", status, last_run, metrics)

    return WorkerStatus(
        id="task_verifier_bot",
        label="Self-Verify Bot",
        last_run=last_run,
        duration_seconds=None,
        processed_count=processed_recent,
        error_count=skipped_recent,
        status=status,  # type: ignore[arg-type]
        window_label=f"last {WORKER_WINDOW_MINUTES} min",
        quota_info=None,
        notes=_build_notes(notes),
        diagnosis_code=diagnosis_code,
    )


async def _monitor_bot_status() -> WorkerStatus:
    sql_activity = """
        SELECT
            MAX(created_at) AS last_created,
            COALESCE(COUNT(*) FILTER (
                WHERE created_at >= NOW() - (($1::int || ' minutes')::interval)
            ), 0)::int AS created_recent,
            COALESCE(COUNT(*) FILTER (
                WHERE UPPER(status) = 'FAILED'
                  AND COALESCE(last_attempted_at, created_at) >= NOW() - (($1::int || ' minutes')::interval)
            ), 0)::int AS failed_recent
        FROM tasks
        WHERE task_type = 'VERIFICATION'
    """
    sql_backlog = """
        SELECT
            COALESCE(COUNT(*) FILTER (WHERE UPPER(status) = 'PENDING'), 0)::int AS pending_count,
            COALESCE(COUNT(*) FILTER (WHERE UPPER(status) = 'PROCESSING'), 0)::int AS processing_count
        FROM tasks
        WHERE task_type = 'VERIFICATION'
    """
    activity_rows = await fetch(sql_activity, int(WORKER_WINDOW_MINUTES))
    backlog_rows = await fetch(sql_backlog)

    last_created = None
    created_recent = 0
    failed_recent = 0
    if activity_rows:
        activity = activity_rows[0]
        last_created = activity.get("last_created")
        created_recent = int(activity.get("created_recent") or 0)
        failed_recent = int(activity.get("failed_recent") or 0)

    pending_count = 0
    processing_count = 0
    if backlog_rows:
        backlog = backlog_rows[0]
        pending_count = int(backlog.get("pending_count") or 0)
        processing_count = int(backlog.get("processing_count") or 0)

    status = "ok"
    notes: List[str] = ["Monitors verification queue health via tasks table."]
    if last_created is None:
        status = "unknown"
        notes.append("No verification tasks created yet.")
    else:
        if (datetime.now(timezone.utc) - last_created) > timedelta(hours=MONITOR_STALE_HOURS):
            status = "warning"
            notes.append(f"No verification tasks created in the last {MONITOR_STALE_HOURS}h.")
        if created_recent == 0:
            notes.append("0 tasks enqueued in the last 60 minutes.")
            if status == "ok":
                status = "warning"
        if failed_recent > 0:
            notes.append(f"{failed_recent} enqueue attempts failed in the last 60 minutes.")
            status = "error" if failed_recent >= 5 else "warning"
        if pending_count > 500:
            notes.append(f"High pending queue ({pending_count}).")
            if status == "ok":
                status = "warning"

    quota_info = {
        "pending_queue": pending_count,
        "processing_queue": processing_count,
    }

    # Compute diagnosis code
    metrics = {
        "pending_queue": pending_count,
        "processing_queue": processing_count,
        "processed_count": created_recent,
        "error_count": failed_recent,
    }
    diagnosis_code = _compute_diagnosis_code("monitor_bot", status, last_created, metrics)

    return WorkerStatus(
        id="monitor_bot",
        label="MonitorBot",
        last_run=last_created,
        duration_seconds=None,
        processed_count=created_recent,
        error_count=failed_recent,
        status=status,  # type: ignore[arg-type]
        window_label=f"last {WORKER_WINDOW_MINUTES} min",
        quota_info=quota_info,
        notes=_build_notes(notes),
        diagnosis_code=diagnosis_code,
    )


async def _verification_consumer_status() -> WorkerStatus:
    now = datetime.now(timezone.utc)

    sql_last_run = """
        SELECT MAX(created_at) AS last_run
        FROM ai_logs
        WHERE action_type = 'verification_consumer.classified'
    """
    sql_window = """
        SELECT
            COALESCE(COUNT(*), 0)::int AS processed_count,
            COALESCE(COUNT(*) FILTER (WHERE COALESCE(is_success, true) = false OR error_message IS NOT NULL), 0)::int AS error_count,
            MIN(created_at) AS first_ts,
            MAX(created_at) AS last_ts
        FROM ai_logs
        WHERE action_type = 'verification_consumer.classified'
          AND created_at >= NOW() - (($1::int || ' minutes')::interval)
    """

    last_run_rows = await fetch(sql_last_run)
    last_run = None
    if last_run_rows:
        last_run = last_run_rows[0].get("last_run")

    window_rows = await fetch(sql_window, int(WORKER_WINDOW_MINUTES))
    processed_recent = 0
    error_recent = 0
    first_ts = None
    last_ts = None
    if window_rows:
        row = window_rows[0]
        processed_recent = int(row.get("processed_count") or 0)
        error_recent = int(row.get("error_count") or 0)
        first_ts = row.get("first_ts")
        last_ts = row.get("last_ts")

    duration_seconds: Optional[float] = None
    if isinstance(first_ts, datetime) and isinstance(last_ts, datetime) and first_ts != last_ts:
        duration_seconds = max((last_ts - first_ts).total_seconds(), 0.0)

    status = "ok"
    notes: List[str] = ["Consumes verification tasks from the queue and classifies them via OpenAI."]

    if last_run is None:
        status = "unknown"
        notes.append("No verification consumer runs recorded yet.")
    else:
        if (now - last_run) > timedelta(hours=VERIFICATION_CONSUMER_STALE_HOURS):
            status = "warning"
            notes.append(f"Last run more than {VERIFICATION_CONSUMER_STALE_HOURS}h ago.")
    if processed_recent == 0:
        notes.append("0 items processed in the last 60 minutes.")
        if status == "ok":
            status = "warning"
    else:
        error_ratio = error_recent / processed_recent if processed_recent else 0.0
        if error_recent >= processed_recent // 2 and processed_recent >= 4:
            status = "error"
            notes.append(f"High failure ratio ({error_recent}/{processed_recent}) in the last 60 minutes.")
        elif error_recent > 0:
            status = "warning"
            notes.append(f"{error_recent} failures in the last 60 minutes.")

    # Compute diagnosis code
    metrics = {
        "processed_count": processed_recent,
        "error_count": error_recent,
    }
    diagnosis_code = _compute_diagnosis_code("verification_consumer", status, last_run, metrics)

    return WorkerStatus(
        id="verification_consumer",
        label="Tasks Consumer",
        last_run=last_run,
        duration_seconds=duration_seconds,
        processed_count=processed_recent,
        error_count=error_recent,
        status=status,  # type: ignore[arg-type]
        window_label=f"last {WORKER_WINDOW_MINUTES} min",
        quota_info=None,
        notes=_build_notes(notes),
        diagnosis_code=diagnosis_code,
    )


async def _alert_bot_status(err_rate: float, g429: int) -> WorkerStatus:
    triggered = 0
    notes: List[str] = ["Status reflects current error rate and Google 429 bursts."]

    status = "ok"
    if err_rate >= ALERT_ERR_RATE_THRESHOLD:
        triggered += 1
        notes.append(f"Task error rate {err_rate:.2%} exceeds {ALERT_ERR_RATE_THRESHOLD:.0%} threshold.")
        status = "warning"
    if err_rate >= (ALERT_ERR_RATE_THRESHOLD * 2):
        status = "error"

    if g429 >= ALERT_GOOGLE_THRESHOLD:
        triggered += 1
        notes.append(f"{g429} Google 429 events in last 60 minutes (threshold {ALERT_GOOGLE_THRESHOLD}).")
        status = "error"

    # Compute diagnosis code
    metrics = {
        "error_rate": err_rate,
        "google429_last_60m": g429,
    }
    diagnosis_code = _compute_diagnosis_code("alert_bot", status, datetime.now(timezone.utc), metrics)

    return WorkerStatus(
        id="alert_bot",
        label="AlertBot",
        last_run=datetime.now(timezone.utc),
        duration_seconds=None,
        processed_count=None,
        error_count=triggered,
        status=status,  # type: ignore[arg-type]
        window_label=f"last {WORKER_WINDOW_MINUTES} min",
        quota_info={"google429_last_60m": g429},
        notes=_build_notes(notes),
        diagnosis_code=diagnosis_code,
    )


async def _worker_statuses(err_rate: float, g429: int) -> List[WorkerStatus]:
    statuses: List[WorkerStatus] = []

    async def safe_call(worker_id: str, label: str, fn: Callable[[], Awaitable[WorkerStatus]]) -> None:
        try:
            ws = await fn()
        except asyncpg.exceptions.UndefinedTableError as exc:
            logger.warning(
                "worker_status_table_missing_unexpected",
                worker_id=worker_id,
                error=str(exc),
            )
            metrics = {"notes": "METRICS_DATA_MISSING"}
            diagnosis_code = _compute_diagnosis_code(worker_id, "unknown", None, metrics)
            ws = WorkerStatus(
                id=worker_id,
                label=label,
                last_run=None,
                duration_seconds=None,
                processed_count=None,
                error_count=None,
                status="unknown",
                window_label=None,
                quota_info=None,
                notes="Table missing; run migrations to enable worker metrics.",
                diagnosis_code=diagnosis_code,
            )
        except Exception:
            logger.exception("worker_status_failed", worker_id=worker_id)
            metrics = {}
            diagnosis_code = _compute_diagnosis_code(worker_id, "error", None, metrics)
            ws = WorkerStatus(
                id=worker_id,
                label=label,
                last_run=None,
                duration_seconds=None,
                processed_count=None,
                error_count=None,
                status="error",
                window_label=None,
                quota_info=None,
                notes="Failed to compute worker status; see logs.",
                diagnosis_code=diagnosis_code,
            )
        statuses.append(ws)

    await safe_call("discovery_bot", "DiscoveryBot", _discovery_worker_status)
    await safe_call("verify_locations_bot", "VerifyLocationsBot", _verify_locations_status)
    await safe_call("task_verifier_bot", "Self-Verify Bot", _task_verifier_status)
    await safe_call("monitor_bot", "MonitorBot", _monitor_bot_status)
    await safe_call("verification_consumer", "Tasks Consumer", _verification_consumer_status)
    await safe_call("alert_bot", "AlertBot", lambda: _alert_bot_status(err_rate, g429))

    return statuses


async def _active_worker_runs(limit: int = 10) -> List[WorkerRunStatus]:
    sql = """
        SELECT id, bot, city, category, status, progress, started_at
        FROM worker_runs
        WHERE status IN ('pending', 'running')
        ORDER BY created_at DESC
        LIMIT $1
    """
    try:
        rows = await fetch(sql, int(limit))
    except asyncpg.UndefinedTableError:
        logger.warning("worker_runs_table_missing", table="worker_runs")
        return []
    runs: List[WorkerRunStatus] = []
    for row in rows or []:
        rec = dict(row)
        runs.append(
            WorkerRunStatus(
                id=rec.get("id"),
                bot=str(rec.get("bot") or ""),
                city=rec.get("city"),
                category=rec.get("category"),
                status=str(rec.get("status") or ""),
                progress=int(rec.get("progress") or 0),
                started_at=rec.get("started_at"),
            )
        )
    return runs


async def generate_metrics_snapshot() -> MetricsSnapshot:
    # Quality
    conv_14d = await _conversion_rate_14d()
    err_rate = await _task_error_rate(60)
    g429 = await _google429_bursts(60)

    # Latency
    p50, avg, mx = await _latency_stats(60)

    # Discovery
    weekly = await _weekly_candidates_series(8)
    latest_count = weekly[-1].count if weekly else 0

    # City progress
    rot = await _rotterdam_progress()

    workers = await _worker_statuses(err_rate, g429)
    current_runs = await _active_worker_runs()

    return MetricsSnapshot(
        city_progress=CityProgress(rotterdam=rot),
        quality=Quality(
            conversion_rate_verified_14d=conv_14d,
            task_error_rate_60m=err_rate,
            google429_last60m=g429,
        ),
        discovery=Discovery(new_candidates_per_week=latest_count),
        latency=Latency(p50_ms=p50, avg_ms=avg, max_ms=mx),
        weekly_candidates=weekly,
        workers=workers,
        current_runs=current_runs,
    )


