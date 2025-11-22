from __future__ import annotations

from fastapi import APIRouter

from app.models.metrics import (
    CategoryHealthResponse,
    LocationStateMetrics,
    MetricsSnapshot,
    NewsMetricsSnapshot,
)
from app.services.metrics_service import (
    category_health_metrics,
    generate_metrics_snapshot,
    generate_news_metrics_snapshot,
    location_state_metrics,
)


router = APIRouter(
    prefix="/admin/metrics",
    tags=["admin-metrics"],
)


@router.get("/snapshot", response_model=MetricsSnapshot)
async def get_metrics_snapshot() -> MetricsSnapshot:
    return await generate_metrics_snapshot()


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
    return await generate_news_metrics_snapshot()


