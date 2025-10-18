from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import structlog
from pydantic import BaseModel, Field, ConfigDict

# Belangrijk: importeer vanuit 'services' omdat metrics_service in Backend/services/ staat.
from services.metrics_service import (
    generate_metrics_snapshot,
    TimeWindow,
)

log = structlog.get_logger("alert_bot")

DEFAULT_ERR_RATE_THRESHOLD = 0.10  # 10% in window
DEFAULT_429_BURST_THRESHOLD = 5    # "burst" drempel


class AlertConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    check_interval_seconds: int = 60
    err_rate_window_minutes: int = 60
    err_rate_threshold: float = DEFAULT_ERR_RATE_THRESHOLD
    google429_window_minutes: int = 60
    google429_threshold: int = DEFAULT_429_BURST_THRESHOLD
    webhook_url: Optional[str] = Field(default=None)
    channel: Optional[str] = Field(default=None)


def _env_cfg() -> AlertConfig:
    return AlertConfig(
        check_interval_seconds=int(os.getenv("ALERT_CHECK_INTERVAL_SECONDS", "60")),
        err_rate_window_minutes=int(os.getenv("ALERT_ERR_RATE_WINDOW_MINUTES", "60")),
        err_rate_threshold=float(os.getenv("ALERT_ERR_RATE_THRESHOLD", str(DEFAULT_ERR_RATE_THRESHOLD))),
        google429_window_minutes=int(os.getenv("ALERT_GOOGLE429_WINDOW_MINUTES", "60")),
        google429_threshold=int(os.getenv("ALERT_GOOGLE429_THRESHOLD", str(DEFAULT_429_BURST_THRESHOLD))),
        webhook_url=os.getenv("ALERT_WEBHOOK_URL"),
        channel=os.getenv("ALERT_CHANNEL"),
    )


async def _post_webhook(url: str, payload: Dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload)
    except Exception as e:
        log.warning("alert_webhook_post_failed", error=str(e))


def _fmt_ratio(val: float) -> str:
    return f"{val:.2%}"


async def check_and_alert_once(cfg: AlertConfig) -> Dict[str, Any]:
    snapshot = await generate_metrics_snapshot(
        weeks_for_new=8,
        conversion_days=14,
        error_rate_window=TimeWindow(minutes=cfg.err_rate_window_minutes),
        latency_window=TimeWindow(minutes=cfg.err_rate_window_minutes),
        google_window=TimeWindow(minutes=cfg.google429_window_minutes),
    )

    # Relevante KPI's ophalen
    err_rate = next((k for k in snapshot.kpis if k.name == "task_error_rate"), None)
    g429 = next((k for k in snapshot.kpis if k.name == "google_api_429_count"), None)

    alerts = []
    if err_rate and isinstance(err_rate.value, float) and err_rate.value >= cfg.err_rate_threshold:
        alerts.append({
            "type": "TASK_FAILURE_SPIKE",
            "message": f"Task error rate {_fmt_ratio(err_rate.value)} >= threshold {_fmt_ratio(cfg.err_rate_threshold)} in last {cfg.err_rate_window_minutes}m.",
            "kpi": err_rate.model_dump(),
        })

    if g429 and isinstance(g429.value, int) and g429.value >= cfg.google429_threshold:
        alerts.append({
            "type": "GOOGLE_429_BURST",
            "message": f"Detected {g429.value} Google API 429 events in last {cfg.google429_window_minutes}m (>= {cfg.google429_threshold}).",
            "kpi": g429.model_dump(),
        })

    # Altijd snapshot loggen
    log.info("metrics_snapshot", snapshot=snapshot.model_dump())

    # Alerts uitsturen (console + optioneel webhook)
    for a in alerts:
        log.warning("alert_triggered", alert=a)
        if cfg.webhook_url:
            payload = {
                "text": f"[TDA-20 ALERT] {a['type']}: {a['message']}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "channel": cfg.channel,
                "data": a,
            }
            await _post_webhook(cfg.webhook_url, payload)

    return {
        "alerts_triggered": len(alerts),
        "alerts": alerts,
        "snapshot": snapshot.model_dump(),
    }


async def run_forever() -> None:
    cfg = _env_cfg()
    log.info("AlertBot_start", cfg=cfg.model_dump())
    while True:
        try:
            await check_and_alert_once(cfg)
        except Exception as e:
            log.error("alert_cycle_error", error=str(e))
        await asyncio.sleep(cfg.check_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_forever())
