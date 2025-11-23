from __future__ import annotations

import argparse
import asyncio
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from app.models.event_raw import EventRaw
from app.models.event_sources import EventSource
from services.event_candidate_service import insert_event_candidate
from services.event_dedupe_service import run_dedupe
from services.event_normalization_service import (
    EventNormalizationError,
    normalize_event,
)
from services.event_raw_service import (
    fetch_pending_event_raw,
    update_event_raw_processing_state,
)
from services.event_sources_service import get_event_source
from services.worker_runs_service import (
    finish_worker_run,
    mark_worker_run_running,
    start_worker_run,
    update_worker_run_progress,
)

configure_logging(service_name="worker")
logger = get_logger().bind(worker="event_normalization_bot")

DEFAULT_LIMIT = 100


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EventNormalizationBot — convert event_raw rows into events_candidate.")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum number of pending rows to normalize (default: 100).",
    )
    parser.add_argument(
        "--worker-run-id",
        type=_parse_worker_run_id,
        default=None,
        help="Existing worker_runs UUID (optional).",
    )
    return parser.parse_args()


async def _get_source_cached(
    source_id: int,
    cache: Dict[int, EventSource],
) -> Optional[EventSource]:
    if source_id in cache:
        return cache[source_id]
    source = await get_event_source(source_id)
    if source:
        cache[source_id] = source
    return source


async def _process_raw_event(
    raw: EventRaw,
    source_cache: Dict[int, EventSource],
    counters: Dict[str, int],
) -> None:
    source = await _get_source_cached(raw.event_source_id, source_cache)
    if source is None:
        counters["errors"] += 1
        await update_event_raw_processing_state(
            raw.id,
            state="error_norm",
            errors={"reason": "missing_source"},
        )
        logger.error(
            "event_normalization_missing_source",
            event_raw_id=raw.id,
            event_source_id=raw.event_source_id,
        )
        return

    try:
        candidate = normalize_event(raw, source)
    except EventNormalizationError as exc:
        counters["errors"] += 1
        await update_event_raw_processing_state(
            raw.id,
            state="error_norm",
            errors={"reason": str(exc)},
        )
        logger.warning(
            "event_normalization_failed",
            event_raw_id=raw.id,
            error=str(exc),
        )
        return
    except Exception as exc:
        counters["errors"] += 1
        await update_event_raw_processing_state(
            raw.id,
            state="error_norm",
            errors={"reason": "unexpected_error", "error": str(exc)},
        )
        logger.error(
            "event_normalization_exception",
            event_raw_id=raw.id,
            error=str(exc),
        )
        return

    new_candidate_id = await insert_event_candidate(candidate)
    await update_event_raw_processing_state(raw.id, state="normalized", errors=None)
    counters["normalized"] += 1
    if new_candidate_id is not None:
        counters["dedupe_checked"] += 1
        try:
            result = await run_dedupe(new_candidate_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            counters["dedupe_errors"] += 1
            logger.error(
                "event_dedupe_failed",
                event_raw_id=raw.id,
                candidate_id=new_candidate_id,
                error=str(exc),
            )
        else:
            if result.duplicate_of_id:
                counters["dedupe_marked_duplicate"] += 1
            else:
                counters["dedupe_canonical"] += 1
    logger.info(
        "event_normalized",
        event_raw_id=raw.id,
        event_source_id=raw.event_source_id,
        ingest_hash=raw.ingest_hash,
    )


async def run_normalization(limit: int, worker_run_id: Optional[UUID]) -> int:
    run_id = worker_run_id or await start_worker_run(bot="event_normalization", city=None, category=None)
    await mark_worker_run_running(run_id)
    await update_worker_run_progress(run_id, 5)

    counters: Dict[str, int] = {
        "fetched": 0,
        "normalized": 0,
        "errors": 0,
        "dedupe_checked": 0,
        "dedupe_marked_duplicate": 0,
        "dedupe_canonical": 0,
        "dedupe_errors": 0,
    }
    progress = 5

    try:
        pending = await fetch_pending_event_raw(limit=limit)
        total = len(pending)
        counters["fetched"] = total

        if total == 0:
            await finish_worker_run(run_id, "finished", 100, counters, None)
            logger.info("event_normalization_no_pending_rows")
            return 0

        source_cache: Dict[int, EventSource] = {}
        for idx, raw in enumerate(pending, start=1):
            progress = 5 + int(idx * 95 / max(total, 1))
            await update_worker_run_progress(run_id, min(progress, 99))
            await _process_raw_event(raw, source_cache, counters)

        await finish_worker_run(run_id, "finished", 100, counters, None)
        logger.info(
            "event_normalization_complete",
            processed=total,
            normalized=counters["normalized"],
            errors=counters["errors"],
        )
        return 0
    except Exception as exc:
        logger.error("event_normalization_run_failed", error=str(exc))
        await finish_worker_run(run_id, "failed", progress, counters or None, str(exc))
        return 1


async def main_async() -> int:
    args = parse_args()
    with with_run_id():
        return await run_normalization(limit=max(1, args.limit), worker_run_id=args.worker_run_id)


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()


