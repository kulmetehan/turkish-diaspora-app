from __future__ import annotations

import argparse
import asyncio
from typing import Dict, Optional
from uuid import UUID

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.db_service import init_db_pool
from services.event_enrichment_service import EventEnrichmentService
from services.event_raw_service import (
    apply_event_enrichment,
    fetch_normalized_event_raw,
    mark_event_enrichment_error,
)
from services.worker_runs_service import (
    finish_worker_run,
    mark_worker_run_running,
    start_worker_run,
    update_worker_run_progress,
)

configure_logging(service_name="worker")
logger = get_logger().bind(worker="event_enrichment_bot")


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EventEnrichmentBot — AI enrichment for event_raw rows.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of rows to enrich.")
    parser.add_argument("--model", type=str, default=None, help="Optional OpenAI model override.")
    parser.add_argument(
        "--worker-run-id",
        type=_parse_worker_run_id,
        default=None,
        help="Existing worker_runs UUID (optional).",
    )
    return parser.parse_args()


async def run_enrichment(
    *,
    limit: int,
    model: Optional[str],
    worker_run_id: Optional[UUID],
) -> int:
    await init_db_pool()
    run_id = worker_run_id or await start_worker_run(bot="event_enrichment", city=None, category=None)
    await mark_worker_run_running(run_id)
    counters: Dict[str, int] = {"total": 0, "enriched": 0, "errors": 0, "locations_extracted": 0}
    progress = 5
    await update_worker_run_progress(run_id, progress)

    try:
        events = await fetch_normalized_event_raw(limit=max(0, int(limit)))
        counters["total"] = len(events)

        if not events:
            await finish_worker_run(run_id, "finished", 100, counters, None)
            logger.info("event_enrichment_no_normalized_rows")
            return 0

        service = EventEnrichmentService(model=model)

        for idx, event in enumerate(events, start=1):
            percent = min(99, max(5, int(idx * 100 / max(len(events), 1))))
            await update_worker_run_progress(run_id, percent)
            try:
                result, meta = service.enrich_event(event)
                await apply_event_enrichment(
                    event_id=int(event.id),
                    language_code=result.language_code,
                    category_key=result.category_key,
                    summary_ai=result.summary,
                    confidence_score=result.confidence_score,
                    extracted_location_text=result.extracted_location_text,
                )
                counters["enriched"] += 1
                if result.extracted_location_text:
                    counters["locations_extracted"] += 1
                logger.info(
                    "event_enrichment_success",
                    event_id=event.id,
                    category=result.category_key,
                    language=result.language_code,
                    confidence=result.confidence_score,
                    location_extracted=bool(result.extracted_location_text),
                    meta=meta,
                )
            except Exception as exc:
                counters["errors"] += 1
                logger.warning(
                    "event_enrichment_failed",
                    event_id=event.id,
                    error=str(exc),
                )
                await mark_event_enrichment_error(
                    event_id=int(event.id),
                    error={"error": str(exc)},
                )

        await finish_worker_run(run_id, "finished", 100, counters, None)
        return 0
    except Exception as exc:
        logger.error("event_enrichment_bot_failed", error=str(exc))
        await finish_worker_run(run_id, "failed", progress, counters or None, str(exc))
        return 1


async def main_async() -> int:
    args = parse_args()
    with with_run_id():
        return await run_enrichment(
            limit=args.limit,
            model=args.model,
            worker_run_id=args.worker_run_id,
        )


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()


