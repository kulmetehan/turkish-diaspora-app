from __future__ import annotations

# Thin wrapper to ensure stable import path `app.services.metrics_service`
from services.metrics_service import category_health_metrics, generate_metrics_snapshot, location_state_metrics  # re-export

__all__ = ["category_health_metrics", "generate_metrics_snapshot", "location_state_metrics"]


