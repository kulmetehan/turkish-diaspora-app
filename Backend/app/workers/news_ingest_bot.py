from __future__ import annotations

import argparse
import asyncio
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.news_ingest_service import ingest_all_sources
from services.worker_runs_service import (
    finish_worker_run,
    mark_worker_run_running,
    start_worker_run,
    update_worker_run_progress,
)

configure_logging(service_name="worker")
logger = get_logger().bind(worker="news_ingest_bot")


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NewsIngestBot — fetch RSS feeds and store raw news items.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of sources to ingest during this run.",
    )
    parser.add_argument(
        "--worker-run-id",
        type=_parse_worker_run_id,
        help="Optional worker run UUID for orchestration integration.",
    )
    return parser.parse_args()


async def run_ingest(limit: Optional[int], worker_run_id: Optional[UUID]) -> int:
    run_id = worker_run_id
    if run_id is None:
        run_id = await start_worker_run(bot="news_ingest", city=None, category=None)

    await mark_worker_run_running(run_id)
    await update_worker_run_progress(run_id, 5)

    counters: Dict[str, Any] = {}
    progress = 5
    try:
        result = await ingest_all_sources(limit=limit)
        counters = result
        progress = 100
        await finish_worker_run(run_id, "finished", progress, counters, None)
        logger.info(
            "news_ingest_bot_finished",
            total_sources=result.get("total_sources"),
            total_inserted=result.get("total_inserted"),
            degraded=result.get("degraded"),
        )
        return 0
    except Exception as exc:
        logger.error("news_ingest_bot_failed", error=str(exc))
        await finish_worker_run(run_id, "failed", progress, counters or None, str(exc))
        return 1


async def main_async() -> int:
    args = parse_args()
    with with_run_id():
        return await run_ingest(limit=args.limit, worker_run_id=args.worker_run_id)


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

