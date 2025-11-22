from __future__ import annotations

# Thin wrapper to ensure stable import path `app.services.metrics_service`
from services.metrics_service import (  # re-export
    category_health_metrics,
    generate_metrics_snapshot,
    generate_news_metrics_snapshot,
    location_state_metrics,
)

__all__ = [
    "category_health_metrics",
    "generate_metrics_snapshot",
    "generate_news_metrics_snapshot",
    "location_state_metrics",
]


