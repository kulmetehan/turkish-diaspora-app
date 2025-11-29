from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
import os
from typing import Any, Dict, List, Optional, Tuple, Callable, Awaitable

import asyncpg
import yaml

from services.db_service import fetch, fetchrow
from services.ai_config_service import get_ai_config, initialize_ai_config
from services.news_feed_rules import FeedThresholds, FeedType, is_in_feed, thresholds_from_config
from app.models.metrics import (
    CategoryHealth,
    CategoryHealthResponse,
    CityProgress,
    CityProgressData,
    CityProgressRotterdam,
    Discovery,
    EventMetricsSnapshot,
    EventPerDayItem,
    EventEnrichmentMetrics,
    EventDedupeMetrics,
    EventCategoryBreakdown,
    EventSourceStat,
    Latency,
    LocationStateBucket,
    LocationStateMetrics,
    MetricsSnapshot,
    NewsErrorMetrics,
    NewsLabelCount,
    NewsMetricsSnapshot,
    NewsPerDayItem,
    NewsTrendingMetrics,
    Quality,
    StaleCandidates,
    WeeklyCandidatesItem,
    WorkerStatus,
    WorkerRunStatus,
)
# Import shared filter definition (single source of truth for Admin metrics and public API)
from app.core.location_filters import get_verified_filter_sql
from app.core.logging import get_logger
from app.models.categories import get_discoverable_categories
from services.news_service import TRENDING_WINDOW_HOURS, list_trending_news

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
NEWS_TRENDING_SAMPLE_LIMIT = 3
EVENT_CANDIDATE_ACTIVE_STATES: Tuple[str, ...] = ("candidate", "verified", "published")

# Category Health thresholds for Turkish-first strategy
CATEGORY_HEALTH_CRITICAL_COVERAGE_THRESHOLD = 5.0
CATEGORY_HEALTH_DEGRADED_COVERAGE_THRESHOLD = 10.0
CATEGORY_HEALTH_WARNING_COVERAGE_THRESHOLD = 20.0
CATEGORY_HEALTH_DEGRADED_PRECISION_THRESHOLD = 15.0
CATEGORY_HEALTH_WARNING_PRECISION_THRESHOLD = 25.0

logger = get_logger()


async def _news_trending_metrics(
    limit: int = NEWS_TRENDING_SAMPLE_LIMIT,
) -> Optional[NewsTrendingMetrics]:
    try:
        items, total = await list_trending_news(
            limit=limit,
            offset=0,
            window_hours=TRENDING_WINDOW_HOURS,
        )
    except Exception as exc:
        logger.warning("news_trending_metrics_failed", error=str(exc))
        return None

    return NewsTrendingMetrics(
        window_hours=TRENDING_WINDOW_HOURS,
        eligible_count=total,
        sample_titles=[item.title for item in items],
    )


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


async def _stale_candidates_metrics(days: int = 7) -> Dict[str, Any]:
    """
    Count stale CANDIDATE records (older than N days), grouped by source.
    
    Returns dict with:
    - total_stale: Total count of stale CANDIDATE records
    - by_source: Dict mapping source -> count
    - by_city: Dict mapping city_key -> count (computed via bbox)
    """
    sql_total = (
        """
        SELECT COUNT(*)::int AS total_stale
        FROM locations
        WHERE state = 'CANDIDATE'
          AND first_seen_at < NOW() - (($1::int || ' days')::interval)
        """
    )
    rows_total = await fetch(sql_total, int(days))
    total_stale = int(rows_total[0]["total_stale"]) if rows_total else 0
    
    sql_by_source = (
        """
        SELECT source, COUNT(*)::int AS count
        FROM locations
        WHERE state = 'CANDIDATE'
          AND first_seen_at < NOW() - (($1::int || ' days')::interval)
        GROUP BY source
        ORDER BY count DESC
        """
    )
    rows_by_source = await fetch(sql_by_source, int(days))
    by_source: Dict[str, int] = {}
    for row in rows_by_source or []:
        rec = dict(row)
        source = str(rec.get("source") or "unknown")
        count = int(rec.get("count") or 0)
        by_source[source] = count
    
    # Compute by city (using bbox from cities.yml)
    by_city: Dict[str, int] = {}
    try:
        cities_config = load_cities_config()
        cities = cities_config.get("cities", {})
        
        for city_key, city_def in cities.items():
            if not isinstance(city_def, dict):
                continue
            
            districts = city_def.get("districts", {})
            if not districts:
                continue
            
            bbox = _compute_city_bbox(city_key)
            if not bbox:
                continue
            
            lat_min, lat_max, lng_min, lng_max = bbox
            sql_city = (
                """
                SELECT COUNT(*)::int AS count
                FROM locations
                WHERE state = 'CANDIDATE'
                  AND first_seen_at < NOW() - (($1::int || ' days')::interval)
                  AND lat BETWEEN $2 AND $3
                  AND lng BETWEEN $4 AND $5
                """
            )
            rows_city = await fetch(sql_city, int(days), float(lat_min), float(lat_max), float(lng_min), float(lng_max))
            if rows_city:
                count = int(dict(rows_city[0]).get("count") or 0)
                if count > 0:
                    by_city[city_key] = count
    except Exception as e:
        logger.warning("failed_to_compute_stale_by_city", error=str(e), exc_info=e)
    
    return {
        "total_stale": total_stale,
        "by_source": by_source,
        "by_city": by_city,
        "days_threshold": days,
    }


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


async def _news_ingest_daily_series(days: int = 7) -> List[NewsPerDayItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
    sql = """
        SELECT
            date_trunc('day', published_at)::date AS day,
            COUNT(*)::int AS count
        FROM raw_ingested_news
        WHERE published_at >= $1
          AND processing_state = 'classified'
        GROUP BY day
        ORDER BY day ASC
    """
    rows = await fetch(sql, cutoff)
    return [
        NewsPerDayItem(
            date=row["day"],
            count=int(row["count"] or 0),
        )
        for row in rows or []
    ]


async def _news_ingest_by_source(window_hours: int = 24) -> List[NewsLabelCount]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(window_hours))
    sql = """
        SELECT
            COALESCE(NULLIF(source_name, ''), source_key) AS label,
            COUNT(*)::int AS count
        FROM raw_ingested_news
        WHERE published_at >= $1
          AND processing_state = 'classified'
        GROUP BY label
        ORDER BY count DESC, label ASC
    """
    rows = await fetch(sql, cutoff)
    return [
        NewsLabelCount(
            label=str(row["label"] or "unknown"),
            count=int(row["count"] or 0),
        )
        for row in rows or []
    ]


async def _news_error_metrics(window_hours: int = 24) -> NewsErrorMetrics:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(window_hours))
    sql_states = """
        SELECT
            COUNT(*) FILTER (WHERE processing_state = 'error_ai')::int AS error_ai_count,
            COUNT(*) FILTER (WHERE processing_state = 'pending')::int AS pending_count
        FROM raw_ingested_news
        WHERE created_at >= $1
    """
    state_row = await fetchrow(sql_states, cutoff) or {}
    ingest_errors = int(state_row.get("error_ai_count") or 0)
    pending = int(state_row.get("pending_count") or 0)

    sql_logs = """
        SELECT COUNT(*)::int AS count
        FROM ai_logs
        WHERE created_at >= $1
          AND action_type = 'news.classify'
          AND (
                COALESCE(is_success, true) = false
             OR error_message IS NOT NULL
          )
    """
    log_row = await fetchrow(sql_logs, cutoff) or {}
    classify_errors = int(log_row.get("count") or 0)

    return NewsErrorMetrics(
        ingest_errors_last_24h=ingest_errors,
        classify_errors_last_24h=classify_errors,
        pending_items_last_24h=pending,
    )


async def _load_news_feed_thresholds() -> FeedThresholds:
    config = await get_ai_config()
    if not config:
        config = await initialize_ai_config()
    return thresholds_from_config(config)


async def _load_news_source_meta(source_keys: List[str]) -> Dict[str, Dict[str, Any]]:
    if not source_keys:
        return {}
    sql = """
        SELECT
            source_key,
            source_name,
            category,
            language,
            region
        FROM news_source_state
        WHERE source_key = ANY($1::text[])
    """
    rows = await fetch(sql, source_keys)
    return {
        str(row["source_key"]): {
            "source_name": row.get("source_name"),
            "category": row.get("category"),
            "language": row.get("language"),
            "region": row.get("region"),
        }
        for row in rows or []
    }


async def _news_feed_distribution(window_hours: int = 24) -> List[NewsLabelCount]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(window_hours))
    sql = """
        SELECT
            source_key,
            category,
            language,
            location_tag,
            relevance_diaspora,
            relevance_nl,
            relevance_tr,
            relevance_geo
        FROM raw_ingested_news
        WHERE published_at >= $1
          AND processing_state = 'classified'
    """
    rows = await fetch(sql, cutoff)
    if not rows:
        return [
            NewsLabelCount(label=feed.value, count=0)
            for feed in FeedType
        ]

    records = [dict(row) for row in rows]
    source_keys = sorted(
        {rec.get("source_key") for rec in records if rec.get("source_key")}
    )
    source_meta = await _load_news_source_meta(source_keys)
    thresholds = await _load_news_feed_thresholds()

    counts: Dict[FeedType, int] = {feed: 0 for feed in FeedType}
    for rec in records:
        source_key = rec.get("source_key")
        meta = source_meta.get(source_key) or {}
        for feed in FeedType:
            if is_in_feed(feed, rec, meta, thresholds):
                counts[feed] += 1

    result = [
        NewsLabelCount(label=feed.value, count=counts[feed])
        for feed in FeedType
    ]
    result.sort(key=lambda item: item.count, reverse=True)
    return result


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
        # Enhanced Overpass error categorization
        overpass_calls = metrics.get("overpass_calls_last_60m", 0)
        overpass_errors = metrics.get("overpass_error_count_last_60m", 0)
        error_ratio = metrics.get("overpass_error_ratio_last_60m", 0.0)
        timeout_errors = metrics.get("timeout_errors_last_60m", 0)
        rate_limit_errors = metrics.get("rate_limit_errors_last_60m", 0)
        server_5xx_errors = metrics.get("server_5xx_errors_last_60m", 0)
        
        # Only diagnose if we have enough calls (avoid false positives on low activity)
        if overpass_calls >= 10 and overpass_errors > 0:
            # Check which error type dominates (≥50% of errors)
            if timeout_errors > 0 and timeout_errors >= (overpass_errors * 0.5):
                return "OSM_TIMEOUT_STORM"
            elif rate_limit_errors > 0 and rate_limit_errors >= (overpass_errors * 0.5):
                return "OSM_RATE_LIMITED"
            elif server_5xx_errors > 0 and server_5xx_errors >= (overpass_errors * 0.5):
                return "OSM_SERVER_UNSTABLE"
            elif error_ratio >= 0.5:
                # Generic fallback: high error rate but unclear category
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
    # Only consider finished runs for metrics (ignore in-progress runs)
    # This avoids false "no locations discovered" when a run is still in progress
    sql_latest_run = """
        SELECT
            id,
            started_at,
            finished_at,
            counters,
            notes
        FROM discovery_runs
        WHERE finished_at IS NOT NULL
        ORDER BY finished_at DESC
        LIMIT 1
    """
    now = datetime.now(timezone.utc)
    quota_info: Dict[str, Optional[int]] = {}

    try:
        rows = await fetch(sql_latest_run)

        # Enhanced Overpass metrics with error categorization
        sql_overpass = """
            SELECT
                COALESCE(COUNT(*), 0)::int AS overpass_calls_last_60m,
                COALESCE(COUNT(*) FILTER (
                    WHERE status_code = 429
                ), 0)::int AS overpass_429_last_60m,
                COALESCE(COUNT(*) FILTER (
                    WHERE (status_code >= 500 OR status_code IS NULL OR error_message IS NOT NULL)
                ), 0)::int AS overpass_error_count_last_60m,
                COALESCE(COUNT(*) FILTER (
                    WHERE error_message LIKE 'TIMEOUT:%'
                ), 0)::int AS timeout_errors_last_60m,
                COALESCE(COUNT(*) FILTER (
                    WHERE error_message LIKE 'RATE_LIMIT:%'
                ), 0)::int AS rate_limit_errors_last_60m,
                COALESCE(COUNT(*) FILTER (
                    WHERE error_message LIKE 'SERVER_5XX:%'
                ), 0)::int AS server_5xx_errors_last_60m
            FROM overpass_calls
            WHERE ts >= NOW() - (($1::int || ' minutes')::interval)
        """
        overpass_rows = await fetch(sql_overpass, int(WORKER_WINDOW_MINUTES))
        if overpass_rows:
            overpass_data = dict(overpass_rows[0])
            calls_total = int(overpass_data.get("overpass_calls_last_60m") or 0)
            errors_total = int(overpass_data.get("overpass_error_count_last_60m") or 0)
            error_ratio = errors_total / max(calls_total, 1)
            quota_info = {
                "overpass_calls_last_60m": calls_total,
                "overpass_429_last_60m": int(overpass_data.get("overpass_429_last_60m") or 0),
                "overpass_error_count_last_60m": errors_total,
                "overpass_error_ratio_last_60m": error_ratio,
                "timeout_errors_last_60m": int(overpass_data.get("timeout_errors_last_60m") or 0),
                "rate_limit_errors_last_60m": int(overpass_data.get("rate_limit_errors_last_60m") or 0),
                "server_5xx_errors_last_60m": int(overpass_data.get("server_5xx_errors_last_60m") or 0),
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
            # No finished runs found - check if there are any in-progress runs
            sql_in_progress = """
                SELECT COUNT(*)::int AS in_progress_count
                FROM discovery_runs
                WHERE finished_at IS NULL
            """
            in_progress_rows = await fetch(sql_in_progress)
            in_progress_count = int(in_progress_rows[0].get("in_progress_count") or 0) if in_progress_rows else 0
            
            metrics = {
                "overpass_error_count_last_60m": quota_info.get("overpass_error_count_last_60m", 0),
                "overpass_calls_last_60m": quota_info.get("overpass_calls_last_60m", 0),
                "overpass_error_ratio_last_60m": quota_info.get("overpass_error_ratio_last_60m", 0.0),
                "total_inserted_30d": total_inserted_30d,
                "total_runs_30d": total_runs_30d,
            }
            diagnosis_code = _compute_diagnosis_code("discovery_bot", "unknown", None, metrics)
            
            notes_msg = "No finished discovery runs recorded yet."
            if in_progress_count > 0:
                notes_msg += f" ({in_progress_count} run(s) currently in progress - excluded from metrics)"
            
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
                notes=notes_msg,
                diagnosis_code=diagnosis_code,
            )

        record = dict(rows[0])
        started_at = record.get("started_at")
        finished_at = record.get("finished_at")
        counters_raw = record.get("counters") or {}
        counters = counters_raw if isinstance(counters_raw, dict) else {}
        notes_field = record.get("notes") or ""

        # Separate discovered vs inserted counts for better messaging
        discovered = int(counters.get("discovered") or 0)
        inserted = int(counters.get("inserted") or 0)
        processed = discovered  # Use discovered for backward compat with processed_count field
        errors = int(counters.get("failed") or 0)
        is_degraded = bool(counters.get("degraded", False))
        last_run = finished_at  # Only use finished_at (we filtered for finished runs)

        duration_seconds: Optional[float] = None
        if isinstance(started_at, datetime) and isinstance(finished_at, datetime):
            duration_seconds = max((finished_at - started_at).total_seconds(), 0.0)

        status = "ok"
        notes: List[str] = ["Processed count uses discovery_runs.counters.discovered."]
        
        # Add degraded mode indicator if applicable
        if is_degraded:
            notes.insert(0, "Run completed in degraded mode: ")

        if last_run is None:
            status = "unknown"
            notes.append("Run timestamp unavailable.")
        else:
            if (now - last_run) > timedelta(hours=DISCOVERY_STALE_HOURS):
                status = "warning"
                notes.append(f"Last run more than {DISCOVERY_STALE_HOURS}h ago.")
            
            # Better messaging for discovered vs inserted
            if inserted > 0:
                notes.append(f"Last run inserted {inserted} new location(s).")
            elif discovered > 0:
                notes.append("Last run found only duplicates; no new locations inserted.")
            else:
                notes.append("Last finished run discovered no locations in the scanned tiles.")
                if status == "ok":
                    status = "warning"
            
            if errors > 0:
                notes.append(f"{errors} failures recorded in last run.")
                status = "error"

        # Compute diagnosis code with enhanced Overpass error metrics
        metrics = {
            "overpass_error_count_last_60m": quota_info.get("overpass_error_count_last_60m", 0),
            "overpass_calls_last_60m": quota_info.get("overpass_calls_last_60m", 0),
            "overpass_error_ratio_last_60m": quota_info.get("overpass_error_ratio_last_60m", 0.0),
            "timeout_errors_last_60m": quota_info.get("timeout_errors_last_60m", 0),
            "rate_limit_errors_last_60m": quota_info.get("rate_limit_errors_last_60m", 0),
            "server_5xx_errors_last_60m": quota_info.get("server_5xx_errors_last_60m", 0),
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
            worker_type="legacy",
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
            worker_type="legacy",
        )


async def _discovery_train_bot_status() -> WorkerStatus:
    """Get status for Discovery Train bot based on worker_runs and discovery_jobs."""
    now = datetime.now(timezone.utc)
    
    # Query last worker run for discovery_train_bot
    sql_last_run = """
        SELECT
            id,
            started_at,
            finished_at,
            status,
            counters,
            error_message
        FROM worker_runs
        WHERE bot = 'discovery_train_bot'
          AND status IN ('finished', 'failed')
        ORDER BY finished_at DESC NULLS LAST, started_at DESC
        LIMIT 1
    """
    
    # Query pending jobs count
    sql_pending_jobs = """
        SELECT COUNT(*)::int AS pending_count
        FROM discovery_jobs
        WHERE status = 'pending'
    """
    
    # Query recently processed jobs (last 60 minutes)
    sql_recent_processed = """
        SELECT 
            COUNT(*)::int AS processed_count,
            COUNT(*) FILTER (WHERE status = 'failed')::int AS failed_count
        FROM discovery_jobs
        WHERE finished_at >= NOW() - (($1::int || ' minutes')::interval)
          AND status IN ('finished', 'failed')
    """
    
    try:
        last_run_rows = await fetch(sql_last_run)
        pending_rows = await fetch(sql_pending_jobs)
        recent_rows = await fetch(sql_recent_processed, int(WORKER_WINDOW_MINUTES))
        
        last_run = None
        duration_seconds: Optional[float] = None
        processed_recent = 0
        failed_recent = 0
        
        if last_run_rows:
            record = dict(last_run_rows[0])
            started_at = record.get("started_at")
            finished_at = record.get("finished_at")
            last_run = finished_at or started_at
            
            if isinstance(started_at, datetime) and isinstance(finished_at, datetime):
                duration_seconds = max((finished_at - started_at).total_seconds(), 0.0)
        
        pending_count = 0
        if pending_rows:
            pending_count = int(pending_rows[0].get("pending_count") or 0)
        
        if recent_rows:
            recent_data = dict(recent_rows[0])
            processed_recent = int(recent_data.get("processed_count") or 0)
            failed_recent = int(recent_data.get("failed_count") or 0)
        
        # Determine status
        status = "ok"
        notes: List[str] = ["Discovery Train processes jobs from discovery_jobs queue sequentially."]
        
        if last_run is None:
            status = "unknown"
            notes.append("No Discovery Train runs recorded yet.")
        else:
            if (now - last_run) > timedelta(hours=DISCOVERY_STALE_HOURS):
                status = "warning"
                notes.append(f"Last run more than {DISCOVERY_STALE_HOURS}h ago.")
            
            if pending_count > 1000:
                status = "error"
                notes.append(f"Very high pending jobs queue ({pending_count}).")
            elif pending_count > 100:
                if status == "ok":
                    status = "warning"
                notes.append(f"High pending jobs queue ({pending_count}).")
            
            if processed_recent == 0 and pending_count > 0:
                notes.append("No jobs processed recently but queue has pending jobs.")
                if status == "ok":
                    status = "warning"
            
            if failed_recent > 0:
                notes.append(f"{failed_recent} job(s) failed in the last 60 minutes.")
                if failed_recent >= 3:
                    status = "error"
                elif status == "ok":
                    status = "warning"
        
        # Build quota_info with pending jobs
        quota_info: Dict[str, Optional[int]] = {
            "pending_jobs": pending_count,
        }
        
        # Compute diagnosis code
        metrics = {
            "pending_jobs": pending_count,
            "processed_count": processed_recent,
            "error_count": failed_recent,
        }
        diagnosis_code = _compute_diagnosis_code("discovery_train_bot", status, last_run, metrics)
        
        return WorkerStatus(
            id="discovery_train_bot",
            label="Discovery Train",
            last_run=last_run,
            duration_seconds=duration_seconds,
            processed_count=processed_recent,
            error_count=failed_recent,
            status=status,  # type: ignore[arg-type]
            window_label=f"last {WORKER_WINDOW_MINUTES} min",
            quota_info=quota_info,
            notes=_build_notes(notes),
            diagnosis_code=diagnosis_code,
            worker_type="queue_based",
        )
    except asyncpg.exceptions.UndefinedTableError as exc:
        logger.warning(
            "worker_status_table_missing",
            worker_id="discovery_train_bot",
            error=str(exc),
        )
        metrics = {"notes": "METRICS_DATA_MISSING"}
        diagnosis_code = _compute_diagnosis_code("discovery_train_bot", "unknown", None, metrics)
        return WorkerStatus(
            id="discovery_train_bot",
            label="Discovery Train",
            last_run=None,
            duration_seconds=None,
            processed_count=None,
            error_count=None,
            status="unknown",
            window_label=None,
            quota_info=None,
            notes="worker_runs or discovery_jobs table is missing; run migrations to enable Discovery Train metrics.",
            diagnosis_code=diagnosis_code,
            worker_type="queue_based",
        )
    except Exception as exc:
        logger.exception("discovery_train_bot_status_failed", error=str(exc))
        metrics = {}
        diagnosis_code = _compute_diagnosis_code("discovery_train_bot", "error", None, metrics)
        return WorkerStatus(
            id="discovery_train_bot",
            label="Discovery Train",
            last_run=None,
            duration_seconds=None,
            processed_count=None,
            error_count=None,
            status="error",
            window_label=None,
            quota_info=None,
            notes=f"Failed to compute status: {str(exc)}",
            diagnosis_code=diagnosis_code,
            worker_type="queue_based",
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
    await safe_call("discovery_train_bot", "Discovery Train", _discovery_train_bot_status)
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

    # City progress - load all cities from cities.yml
    city_progress_dict: Dict[str, CityProgressData] = {}
    try:
        cities_config = load_cities_config()
        cities = cities_config.get("cities", {})
        
        for city_key, city_def in cities.items():
            if not isinstance(city_def, dict):
                continue
            
            # Only compute progress for cities with districts (bbox can be computed)
            districts = city_def.get("districts", {})
            if not districts:
                # Skip cities without districts (can't compute bbox)
                continue
            
            progress = await _city_progress(city_key)
            if progress:
                city_progress_dict[city_key] = progress
    except Exception as e:
        logger.warning("failed_to_load_cities_for_metrics", error=str(e), exc_info=e)
        # Fallback: at least include Rotterdam
        rot = await _rotterdam_progress()
        if rot:
            city_progress_dict["rotterdam"] = CityProgressData(
                verified_count=rot.verified_count,
                candidate_count=rot.candidate_count,
                coverage_ratio=rot.coverage_ratio,
                growth_weekly=rot.growth_weekly,
            )

    news_trending_metrics = await _news_trending_metrics()

    workers = await _worker_statuses(err_rate, g429)
    current_runs = await _active_worker_runs()
    
    # Stale candidates metrics
    stale_metrics = await _stale_candidates_metrics(days=7)
    stale_candidates = StaleCandidates(
        total_stale=stale_metrics["total_stale"],
        by_source=stale_metrics["by_source"],
        by_city=stale_metrics["by_city"],
        days_threshold=stale_metrics["days_threshold"],
    )

    return MetricsSnapshot(
        city_progress=CityProgress(cities=city_progress_dict),
        quality=Quality(
            conversion_rate_verified_14d=conv_14d,
            task_error_rate_60m=err_rate,
            google429_last60m=g429,
        ),
        discovery=Discovery(new_candidates_per_week=latest_count),
        news_trending=news_trending_metrics,
        latency=Latency(p50_ms=p50, avg_ms=avg, max_ms=mx),
        weekly_candidates=weekly,
        workers=workers,
        current_runs=current_runs,
        stale_candidates=stale_candidates,
    )


async def _event_daily_series(days: int = 7) -> List[EventPerDayItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
    sql = """
        SELECT
            date_trunc('day', COALESCE(start_at, fetched_at))::date AS day,
            COUNT(*)::int AS count
        FROM event_raw
        WHERE fetched_at >= $1
        GROUP BY day
        ORDER BY day ASC
    """
    rows = await fetch(sql, cutoff)
    return [
        EventPerDayItem(
            date=row["day"],
            count=int(row["count"] or 0),
        )
        for row in rows or []
    ]


async def _event_source_stats(window_hours: int = 24) -> List[EventSourceStat]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(window_hours))
    sql = """
        WITH recent AS (
            SELECT event_source_id, COUNT(*)::int AS count_last
            FROM event_raw
            WHERE fetched_at >= $1
            GROUP BY event_source_id
        ),
        total AS (
            SELECT event_source_id, COUNT(*)::int AS total_count
            FROM event_raw
            GROUP BY event_source_id
        )
        SELECT
            es.id,
            es.key,
            es.name,
            es.last_success_at,
            es.last_error_at,
            es.last_error,
            COALESCE(recent.count_last, 0) AS events_last_24h,
            COALESCE(total.total_count, 0) AS total_events
        FROM event_sources es
        LEFT JOIN recent ON recent.event_source_id = es.id
        LEFT JOIN total ON total.event_source_id = es.id
        ORDER BY events_last_24h DESC, es.name ASC
    """
    rows = await fetch(sql, cutoff)
    return [
        EventSourceStat(
            source_id=int(row["id"]),
            source_key=str(row["key"]),
            source_name=str(row["name"]),
            last_success_at=row.get("last_success_at"),
            last_error_at=row.get("last_error_at"),
            last_error=row.get("last_error"),
            events_last_24h=int(row.get("events_last_24h") or 0),
            total_events=int(row.get("total_events") or 0),
        )
        for row in rows or []
    ]


async def _total_events_last_30d(days: int = 30) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
    sql = """
        SELECT COUNT(*)::int AS count
        FROM event_raw
        WHERE fetched_at >= $1
    """
    rows = await fetch(sql, cutoff)
    return int(rows[0]["count"]) if rows else 0


async def _event_enrichment_metrics() -> EventEnrichmentMetrics:
    totals_sql = """
        SELECT
            COUNT(*)::int AS total,
            COUNT(*) FILTER (WHERE processing_state = 'enriched')::int AS enriched,
            COUNT(*) FILTER (WHERE processing_state = 'pending')::int AS pending,
            COUNT(*) FILTER (WHERE processing_state = 'error')::int AS errors,
            AVG(confidence_score) FILTER (
                WHERE processing_state = 'enriched' AND confidence_score IS NOT NULL
            ) AS avg_confidence
        FROM event_raw
    """
    rows = await fetch(totals_sql)
    totals = rows[0] if rows else {}

    breakdown_sql = """
        SELECT
            COALESCE(NULLIF(category_key, ''), 'other') AS category_key,
            COUNT(*)::int AS count
        FROM event_raw
        WHERE processing_state = 'enriched'
        GROUP BY category_key
        ORDER BY count DESC
        LIMIT 10
    """
    category_rows = await fetch(breakdown_sql)
    breakdown = [
        EventCategoryBreakdown(
            category_key=str(row["category_key"] or "other"),
            count=int(row["count"] or 0),
        )
        for row in category_rows or []
    ]

    return EventEnrichmentMetrics(
        total=int(totals.get("total") or 0),
        enriched=int(totals.get("enriched") or 0),
        pending=int(totals.get("pending") or 0),
        errors=int(totals.get("errors") or 0),
        avg_confidence_score=totals.get("avg_confidence"),
        category_breakdown=breakdown,
    )


async def _event_dedupe_metrics(days: int = 7) -> EventDedupeMetrics:
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
    row = await fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE duplicate_of_id IS NULL) AS canonical_count,
            COUNT(*) FILTER (WHERE duplicate_of_id IS NOT NULL) AS duplicate_count,
            COUNT(*) FILTER (
                WHERE duplicate_of_id IS NOT NULL AND updated_at >= $1
            ) AS duplicates_recent
        FROM events_candidate
        WHERE state = ANY($2::text[])
        """,
        cutoff,
        list(EVENT_CANDIDATE_ACTIVE_STATES),
    )
    canonical = int(row["canonical_count"]) if row else 0
    duplicates = int(row["duplicate_count"]) if row else 0
    duplicates_recent = int(row["duplicates_recent"]) if row else 0
    total = canonical + duplicates
    ratio = canonical / total if total else None
    return EventDedupeMetrics(
        canonical_events=canonical,
        duplicate_events=duplicates,
        duplicates_last_7d=duplicates_recent,
        canonical_ratio=ratio,
    )


async def generate_event_metrics_snapshot(
    days: int = 7,
    window_hours: int = 24,
) -> EventMetricsSnapshot:
    daily_series = await _event_daily_series(days=days)
    source_stats = await _event_source_stats(window_hours=window_hours)
    total_events_last_30d = await _total_events_last_30d()
    enrichment_metrics = await _event_enrichment_metrics()
    dedupe_metrics = await _event_dedupe_metrics(days=days)

    return EventMetricsSnapshot(
        events_per_day_last_7d=daily_series,
        sources=source_stats,
        total_events_last_30d=total_events_last_30d,
        enrichment=enrichment_metrics,
        dedupe=dedupe_metrics,
    )


async def generate_news_metrics_snapshot(
    days: int = 7,
    window_hours: int = 24,
) -> NewsMetricsSnapshot:
    """
    Build a news-specific metrics snapshot without altering the main MetricsSnapshot payload.
    """
    daily_series = await _news_ingest_daily_series(days=days)
    by_source = await _news_ingest_by_source(window_hours=window_hours)
    by_feed = await _news_feed_distribution(window_hours=window_hours)
    errors = await _news_error_metrics(window_hours=window_hours)

    return NewsMetricsSnapshot(
        items_per_day_last_7d=daily_series,
        items_by_source_last_24h=by_source,
        items_by_feed_last_24h=by_feed,
        errors=errors,
    )


def _compute_category_health_status(cat: CategoryHealth) -> str:
    """
    Compute category health status based on Turkish-first strategy metrics.
    
    Returns: "healthy", "warning", "degraded", "critical", or "no_data"
    """
    # no_data: no Overpass data in window
    if cat.overpass_found == 0:
        return "no_data"
    
    # critical: very low Turkish coverage AND no inserts AND (no classifications OR all ignored)
    if (cat.turkish_coverage_ratio_pct < CATEGORY_HEALTH_CRITICAL_COVERAGE_THRESHOLD and
        cat.inserted_locations_last_7d == 0 and
        (cat.ai_classifications_last_7d == 0 or cat.ai_action_keep == 0)):
        return "critical"
    
    # degraded: low Turkish coverage OR no inserts OR very low AI precision
    if (cat.turkish_coverage_ratio_pct < CATEGORY_HEALTH_DEGRADED_COVERAGE_THRESHOLD or
        cat.inserted_locations_last_7d == 0 or
        cat.ai_precision_pct < CATEGORY_HEALTH_DEGRADED_PRECISION_THRESHOLD):
        return "degraded"
    
    # warning: moderate Turkish coverage OR moderate AI precision (but not degraded)
    if (cat.turkish_coverage_ratio_pct < CATEGORY_HEALTH_WARNING_COVERAGE_THRESHOLD or
        cat.ai_precision_pct < CATEGORY_HEALTH_WARNING_PRECISION_THRESHOLD):
        return "warning"
    
    # healthy: good Turkish coverage and good AI precision
    if (cat.turkish_coverage_ratio_pct >= CATEGORY_HEALTH_WARNING_COVERAGE_THRESHOLD and
        cat.ai_precision_pct >= CATEGORY_HEALTH_WARNING_PRECISION_THRESHOLD and
        cat.inserted_locations_last_7d > 0):
        return "healthy"
    
    # Default fallback
    return "warning"


async def category_health_metrics() -> CategoryHealthResponse:
    """
    Returns category-level health metrics over recent time windows:
    - Overpass calls & zero-result ratio per category (last 7 days)
    - Insert counts in last 7 days per category
    - Classification stats per category (keep/ignore)
    - Promotions to VERIFIED per category (last 7d)
    
    Returns CategoryHealthResponse with all discovery-enabled categories included.
    """
    # Get all discovery-enabled categories
    discoverable_cats = get_discoverable_categories()
    category_keys = [cat.key for cat in discoverable_cats]
    
    if not category_keys:
        return CategoryHealthResponse(
            categories={},
            time_windows={
                "overpass_window_hours": 72,
                "inserts_window_days": 7,
                "classifications_window_days": 7,
                "promotions_window_days": 7,
            }
        )
    
    # Initialize result dict with all categories (ensures all appear even with 0 counts)
    result: Dict[str, CategoryHealth] = {}
    for cat_key in category_keys:
        result[cat_key] = CategoryHealth(
            overpass_calls=0,
            overpass_successful_calls=0,
            overpass_zero_results=0,
            overpass_zero_result_ratio_pct=0.0,
            inserted_locations_last_7d=0,
            state_counts={
                "CANDIDATE": 0,
                "PENDING_VERIFICATION": 0,
                "VERIFIED": 0,
                "SUSPENDED": 0,
                "RETIRED": 0,
            },
            avg_confidence_last_7d=None,
            ai_classifications_last_7d=0,
            ai_action_keep=0,
            ai_action_ignore=0,
            ai_avg_confidence=None,
            promoted_verified_last_7d=0,
            overpass_found=0,
            turkish_coverage_ratio_pct=0.0,
            ai_precision_pct=0.0,
            status="no_data",
        )
    
    # Query 1: Overpass calls (last 7 days)
    # Use LATERAL join to expand category_set, then filter by category_keys
    # This avoids "set-returning functions are not allowed in WHERE" error
    try:
        sql_overpass = """
            SELECT 
                cat AS category,
                COUNT(*)::int AS total_calls,
                COUNT(*) FILTER (WHERE oc.status_code = 200)::int AS successful_calls,
                COUNT(*) FILTER (WHERE oc.found = 0 AND oc.status_code = 200)::int AS zero_results,
                SUM(oc.found)::int AS total_found
            FROM overpass_calls oc
            CROSS JOIN LATERAL unnest(oc.category_set) AS cat
            WHERE oc.ts >= now() - interval '7 days'
                AND cat = ANY($1::text[])
            GROUP BY cat
        """
        overpass_rows = await fetch(sql_overpass, category_keys)
    except Exception as e:
        logger.warning("category_health_overpass_query_failed", error=str(e), error_type=type(e).__name__)
        overpass_rows = []
    
    for row in overpass_rows or []:
        row_dict = dict(row)
        cat_key = str(row_dict.get("category", ""))
        if cat_key not in result:
            continue
        
        total_calls = int(row_dict.get("total_calls", 0))
        successful_calls = int(row_dict.get("successful_calls", 0))
        zero_results = int(row_dict.get("zero_results", 0))
        total_found = int(row_dict.get("total_found", 0))
        
        result[cat_key].overpass_calls = total_calls
        result[cat_key].overpass_successful_calls = successful_calls
        result[cat_key].overpass_zero_results = zero_results
        result[cat_key].overpass_found = total_found
        
        if successful_calls > 0:
            zero_ratio = (zero_results / successful_calls) * 100.0
            result[cat_key].overpass_zero_result_ratio_pct = round(zero_ratio, 2)
    
    # Query 2: Locations inserted (last 7 days)
    try:
        sql_locations = """
            SELECT 
                category,
                COUNT(*)::int AS total_inserted,
                COUNT(*) FILTER (WHERE state = 'CANDIDATE')::int AS candidate,
                COUNT(*) FILTER (WHERE state = 'PENDING_VERIFICATION')::int AS pending,
                COUNT(*) FILTER (WHERE state = 'VERIFIED')::int AS verified,
                COUNT(*) FILTER (WHERE state = 'SUSPENDED')::int AS suspended,
                COUNT(*) FILTER (WHERE state = 'RETIRED')::int AS retired,
                ROUND(AVG(confidence_score), 3) AS avg_confidence
            FROM locations
            WHERE category = ANY($1::text[])
                AND first_seen_at >= now() - interval '7 days'
            GROUP BY category
        """
        location_rows = await fetch(sql_locations, category_keys)
    except Exception as e:
        logger.warning("category_health_locations_query_failed", error=str(e), error_type=type(e).__name__)
        location_rows = []
    
    for row in location_rows or []:
        row_dict = dict(row)
        cat_key = str(row_dict.get("category", ""))
        if cat_key not in result:
            continue
        
        result[cat_key].inserted_locations_last_7d = int(row_dict.get("total_inserted", 0))
        result[cat_key].state_counts["CANDIDATE"] = int(row_dict.get("candidate", 0))
        result[cat_key].state_counts["PENDING_VERIFICATION"] = int(row_dict.get("pending", 0))
        result[cat_key].state_counts["VERIFIED"] = int(row_dict.get("verified", 0))
        result[cat_key].state_counts["SUSPENDED"] = int(row_dict.get("suspended", 0))
        result[cat_key].state_counts["RETIRED"] = int(row_dict.get("retired", 0))
        
        avg_conf = row_dict.get("avg_confidence")
        if avg_conf is not None:
            result[cat_key].avg_confidence_last_7d = float(avg_conf)
    
    # Query 3: Promotions to VERIFIED (last 7 days)
    # Count locations that became VERIFIED in the last 7 days
    try:
        sql_promotions = """
            SELECT 
                category,
                COUNT(*)::int AS promoted_count
            FROM locations
            WHERE category = ANY($1::text[])
                AND state = 'VERIFIED'
                AND last_verified_at >= now() - interval '7 days'
            GROUP BY category
        """
        promotion_rows = await fetch(sql_promotions, category_keys)
    except Exception as e:
        logger.warning("category_health_promotions_query_failed", error=str(e), error_type=type(e).__name__)
        promotion_rows = []
    
    for row in promotion_rows or []:
        row_dict = dict(row)
        cat_key = str(row_dict.get("category", ""))
        if cat_key not in result:
            continue
        
        result[cat_key].promoted_verified_last_7d = int(row_dict.get("promoted_count", 0))
    
    # Query 4: AI classifications (last 7 days)
    try:
        sql_ai = """
            SELECT 
                l.category,
                COUNT(*)::int AS classification_count,
                COUNT(*) FILTER (WHERE al.validated_output->>'action' = 'keep')::int AS action_keep,
                COUNT(*) FILTER (WHERE al.validated_output->>'action' = 'ignore')::int AS action_ignore,
                ROUND(AVG((al.validated_output->>'confidence_score')::numeric), 3) AS avg_confidence
            FROM ai_logs al
            JOIN locations l ON al.location_id = l.id
            WHERE l.category = ANY($1::text[])
                AND al.created_at >= now() - interval '7 days'
                AND al.action_type IN ('classification', 'verify_locations.classified', 'verification_consumer.classified')
            GROUP BY l.category
        """
        ai_rows = await fetch(sql_ai, category_keys)
    except Exception as e:
        logger.warning("category_health_ai_query_failed", error=str(e), error_type=type(e).__name__)
        ai_rows = []
    
    for row in ai_rows or []:
        row_dict = dict(row)
        cat_key = str(row_dict.get("category", ""))
        if cat_key not in result:
            continue
        
        result[cat_key].ai_classifications_last_7d = int(row_dict.get("classification_count", 0))
        result[cat_key].ai_action_keep = int(row_dict.get("action_keep", 0))
        result[cat_key].ai_action_ignore = int(row_dict.get("action_ignore", 0))
        
        avg_conf = row_dict.get("avg_confidence")
        if avg_conf is not None:
            result[cat_key].ai_avg_confidence = float(avg_conf)
    
    # Compute new metrics: Turkish coverage ratio and AI precision
    for cat_key, cat in result.items():
        # Turkish coverage ratio: (inserted / overpass_found) * 100
        # Capped at 100% to handle edge cases where window alignment artifacts
        # might cause ratio to exceed 100% (e.g., if inserts window includes
        # locations from before Overpass window start)
        if cat.overpass_found > 0:
            ratio = (cat.inserted_locations_last_7d / cat.overpass_found) * 100.0
            cat.turkish_coverage_ratio_pct = round(min(ratio, 100.0), 2)
        else:
            cat.turkish_coverage_ratio_pct = 0.0
        
        # AI precision: (keep / total_classifications) * 100
        if cat.ai_classifications_last_7d > 0:
            cat.ai_precision_pct = round((cat.ai_action_keep / cat.ai_classifications_last_7d) * 100.0, 2)
        else:
            cat.ai_precision_pct = 0.0
        
        # Compute status
        cat.status = _compute_category_health_status(cat)
        
        # Debug logging per category
        logger.debug(
            "category_health_metrics_computed",
            category_key=cat_key,
            overpass_found=cat.overpass_found,
            inserted_locations_last_7d=cat.inserted_locations_last_7d,
            turkish_coverage_ratio_pct=cat.turkish_coverage_ratio_pct,
            ai_classifications_last_7d=cat.ai_classifications_last_7d,
            ai_action_keep=cat.ai_action_keep,
            ai_action_ignore=cat.ai_action_ignore,
            ai_precision_pct=cat.ai_precision_pct,
            status=cat.status,
        )
    
    return CategoryHealthResponse(
        categories=result,
        time_windows={
            "overpass_window_hours": 168,
            "inserts_window_days": 7,
            "classifications_window_days": 7,
            "promotions_window_days": 7,
        }
    )


async def location_state_metrics() -> LocationStateMetrics:
    """
    Compute location state breakdown metrics.
    
    Returns counts for each state: CANDIDATE, PENDING_VERIFICATION, VERIFIED, RETIRED, SUSPENDED.
    """
    sql = """
        SELECT 
            state::text,
            COUNT(*)::int AS count
        FROM locations
        GROUP BY state
        ORDER BY state
    """
    
    rows = await fetch(sql)
    
    by_state: List[LocationStateBucket] = []
    total = 0
    
    for row in rows or []:
        rec = dict(row)
        state = str(rec.get("state", ""))
        count = int(rec.get("count", 0))
        by_state.append(LocationStateBucket(state=state, count=count))
        total += count
    
    logger.info(
        "location_state_metrics_computed",
        total=total,
        states_count=len(by_state),
    )
    
    return LocationStateMetrics(
        total=total,
        by_state=by_state,
    )


