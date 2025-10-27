from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
import os
from typing import Any, Dict, List, Optional, Tuple

import yaml

from services.db_service import fetch
from app.models.metrics import (
    CityProgress,
    CityProgressRotterdam,
    Discovery,
    Latency,
    MetricsSnapshot,
    Quality,
    WeeklyCandidatesItem,
)


def _load_rotterdam_bbox():
    """
    Returns (lat_min, lat_max, lng_min, lng_max) for Rotterdam.

    In production we read Infra/config/cities.yml.
    In local development, that file may not exist,
    which currently crashes /admin/metrics/snapshot with FileNotFoundError.

    This fallback ensures the endpoint still works locally
    by returning a hardcoded Rotterdam bounding box if the file is missing.
    """
    path = "Infra/config/cities.yml"

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        rot = cfg["rotterdam"]["bbox"]
        return (
            rot["lat_min"], rot["lat_max"],
            rot["lng_min"], rot["lng_max"],
        )

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


async def _rotterdam_progress() -> CityProgressRotterdam:
    lat_min, lat_max, lng_min, lng_max = _load_rotterdam_bbox()
    sql_counts = (
        """
        SELECT
          SUM(CASE WHEN state = 'VERIFIED' THEN 1 ELSE 0 END)::int AS verified_count,
          SUM(CASE WHEN state = 'CANDIDATE' THEN 1 ELSE 0 END)::int AS candidate_count
        FROM locations
        WHERE lat BETWEEN $1 AND $2 AND lng BETWEEN $3 AND $4
        """
    )
    rows = await fetch(sql_counts, float(lat_min), float(lat_max), float(lng_min), float(lng_max))
    verified = int(dict(rows[0]).get("verified_count", 0)) if rows else 0
    candidates = int(dict(rows[0]).get("candidate_count", 0)) if rows else 0
    denom = verified + candidates
    coverage = (float(verified) / float(denom)) if denom > 0 else 0.0

    # Weekly growth: compare VERIFIED in current week vs prior week based on last_verified_at
    sql_weekly = (
        """
        WITH r AS (
          SELECT * FROM locations
          WHERE lat BETWEEN $1 AND $2 AND lng BETWEEN $3 AND $4
        )
        SELECT
          SUM(CASE WHEN last_verified_at >= date_trunc('week', NOW()) THEN 1 ELSE 0 END)::int AS cur,
          SUM(CASE WHEN last_verified_at < date_trunc('week', NOW())
                    AND last_verified_at >= date_trunc('week', NOW()) - INTERVAL '7 days'
                   THEN 1 ELSE 0 END)::int AS prev
        FROM r
        WHERE state = 'VERIFIED'
        """
    )
    rows2 = await fetch(sql_weekly, float(lat_min), float(lat_max), float(lng_min), float(lng_max))
    cur = int(dict(rows2[0]).get("cur", 0)) if rows2 else 0
    prev = int(dict(rows2[0]).get("prev", 0)) if rows2 else 0
    growth = 0.0
    if prev > 0:
        growth = (float(cur - prev) / float(prev)) * 100.0
    elif cur > 0:
        growth = 100.0

    return CityProgressRotterdam(
        verified_count=verified,
        candidate_count=candidates,
        coverage_ratio=coverage,
        growth_weekly=growth,
    )


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
    )


