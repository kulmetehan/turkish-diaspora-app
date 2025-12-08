from __future__ import annotations

import asyncpg
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import APIRouter, HTTPException

from app.models.metrics import (
    CategoryHealthResponse,
    EventMetricsSnapshot,
    LocationStateMetrics,
    MetricsSnapshot,
    NewsMetricsSnapshot,
)
from app.services.metrics_service import (
    category_health_metrics,
    generate_event_metrics_snapshot,
    generate_metrics_snapshot,
    generate_news_metrics_snapshot,
    location_state_metrics,
)


router = APIRouter(
    prefix="/admin/metrics",
    tags=["admin-metrics"],
)

# Simple in-memory cache for metrics snapshot
# Cache for 30 seconds to reduce database load while keeping data reasonably fresh
_metrics_cache: Optional[Tuple[datetime, MetricsSnapshot]] = None
_METRICS_CACHE_TTL = timedelta(seconds=30)


@router.get("/snapshot", response_model=MetricsSnapshot)
async def get_metrics_snapshot() -> MetricsSnapshot:
    """
    Get metrics snapshot with 30-second caching to reduce database load.
    
    The cache helps prevent slow query issues when multiple admin users
    access the dashboard simultaneously, especially during active discovery runs.
    """
    global _metrics_cache
    
    # Check cache
    now = datetime.now(timezone.utc)
    if _metrics_cache is not None:
        cached_time, cached_snapshot = _metrics_cache
        if now - cached_time < _METRICS_CACHE_TTL:
            return cached_snapshot
    
    # Generate fresh snapshot
    snapshot = await generate_metrics_snapshot()
    
    # Update cache
    _metrics_cache = (now, snapshot)
    
    return snapshot


@router.get("/categories", response_model=CategoryHealthResponse)
async def get_category_health_metrics() -> CategoryHealthResponse:
    """
    Returns category-level health KPIs for all discovery-enabled categories.
    
    Includes:
    - Overpass calls and zero-result ratio (last 72h)
    - Inserted locations and state breakdown (last 7d)
    - AI classification stats (last 7d)
    - Promotions to VERIFIED (last 7d)
    """
    return await category_health_metrics()


@router.get("/location_states", response_model=LocationStateMetrics)
async def get_location_state_metrics() -> LocationStateMetrics:
    """
    Returns location state breakdown metrics.
    
    Includes:
    - Total location count
    - Count per state: CANDIDATE, PENDING_VERIFICATION, VERIFIED, RETIRED, SUSPENDED
    """
    return await location_state_metrics()


@router.get("/news", response_model=NewsMetricsSnapshot)
async def get_news_metrics_snapshot() -> NewsMetricsSnapshot:
    """
    Returns ingest, feed distribution, and error stats for the news pipeline.
    
    Includes:
    - Items per day (last 7 days)
    - Items by source (last 24h)
    - Items by feed (last 24h)
    - Error counters for ingest/classification
    """
    try:
        return await generate_news_metrics_snapshot()
    except (asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        raise HTTPException(status_code=503, detail="news metrics unavailable") from exc


@router.get("/events", response_model=EventMetricsSnapshot)
async def get_event_metrics_snapshot() -> EventMetricsSnapshot:
    """
    Returns per-day, per-source, and enrichment stats for the event pipeline.
    
    Includes:
    - Events per day (last 7 days)
    - Per-source counts & last success/error metadata (last 24h)
    - Total inserts in the last 30 days
    - Enrichment coverage/errors, average confidence, and top categories
    """
    try:
        return await generate_event_metrics_snapshot()
    except (asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        raise HTTPException(status_code=503, detail="event metrics unavailable") from exc


