from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from services.db_service import fetch


logger = logging.getLogger(__name__)


def _timedelta_ms(start: Optional[datetime]) -> Optional[int]:
    if start is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return int((now - start).total_seconds() * 1000)


class DbSessionMonitor:
    """
    Periodically inspects pg_stat_activity for the application and emits structured
    logs when sessions are stuck idle in transaction.
    """

    def __init__(
        self,
        *,
        interval_seconds: int = 60,
        application_name: str = "tda-backend",
        limit: int = 25,
    ) -> None:
        self.interval_seconds = interval_seconds
        self.application_name = application_name
        self.limit = limit
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task[None]] = None

    def start(self) -> None:
        if self._task is not None:
            return
        loop = asyncio.get_running_loop()
        self._stop_event.clear()
        self._task = loop.create_task(self._run(), name="db-session-monitor")
        logger.info("db_session_monitor_started", extra={"interval_seconds": self.interval_seconds})

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None
            logger.info("db_session_monitor_stopped")

    async def _run(self) -> None:
        try:
            while not self._stop_event.is_set():
                try:
                    await self._sample_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("db_session_monitor_sample_failed")
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise

    async def _sample_once(self) -> None:
        sql = """
            SELECT
                pid,
                state,
                backend_start,
                xact_start,
                state_change,
                query
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND application_name = $1
            ORDER BY xact_start NULLS LAST
            LIMIT $2
        """
        rows = await fetch(sql, self.application_name, int(self.limit))

        summaries: List[Dict[str, Any]] = []
        idle_sessions = 0
        longest_idle_ms: Optional[int] = None

        for row in rows:
            record = dict(row)
            state = (record.get("state") or "").lower()
            if state == "idle in transaction":
                idle_sessions += 1
                age_ms = _timedelta_ms(record.get("xact_start"))
                if age_ms is not None:
                    if longest_idle_ms is None or age_ms > longest_idle_ms:
                        longest_idle_ms = age_ms
                summaries.append(
                    {
                        "pid": record.get("pid"),
                        "xact_age_ms": age_ms,
                        "state_age_ms": _timedelta_ms(record.get("state_change")),
                        "query": (record.get("query") or "")[:200],
                    }
                )

        if idle_sessions:
            logger.warning(
                "db_idle_transactions_detected",
                extra={
                    "idle_sessions": idle_sessions,
                    "longest_idle_ms": longest_idle_ms,
                    "samples": summaries[:5],
                },
            )
        else:
            logger.debug(
                "db_sessions_healthy",
                extra={
                    "checked_sessions": len(rows),
                },
            )

