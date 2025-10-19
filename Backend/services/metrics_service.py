from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
import structlog

# Logger (JSON via structlog)
logger = structlog.get_logger()

# Optional: PyYAML voor city-grid (bbox) laden
try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # we fallbacken op env-variabelen als YAML niet beschikbaar is


# =========================================================
# Engine management (compatibel met jouw project)
# =========================================================

_ENGINE: Optional[AsyncEngine] = None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_to_asyncpg(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_engine() -> AsyncEngine:
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    # Probeer gedeelde engine (indien jouw project die expose't)
    try:
        from app.services.db_service import async_engine as shared_engine  # type: ignore
        _ENGINE = shared_engine
        return _ENGINE
    except Exception:
        pass
    try:
        from app.db import async_engine as shared_engine  # type: ignore
        _ENGINE = shared_engine
        return _ENGINE
    except Exception:
        pass

    # Fallback: zelf engine opbouwen
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL is niet gezet. Zet bijv.: "
            "export DATABASE_URL='postgresql+asyncpg://user:pass@host:5432/dbname'"
        )
    db_url = _coerce_to_asyncpg(db_url)
    _ENGINE = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    return _ENGINE


# =========================================================
# Pydantic v2 datamodellen (bestaand + extensie via KPIItem)
# =========================================================

class TimeWindow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    minutes: Optional[int] = None
    hours: Optional[int] = None
    days: Optional[int] = None

    def to_timedelta(self) -> timedelta:
        total = 0
        if self.minutes:
            total += self.minutes
        if self.hours:
            total += self.hours * 60
        if self.days:
            total += self.days * 1440
        return timedelta(minutes=total)


class KPIItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    value: Any
    unit: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class MetricsSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    generated_at: datetime
    window_desc: str
    kpis: List[KPIItem]


# =========================================================
# KPI helpers (bestaand)
# =========================================================

async def kpi_new_candidates_per_week(engine: AsyncEngine, weeks: int = 8) -> KPIItem:
    sql = text("""
        WITH weekly AS (
          SELECT date_trunc('week', first_seen_at) AS week_start, COUNT(*) AS cnt
          FROM locations
          WHERE state = 'CANDIDATE'
            AND first_seen_at >= :since_ts
          GROUP BY 1
        )
        SELECT to_char(week_start, 'IYYY-IW') AS iso_week, cnt
        FROM weekly
        ORDER BY week_start ASC
    """)
    since_ts = _now_utc() - timedelta(weeks=weeks)
    out: List[Dict[str, Any]] = []
    async with engine.begin() as conn:
        rows = (await conn.execute(sql, {"since_ts": since_ts})).mappings().all()
        for r in rows:
            out.append({"week": r["iso_week"], "count": int(r["cnt"])})
    return KPIItem(name="new_candidates_per_week", value=out, unit="locations")


async def kpi_conversion_rate_verified(engine: AsyncEngine, days: int = 14) -> KPIItem:
    sql_total = text("""
        SELECT COUNT(*) AS total
        FROM locations
        WHERE first_seen_at >= :since_ts
    """)
    sql_verified = text("""
        SELECT COUNT(*) AS verified
        FROM locations
        WHERE first_seen_at >= :since_ts
          AND state = 'VERIFIED'
    """)
    since_ts = _now_utc() - timedelta(days=days)
    async with engine.begin() as conn:
        total = int((await conn.execute(sql_total, {"since_ts": since_ts})).scalar() or 0)
        verified = int((await conn.execute(sql_verified, {"since_ts": since_ts})).scalar() or 0)
    rate = (verified / total) if total > 0 else 0.0
    return KPIItem(
        name="conversion_rate_to_VERIFIED",
        value=round(rate, 4),
        unit="ratio",
        meta={"window_days": days, "verified": verified, "total": total},
    )


async def kpi_task_error_rate(engine: AsyncEngine, window: TimeWindow = TimeWindow(hours=1)) -> KPIItem:
    """
    Task-foutpercentage over de laatste window.
    1) Probeer uit tasks (status/is_success).
    2) Fallback naar ai_logs bij ontbreken.
    """
    since_ts = _now_utc() - window.to_timedelta()

    # ---- Eerst tasks
    try:
        sql_tasks_total = text("""
            SELECT COUNT(*) AS total
            FROM tasks
            WHERE created_at >= :since_ts
        """)
        sql_tasks_failed = text("""
            SELECT COUNT(*) AS failed
            FROM tasks
            WHERE created_at >= :since_ts
              AND (status = 'FAILED' OR is_success = false)
        """)
        async with engine.begin() as conn:
            total = (await conn.execute(sql_tasks_total, {"since_ts": since_ts})).scalar()
            failed = (await conn.execute(sql_tasks_failed, {"since_ts": since_ts})).scalar()
        total = int(total or 0)
        failed = int(failed or 0)
        rate = (failed / total) if total > 0 else 0.0
        return KPIItem(
            name="task_error_rate",
            value=round(rate, 4),
            unit="ratio",
            meta={
                "window_minutes": int(window.to_timedelta().total_seconds() // 60),
                "failed": failed,
                "total": total,
                "source": "tasks",
            },
        )
    except Exception:
        pass  # fallback hieronder

    # ---- Fallback ai_logs
    sql_logs_total = text("""
        SELECT COUNT(*) AS total
        FROM ai_logs
        WHERE created_at >= :since_ts
          AND (
            action_type ILIKE 'worker.%'
            OR action_type ILIKE 'bot.%'
            OR action_type ILIKE 'task.%'
          )
    """)
    sql_logs_failed = text("""
        SELECT COUNT(*) AS failed
        FROM ai_logs
        WHERE created_at >= :since_ts
          AND (
            action_type ILIKE 'worker.%'
            OR action_type ILIKE 'bot.%'
            OR action_type ILIKE 'task.%'
          )
          AND is_success = false
    """)
    async with engine.begin() as conn:
        total = (await conn.execute(sql_logs_total, {"since_ts": since_ts})).scalar()
        failed = (await conn.execute(sql_logs_failed, {"since_ts": since_ts})).scalar()

    total = int(total or 0)
    failed = int(failed or 0)
    rate = (failed / total) if total > 0 else 0.0
    return KPIItem(
        name="task_error_rate",
        value=round(rate, 4),
        unit="ratio",
        meta={
            "window_minutes": int(window.to_timedelta().total_seconds() // 60),
            "failed": failed,
            "total": total,
            "source": "ai_logs_fallback",
        },
    )


async def kpi_api_latency(engine: AsyncEngine, window: TimeWindow = TimeWindow(hours=1)) -> KPIItem:
    since_ts = _now_utc() - window.to_timedelta()
    sql = text("""
        WITH d AS (
          SELECT
            (CASE
              WHEN validated_output ? 'duration_ms' THEN (validated_output->>'duration_ms')::numeric
              WHEN raw_response ? 'duration_ms' THEN (raw_response->>'duration_ms')::numeric
              WHEN (raw_response ? 'meta') AND ((raw_response->'meta') ? 'duration_ms')
                THEN ((raw_response->'meta')->>'duration_ms')::numeric
              ELSE NULL
            END) AS dur
          FROM ai_logs
          WHERE created_at >= :since_ts
        )
        SELECT
          COUNT(*) FILTER (WHERE dur IS NOT NULL)    AS n,
          PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dur)
            FILTER (WHERE dur IS NOT NULL) AS p50,
          AVG(dur)  FILTER (WHERE dur IS NOT NULL)   AS avg,
          MAX(dur)  FILTER (WHERE dur IS NOT NULL)   AS p100
        FROM d;
    """)
    async with engine.begin() as conn:
        row = (await conn.execute(sql, {"since_ts": since_ts})).mappings().one()
    n = int(row["n"] or 0)
    p50 = float(row["p50"] or 0)
    avg = float(row["avg"] or 0)
    p100 = float(row["p100"] or 0)
    return KPIItem(
        name="api_latency_ms",
        value={"p50": p50, "avg": avg, "max": p100},
        unit="milliseconds",
        meta={"window_minutes": int(window.to_timedelta().total_seconds() // 60), "n": n},
    )


async def kpi_google_429_count(engine: AsyncEngine, window: TimeWindow = TimeWindow(hours=1)) -> KPIItem:
    since_ts = _now_utc() - window.to_timedelta()
    sql = text("""
        SELECT COUNT(*) AS cnt
        FROM ai_logs
        WHERE created_at >= :since_ts
          AND (
            error_message ILIKE '%429%' OR
            (raw_response ? 'statusCode' AND (raw_response->>'statusCode')::int = 429) OR
            (raw_response ? 'error' AND (raw_response->'error'->>'code') = 'RESOURCE_EXHAUSTED')
          )
    """)
    async with engine.begin() as conn:
        cnt = int((await conn.execute(sql, {"since_ts": since_ts})).scalar() or 0)
    return KPIItem(
        name="google_api_429_count",
        value=cnt,
        unit="events",
        meta={"window_minutes": int(window.to_timedelta().total_seconds() // 60)},
    )


# =========================================================
# 🔹 City KPI (Rotterdam only) — bbox uit cities.yml
# =========================================================

def _load_rotterdam_bbox() -> Tuple[float, float, float, float]:
    """
    Laad de Rotterdam-bbox uit cities.yml (union van alle districten).
    Zoekpad:
      1) ENV CITIES_YML
      2) ./Infra/config/cities.yml
      3) Infra/config/cities.yml
      4) ./cities.yml
      5) /mnt/data/cities.yml
    Als PyYAML ontbreekt, gebruik ENV fallback:
      ROTTERDAM_LAT_MIN, ROTTERDAM_LAT_MAX, ROTTERDAM_LNG_MIN, ROTTERDAM_LNG_MAX
    """
    if yaml is not None:
        paths = [
            os.getenv("CITIES_YML"),
            os.path.join(".", "Infra", "config", "cities.yml"),
            os.path.join("Infra", "config", "cities.yml"),
            os.path.join(".", "cities.yml"),
            "/mnt/data/cities.yml",
        ]
        for p in [pp for pp in paths if pp]:
            try:
                if os.path.exists(p):
                    with open(p, "r") as f:
                        data = yaml.safe_load(f)
                    city = data["cities"]["rotterdam"]
                    lat_min = 10**9
                    lat_max = -10**9
                    lng_min = 10**9
                    lng_max = -10**9
                    for _, bbox in city["districts"].items():
                        lat_min = min(lat_min, float(bbox["lat_min"]))
                        lat_max = max(lat_max, float(bbox["lat_max"]))
                        lng_min = min(lng_min, float(bbox["lng_min"]))
                        lng_max = max(lng_max, float(bbox["lng_max"]))
                    return (lat_min, lat_max, lng_min, lng_max)
            except Exception:
                pass  # try next path

    # ENV fallback (ruime defaults; overschrijf in CI/ENV voor exacte grenzen)
    lat_min = float(os.getenv("ROTTERDAM_LAT_MIN", "51.845"))
    lat_max = float(os.getenv("ROTTERDAM_LAT_MAX", "51.990"))
    lng_min = float(os.getenv("ROTTERDAM_LNG_MIN", "4.340"))
    lng_max = float(os.getenv("ROTTERDAM_LNG_MAX", "4.650"))
    return (lat_min, lat_max, lng_min, lng_max)


_SQL_VERIFIED_RTM = text("""
    SELECT COUNT(*) AS verified_count
    FROM locations
    WHERE state = 'VERIFIED'
      AND lat BETWEEN :lat_min AND :lat_max
      AND lng BETWEEN :lng_min AND :lng_max
""")

_SQL_CANDIDATE_RTM = text("""
    SELECT COUNT(*) AS candidate_count
    FROM locations
    WHERE state = 'CANDIDATE'
      AND lat BETWEEN :lat_min AND :lat_max
      AND lng BETWEEN :lng_min AND :lng_max
""")

_SQL_NEW_VERIFIED_CURR_RTM = text("""
    SELECT COUNT(*) AS new_verified_curr
    FROM locations
    WHERE state = 'VERIFIED'
      AND last_verified_at IS NOT NULL
      AND last_verified_at >= (NOW() - INTERVAL '7 days')
      AND last_verified_at < NOW()
      AND lat BETWEEN :lat_min AND :lat_max
      AND lng BETWEEN :lng_min AND :lng_max
""")

_SQL_NEW_VERIFIED_PREV_RTM = text("""
    SELECT COUNT(*) AS new_verified_prev
    FROM locations
    WHERE state = 'VERIFIED'
      AND last_verified_at IS NOT NULL
      AND last_verified_at >= (NOW() - INTERVAL '14 days')
      AND last_verified_at < (NOW() - INTERVAL '7 days')
      AND lat BETWEEN :lat_min AND :lat_max
      AND lng BETWEEN :lng_min AND :lng_max
""")


def _growth_wow(curr: int, prev: int) -> float:
    denom = prev if prev > 0 else 1
    return (curr - prev) / float(denom)


async def kpi_city_progress_rotterdam(engine: AsyncEngine) -> KPIItem:
    """
    City-level KPI's voor **rotterdam** op basis van lat/lng binnen union(bbox districten).
    Output is een enkele rij voor 'rotterdam'.
    """
    lat_min, lat_max, lng_min, lng_max = _load_rotterdam_bbox()
    params = {"lat_min": lat_min, "lat_max": lat_max, "lng_min": lng_min, "lng_max": lng_max}

    async with engine.begin() as conn:
        verified = int((await conn.execute(_SQL_VERIFIED_RTM, params)).scalar() or 0)
        candidate = int((await conn.execute(_SQL_CANDIDATE_RTM, params)).scalar() or 0)
        curr = int((await conn.execute(_SQL_NEW_VERIFIED_CURR_RTM, params)).scalar() or 0)
        prev = int((await conn.execute(_SQL_NEW_VERIFIED_PREV_RTM, params)).scalar() or 0)

    coverage = verified / float(candidate if candidate > 0 else 1)
    growth = _growth_wow(curr, prev)

    row = {
        "city": "rotterdam",  # consistentie behouden
        "verified_count": verified,
        "candidate_count": candidate,
        "coverage_ratio": round(coverage, 4),
        "growth_weekly": round(growth, 4),
    }

    # 🔸 JSON-logging voor observability & alerts (AC eis)
    logger.info(
        "metrics_city_progress",
        city=row["city"],
        verified_count=row["verified_count"],
        candidate_count=row["candidate_count"],
        coverage_ratio=row["coverage_ratio"],
        growth_weekly=row["growth_weekly"],
        bbox={"lat_min": lat_min, "lat_max": lat_max, "lng_min": lng_min, "lng_max": lng_max},
    )

    return KPIItem(
        name="city_progress",
        value=[row],  # één stad: rotterdam
        meta={
            "goal_verified_per_city": 500,
            "filter": "bbox(rotterdam)",
            "bbox": {"lat_min": lat_min, "lat_max": lat_max, "lng_min": lng_min, "lng_max": lng_max},
        },
    )


# =========================================================
# Public API (ongewijzigd + extra KPI)
# =========================================================

async def generate_metrics_snapshot(
    engine: Optional[AsyncEngine] = None,
    weeks_for_new: int = 8,
    conversion_days: int = 14,
    error_rate_window: TimeWindow = TimeWindow(hours=1),
    latency_window: TimeWindow = TimeWindow(hours=1),
    google_window: TimeWindow = TimeWindow(hours=1),
) -> MetricsSnapshot:
    engine = engine or get_engine()
    kpis = [
        await kpi_new_candidates_per_week(engine, weeks=weeks_for_new),
        await kpi_conversion_rate_verified(engine, days=conversion_days),
        await kpi_task_error_rate(engine, window=error_rate_window),
        await kpi_api_latency(engine, window=latency_window),
        await kpi_google_429_count(engine, window=google_window),
        # 🔹 NIEUW: city-level KPI (Rotterdam via bbox)
        await kpi_city_progress_rotterdam(engine),
    ]
    return MetricsSnapshot(
        generated_at=_now_utc(),
        window_desc=(
            f"new={weeks_for_new}w, conv={conversion_days}d, "
            f"err={int(error_rate_window.to_timedelta().total_seconds()//60)}m, "
            f"lat={int(latency_window.to_timedelta().total_seconds()//60)}m, "
            f"g429={int(google_window.to_timedelta().total_seconds()//60)}m"
        ),
        kpis=kpis,
    )
