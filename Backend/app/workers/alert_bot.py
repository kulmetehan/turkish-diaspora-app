from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, Field, ConfigDict

# ---------------------------------------------------------------------------
# Pathing zodat 'app.*' en 'services.*' werken (CI, GH Actions, lokale run)
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent           # .../Backend/app
BACKEND_DIR = APP_DIR.parent                # .../Backend

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))    # .../Backend

# --- Uniform logging voor workers ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="alert_bot")

# DB helpers (asyncpg)
from services.db_service import init_db_pool, fetch, execute  # noqa: E402

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
        logger.warning("alert_webhook_post_failed", error=str(e))


def _fmt_ratio(val: float) -> str:
    return f"{val:.2%}"


async def _task_error_rate(window_minutes: int) -> float:
    # window_minutes is already an int

    logs_total = (
        """
        SELECT COUNT(*) AS n
        FROM ai_logs
        WHERE created_at >= NOW() - (($1::int || ' minutes')::interval)
        """
    )
    rows_total = await fetch(logs_total, int(window_minutes))
    total = rows_total[0]["n"] if rows_total else 0

    logs_errors = (
        """
        SELECT COUNT(*) AS n
        FROM ai_logs
        WHERE created_at >= NOW() - (($1::int || ' minutes')::interval)
          AND (is_success = false OR error_message IS NOT NULL)
        """
    )
    rows_err = await fetch(logs_errors, int(window_minutes))
    err = rows_err[0]["n"] if rows_err else 0

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
    return rows[0]["n"] if rows else 0


async def check_and_alert_once(cfg: AlertConfig) -> Dict[str, Any]:
    err_rate = await _task_error_rate(cfg.err_rate_window_minutes)
    g429 = await _google429_bursts(cfg.google429_window_minutes)

    # Altijd snapshot loggen
    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kpis": {
            "task_error_rate": err_rate,
            "google_api_429_count": g429,
        },
        "windows": {
            "err_rate_minutes": cfg.err_rate_window_minutes,
            "google_minutes": cfg.google429_window_minutes,
        },
    }
    logger.info("metrics_snapshot", snapshot=snapshot)

    alerts: list[dict[str, Any]] = []
    if err_rate >= cfg.err_rate_threshold:
        alerts.append({
            "type": "TASK_FAILURE_SPIKE",
            "message": f"Task error rate {_fmt_ratio(err_rate)} >= threshold {_fmt_ratio(cfg.err_rate_threshold)} in last {cfg.err_rate_window_minutes}m.",
        })
    if g429 >= cfg.google429_threshold:
        alerts.append({
            "type": "GOOGLE_429_BURST",
            "message": f"Detected {g429} Google API 429 events in last {cfg.google429_window_minutes}m (>= {cfg.google429_threshold}).",
        })

    for a in alerts:
        logger.warning("alert_triggered", alert=a)
        if cfg.webhook_url:
            payload = {
                "text": f"[TDA-20 ALERT] {a['type']}: {a['message']}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "channel": cfg.channel,
                "data": a,
            }
            await _post_webhook(cfg.webhook_url, payload)

    return {"alerts_triggered": len(alerts), "alerts": alerts, "snapshot": snapshot}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TDA Alert Bot")
    p.add_argument("--once", action="store_true", help="Run one check and exit")
    return p.parse_args()


async def main_async() -> None:
    with with_run_id() as rid:
        logger.info("worker_started")
        await init_db_pool()
        cfg = _env_cfg()
        logger.info("alert_worker_config", cfg=cfg.model_dump())

        args = _parse_args()
        run_once = args.once or (os.getenv("ALERT_RUN_ONCE", "0").strip().lower() in ("1", "true", "yes", "y"))
        if run_once:
            await check_and_alert_once(cfg)
            return

        cycle = 0
        while True:
            try:
                res = await check_and_alert_once(cfg)
                if cycle % 20 == 0:
                    logger.info("worker_heartbeat", alerts_triggered=res["alerts_triggered"]) 
                cycle += 1
            except Exception as e:
                logger.error("alert_cycle_error", error=str(e))
            await asyncio.sleep(cfg.check_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main_async())
