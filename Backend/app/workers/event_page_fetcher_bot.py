from __future__ import annotations

import argparse
import asyncio
import hashlib
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

import httpx

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from app.models.event_pages_raw import EventPageRawCreate
from app.models.event_sources import EventSource
from services.event_pages_raw_service import insert_event_page_raw
from services.event_sources_service import list_event_sources
from services.worker_runs_service import (
    finish_worker_run,
    mark_worker_run_running,
    start_worker_run,
    update_worker_run_progress,
)

configure_logging(service_name="worker")
logger = get_logger().bind(worker="event_page_fetcher_bot")

AI_PAGE_SOURCE_KEYS: set[str] = {
    "sahmeran_events",
    "ajda_events",
    "ediz_events",
    "meervaart_events",
    "melkweg_events",
    "paradiso_events",
    "dedoelen_events",
    "podiummozaiek_events",
    "tivolivredenburg_events",
    "bitterzoet_events",
    "muziekgebouw_events",
}


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:  # pragma: no cover - argparse validation
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EventPageFetcherBot — store full HTML pages for AI extraction."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of sources to fetch this run.",
    )
    parser.add_argument(
        "--source-key",
        type=str,
        default=None,
        help="Restrict fetching to a single source key.",
    )
    parser.add_argument(
        "--worker-run-id",
        type=_parse_worker_run_id,
        default=None,
        help="Existing worker_runs UUID (optional).",
    )
    return parser.parse_args()


def _select_sources(
    sources: Sequence[EventSource],
    *,
    source_key: Optional[str],
    limit: Optional[int],
) -> List[EventSource]:
    filtered = [s for s in sources if s.key in AI_PAGE_SOURCE_KEYS]
    if source_key:
        normalized = source_key.strip().lower()
        filtered = [s for s in filtered if s.key == normalized]
    if limit is not None and limit >= 0:
        filtered = filtered[:limit]
    return filtered


def _compute_content_hash(source_id: int, page_url: str, body: str) -> str:
    payload = f"{source_id}|{page_url}|{body}"
    return hashlib.sha1(payload.encode("utf-8", "ignore")).hexdigest()


async def _fetch_page_content(client: httpx.AsyncClient, url: str) -> tuple[int, Dict[str, Any], str]:
    response = await client.get(url)
    response.raise_for_status()
    headers = dict(response.headers or {})
    return response.status_code, headers, response.text


async def _process_single_source(
    client: httpx.AsyncClient,
    source: EventSource,
    counters: Dict[str, int],
) -> None:
    page_url = source.list_url or source.base_url
    state = "pending"
    errors: Optional[Dict[str, Any]] = None
    http_status: Optional[int] = None
    headers: Dict[str, Any] = {}
    body: str

    try:
        http_status, headers, body = await _fetch_page_content(client, page_url)
        counters["pages_fetched"] += 1
    except Exception as exc:
        state = "error_fetch"
        errors = {"error": str(exc)}
        counters["fetch_errors"] += 1
        body = f"FETCH_ERROR: {exc}"
        logger.warning(
            "event_page_fetch_failed",
            source_id=source.id,
            key=source.key,
            url=page_url,
            error=str(exc),
        )

    content_hash = _compute_content_hash(source.id, page_url, body)
    payload = EventPageRawCreate(
        event_source_id=source.id,
        page_url=page_url,
        http_status=http_status,
        response_headers=headers,
        response_body=body,
        content_hash=content_hash,
        processing_state=state,
        processing_errors=errors,
    )

    new_id = await insert_event_page_raw(payload)
    if new_id is not None:
        counters["pages_inserted"] += 1
        logger.info(
            "event_page_stored",
            source_id=source.id,
            key=source.key,
            page_id=new_id,
            state=state,
        )
    else:
        counters["pages_deduped"] += 1


async def run_fetcher(
    *,
    limit: Optional[int],
    source_key: Optional[str],
    worker_run_id: Optional[UUID],
) -> int:
    run_id = worker_run_id or await start_worker_run(bot="event_page_fetcher", city=None, category=None)
    await mark_worker_run_running(run_id)
    progress = 5
    await update_worker_run_progress(run_id, progress)

    counters: Dict[str, int] = {
        "total_sources": 0,
        "pages_fetched": 0,
        "pages_inserted": 0,
        "pages_deduped": 0,
        "fetch_errors": 0,
    }

    try:
        sources = await list_event_sources(status="active")
        selected = _select_sources(sources, source_key=source_key, limit=limit)
        counters["total_sources"] = len(selected)

        if not selected:
            await finish_worker_run(run_id, "finished", 100, counters, None)
            logger.info("event_page_fetcher_no_sources")
            return 0

        timeout = httpx.Timeout(15.0)
        async with httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "tda-event-page-fetcher/1.0"},
            follow_redirects=True,
        ) as client:
            for idx, source in enumerate(selected, start=1):
                progress = 5 + int(idx * 95 / max(len(selected), 1))
                await update_worker_run_progress(run_id, min(progress, 99))
                await _process_single_source(client, source, counters)

        await finish_worker_run(run_id, "finished", 100, counters, None)
        return 0
    except Exception as exc:
        logger.error("event_page_fetcher_failed", error=str(exc))
        await finish_worker_run(run_id, "failed", progress, counters or None, str(exc))
        return 1


async def main_async() -> int:
    args = parse_args()
    with with_run_id():
        return await run_fetcher(
            limit=args.limit,
            source_key=args.source_key,
            worker_run_id=args.worker_run_id,
        )


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()


