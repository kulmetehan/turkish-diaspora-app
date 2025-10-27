from __future__ import annotations

# Thin wrapper to ensure stable import path `app.services.metrics_service`
from services.metrics_service import generate_metrics_snapshot  # re-export

__all__ = ["generate_metrics_snapshot"]


