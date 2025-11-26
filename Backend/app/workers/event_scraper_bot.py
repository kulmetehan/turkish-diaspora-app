from __future__ import annotations

import argparse
import asyncio
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from app.models.event_sources import EventSource
from services.event_scraper_service import EventScraperResult, EventScraperService
from services.event_sources_service import list_event_sources, mark_event_source_run
from services.worker_runs_service import (
    finish_worker_run,
    mark_worker_run_running,
    start_worker_run,
    update_worker_run_progress,
)

configure_logging(service_name="worker")
logger = get_logger().bind(worker="event_scraper_bot")


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EventScraperBot — scrape diaspora event sources.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on the number of sources to scrape in this run.",
    )
    parser.add_argument(
        "--worker-run-id",
        type=_parse_worker_run_id,
        default=None,
        help="Existing worker_runs UUID (optional).",
    )
    return parser.parse_args()


async def run_scraper(limit: Optional[int], worker_run_id: Optional[UUID]) -> int:
    run_id = worker_run_id or await start_worker_run(bot="event_scraper", city=None, category=None)
    await mark_worker_run_running(run_id)
    await update_worker_run_progress(run_id, 5)

    counters: Dict[str, Any] = {
        "total_sources": 0,
        "processed_sources": 0,
        "skipped_sources": 0,
        "error_sources": 0,
        "total_items": 0,
        "inserted_items": 0,
    }
    progress = 5

    try:
        sources = await list_event_sources(status="active")
        if limit is not None and limit >= 0:
            sources = sources[:limit]
        counters["total_sources"] = len(sources)

        if not sources:
            await finish_worker_run(run_id, "finished", 100, counters, None)
            logger.info("event_scraper_no_sources_configured")
            return 0

        async with EventScraperService() as service:
            for idx, source in enumerate(sources, start=1):
                progress = 5 + int(idx * 95 / max(len(sources), 1))
                await update_worker_run_progress(run_id, min(progress, 99))
                await _process_single_source(service, source, counters)

        await finish_worker_run(run_id, "finished", 100, counters, None)
        logger.info(
            "event_scraper_bot_finished",
            total_sources=counters["total_sources"],
            inserted=counters["inserted_items"],
            errors=counters["error_sources"],
        )
        return 0
    except Exception as exc:
        logger.error("event_scraper_bot_failed", error=str(exc))
        await finish_worker_run(run_id, "failed", progress, counters or None, str(exc))
        return 1


async def _process_single_source(
    service: EventScraperService,
    source: EventSource,
    counters: Dict[str, Any],
) -> None:
    try:
        result: EventScraperResult = await service.scrape_source(source)
    except Exception as exc:
        logger.error(
            "event_scraper_source_exception",
            source_id=source.id,
            key=source.key,
            error=str(exc),
        )
        counters["error_sources"] += 1
        await mark_event_source_run(source.id, success=False, error_message=str(exc))
        return

    if result.skipped:
        counters["skipped_sources"] += 1
        return

    counters["processed_sources"] += 1
    counters["total_items"] += result.total_items
    counters["inserted_items"] += result.inserted

    if result.errors > 0:
        counters["error_sources"] += 1
        await mark_event_source_run(source.id, success=False, error_message="scrape_errors")
    else:
        await mark_event_source_run(source.id, success=True, error_message=None)


async def main_async() -> int:
    args = parse_args()
    with with_run_id():
        return await run_scraper(limit=args.limit, worker_run_id=args.worker_run_id)


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()




