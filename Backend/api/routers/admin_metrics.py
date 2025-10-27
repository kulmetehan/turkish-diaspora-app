from __future__ import annotations

from fastapi import APIRouter

from app.models.metrics import MetricsSnapshot
from app.services.metrics_service import generate_metrics_snapshot


router = APIRouter(
    prefix="/admin/metrics",
    tags=["admin-metrics"],
)


@router.get("/snapshot", response_model=MetricsSnapshot)
async def get_metrics_snapshot() -> MetricsSnapshot:
    return await generate_metrics_snapshot()


