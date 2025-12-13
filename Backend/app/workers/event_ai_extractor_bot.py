from __future__ import annotations

import argparse
import asyncio
from typing import Dict, List, Optional, Sequence, Tuple
from uuid import UUID

import httpx

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from app.models.event_pages_raw import EventPageRaw
from app.models.event_sources import EventSource
from app.models.event_extraction import ExtractedEvent, ExtractedEventsPayload
from app.models.event_raw import EventRawCreate
from app.workers.event_scraper_bot import EventScraperService
from services.event_extraction_service import EventExtractionService
from services.event_pages_raw_service import (
    fetch_pending_event_pages,
    update_event_page_processing_state,
)
from services.event_raw_service import insert_event_raw, update_event_raw_from_detail_page
from services.event_sources_service import get_event_source
from services.db_service import fetchrow
from services.worker_runs_service import (
    finish_worker_run,
    mark_worker_run_running,
    start_worker_run,
    update_worker_run_progress,
)

configure_logging(service_name="worker")
logger = get_logger().bind(worker="event_ai_extractor_bot")

DEFAULT_LIMIT = 20
DEFAULT_CHUNK_SIZE = 16000
AI_PAGE_SOURCE_KEYS: set[str] = {"sahmeran_events", "ajda_events", "ediz_events"}


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:  # pragma: no cover
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EventAIExtractorBot — turn HTML pages into event_raw rows via OpenAI."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum number of pending pages to process (default: 20).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Max characters per HTML chunk sent to OpenAI (default: 16000).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Optional OpenAI model override.",
    )
    parser.add_argument(
        "--worker-run-id",
        type=_parse_worker_run_id,
        default=None,
        help="Existing worker_runs UUID (optional).",
    )
    return parser.parse_args()


def _chunk_html(body: str, chunk_size: int) -> List[str]:
    text = body.strip()
    if not text:
        return []
    if chunk_size <= 0 or len(text) <= chunk_size:
        return [text]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


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


def _dedupe_events(events: Sequence[ExtractedEvent]) -> List[ExtractedEvent]:
    seen: Dict[Tuple[str, str, str], ExtractedEvent] = {}
    for event in events:
        # Handle None start_at for dedupe key
        start_at_str = event.start_at.isoformat() if event.start_at else ""
        key = (
            event.title.strip().lower(),
            start_at_str,
            (event.event_url or "").strip().lower(),
        )
        seen[key] = event
    return list(seen.values())


async def _fetch_and_extract_detail_page(
    event_url: str,
    *,
    extraction_service: EventExtractionService,
    source: EventSource,
    event_raw_id: Optional[int] = None,
) -> Optional[ExtractedEvent]:
    """
    Fetch a detail page and extract event data from it.
    Returns the extracted event or None if extraction fails.
    """
    try:
        # Normalize URL: convert relative to absolute if needed
        absolute_url = event_url
        if event_url and not event_url.startswith(("http://", "https://")):
            from urllib.parse import urljoin
            base_url = source.base_url or source.list_url or ""
            if base_url:
                base_url = base_url.rstrip("/")
                if not event_url.startswith("/"):
                    event_url = "/" + event_url
                absolute_url = urljoin(base_url, event_url)
            else:
                logger.warning(
                    "event_detail_page_relative_url_no_base",
                    event_url=event_url,
                    event_raw_id=event_raw_id,
                )
                return None

        timeout = httpx.Timeout(15.0)
        async with httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "tda-event-detail-extractor/1.0"},
            follow_redirects=True,
        ) as client:
            response = await client.get(absolute_url)
            response.raise_for_status()
            html = response.text

            # Extract event data from detail page
            payload, _meta = extraction_service.extract_events_from_html(
                html=html,
                source_key=source.key,
                page_url=absolute_url,
                event_source_id=source.id,
            )

            # Take the first event (detail pages usually have one event)
            if payload.events:
                return payload.events[0]
            return None

    except Exception as exc:
        logger.warning(
            "event_detail_page_extraction_failed",
            event_url=event_url,
            event_raw_id=event_raw_id,
            error=str(exc),
        )
        return None


async def _enrich_events_with_detail_pages(
    events: List[ExtractedEvent],
    *,
    extraction_service: EventExtractionService,
    source: EventSource,
    counters: Dict[str, int],
    event_raw_ids: Dict[Tuple[str, str], int],  # Maps (title_lower, event_url_lower) -> event_raw_id
) -> None:
    """
    For events that have event_url but missing start_at, fetch detail pages
    and extract missing data, then update the corresponding event_raw records.
    """
    for event in events:
        # Check if event has URL but missing start_at
        if event.event_url and not event.start_at:
            counters["detail_pages_fetched"] = counters.get("detail_pages_fetched", 0) + 1

            # Fetch and extract from detail page
            detail_event = await _fetch_and_extract_detail_page(
                event.event_url,
                extraction_service=extraction_service,
                source=source,
            )

            if detail_event and detail_event.start_at:
                # Find the corresponding event_raw_id
                key = (event.title.strip().lower(), event.event_url.strip().lower())
                event_raw_id = event_raw_ids.get(key)

                if event_raw_id:
                    # Update event_raw with data from detail page
                    raw_payload_updates = {
                        "detail_page_extracted": True,
                        "detail_page_url": event.event_url,
                        "detail_page_extracted_event": detail_event.model_dump(mode="json"),
                    }

                    await update_event_raw_from_detail_page(
                        event_raw_id,
                        start_at=detail_event.start_at,
                        end_at=detail_event.end_at,
                        description=detail_event.description or event.description,
                        location_text=detail_event.location_text or event.location_text,
                        venue=detail_event.venue or event.venue,
                        image_url=detail_event.image_url or event.image_url,
                        raw_payload_updates=raw_payload_updates,
                    )

                    counters["detail_pages_success"] = counters.get("detail_pages_success", 0) + 1
                    logger.info(
                        "event_enriched_from_detail_page",
                        event_raw_id=event_raw_id,
                        event_url=event.event_url,
                        start_at=detail_event.start_at.isoformat() if detail_event.start_at else None,
                    )
                else:
                    counters["detail_pages_no_event_raw_id"] = counters.get("detail_pages_no_event_raw_id", 0) + 1
            else:
                counters["detail_pages_no_start_at"] = counters.get("detail_pages_no_start_at", 0) + 1


async def _process_page(
    page: EventPageRaw,
    *,
    chunk_size: int,
    extraction_service: EventExtractionService,
    source_cache: Dict[int, EventSource],
    counters: Dict[str, int],
) -> None:
    source = await _get_source_cached(page.event_source_id, source_cache)
    if source is None:
        await update_event_page_processing_state(
            page.id,
            state="error_extract",
            errors={"reason": "missing_source"},
        )
        counters["pages_failed"] += 1
        logger.error(
            "event_ai_extractor_missing_source",
            page_id=page.id,
            event_source_id=page.event_source_id,
        )
        return

    chunks = _chunk_html(page.response_body, chunk_size)
    if not chunks:
        await update_event_page_processing_state(
            page.id,
            state="error_extract",
            errors={"reason": "empty_body"},
        )
        counters["pages_failed"] += 1
        return

    extracted_events: List[ExtractedEvent] = []
    for idx, chunk in enumerate(chunks):
        try:
            payload, _meta = extraction_service.extract_events_from_html(
                html=chunk,
                source_key=source.key,
                page_url=page.page_url,
                event_source_id=page.event_source_id,
            )
        except Exception as exc:
            await update_event_page_processing_state(
                page.id,
                state="error_extract",
                errors={"reason": "openai_error", "error": str(exc), "chunk": idx},
            )
            counters["pages_failed"] += 1
            logger.warning(
                "event_ai_extractor_chunk_failed",
                page_id=page.id,
                chunk_index=idx,
                error=str(exc),
            )
            return
        extracted_events.extend(payload.events)

    deduped = _dedupe_events(extracted_events)
    counters["events_extracted_total"] += len(deduped)
    new_events = 0

    # Map to track event_raw_id by (title_lower, event_url_lower) for detail page enrichment
    event_raw_ids: Dict[Tuple[str, str], int] = {}

    for event in deduped:
        ingest_hash = EventScraperService._compute_ingest_hash(
            source_id=page.event_source_id,
            event_url=event.event_url,
            start_at=event.start_at,
            title=event.title,
        )
        raw_payload = {
            "extracted_via": "event_ai_extractor_bot",
            "source_page_id": page.id,
            "source_page_url": page.page_url,
            "chunk_count": len(chunks),
            "extracted_event": event.model_dump(mode="json"),
        }
        raw = EventRawCreate(
            event_source_id=page.event_source_id,
            title=event.title,
            description=event.description,
            location_text=event.location_text,
            venue=event.venue,
            event_url=event.event_url,
            image_url=event.image_url,
            start_at=event.start_at,
            end_at=event.end_at,
            detected_format="json",
            ingest_hash=ingest_hash,
            raw_payload=raw_payload,
            processing_state="pending",
        )
        inserted_id = await insert_event_raw(raw)
        if inserted_id is not None:
            new_events += 1
            counters["events_created_new"] += 1
            # Track event_raw_id for detail page enrichment
            if event.event_url:
                key = (event.title.strip().lower(), event.event_url.strip().lower())
                event_raw_ids[key] = inserted_id
        else:
            counters["events_skipped_existing"] += 1
            # For existing events, we might still want to enrich if start_at is missing
            # Fetch the existing event_raw_id
            if event.event_url and not event.start_at:
                existing = await fetchrow(
                    """
                    SELECT id FROM event_raw
                    WHERE event_source_id = $1
                      AND event_url = $2
                      AND title = $3
                      AND start_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    page.event_source_id,
                    event.event_url,
                    event.title,
                )
                if existing:
                    key = (event.title.strip().lower(), event.event_url.strip().lower())
                    event_raw_ids[key] = existing["id"]

    # Enrich events with detail pages if needed
    await _enrich_events_with_detail_pages(
        deduped,
        extraction_service=extraction_service,
        source=source,
        counters=counters,
        event_raw_ids=event_raw_ids,
    )

    await update_event_page_processing_state(page.id, state="extracted", errors=None)
    counters["pages_processed"] += 1
    logger.info(
        "event_ai_extractor_page_complete",
        page_id=page.id,
        new_events=new_events,
        total_events=len(deduped),
    )


async def run_extractor(
    *,
    limit: int,
    chunk_size: int,
    model: Optional[str],
    worker_run_id: Optional[UUID],
) -> int:
    run_id = worker_run_id or await start_worker_run(bot="event_ai_extractor", city=None, category=None)
    await mark_worker_run_running(run_id)
    progress = 5
    await update_worker_run_progress(run_id, progress)

    counters: Dict[str, int] = {
        "pages_fetched": 0,
        "pages_processed": 0,
        "pages_failed": 0,
        "events_extracted_total": 0,
        "events_created_new": 0,
        "events_skipped_existing": 0,
        "detail_pages_fetched": 0,
        "detail_pages_success": 0,
        "detail_pages_no_start_at": 0,
        "detail_pages_no_event_raw_id": 0,
    }

    try:
        pages = await fetch_pending_event_pages(limit=max(1, limit))
        counters["pages_fetched"] = len(pages)
        if not pages:
            await finish_worker_run(run_id, "finished", 100, counters, None)
            logger.info("event_ai_extractor_no_pending_pages")
            return 0

        extraction_service = EventExtractionService(model=model)
        source_cache: Dict[int, EventSource] = {}
        for idx, page in enumerate(pages, start=1):
            progress = 5 + int(idx * 95 / max(len(pages), 1))
            await update_worker_run_progress(run_id, min(progress, 99))
            await _process_page(
                page,
                chunk_size=chunk_size,
                extraction_service=extraction_service,
                source_cache=source_cache,
                counters=counters,
            )

        await finish_worker_run(run_id, "finished", 100, counters, None)
        return 0
    except Exception as exc:
        logger.error("event_ai_extractor_failed", error=str(exc))
        await finish_worker_run(run_id, "failed", progress, counters or None, str(exc))
        return 1


async def main_async() -> int:
    args = parse_args()
    with with_run_id():
        return await run_extractor(
            limit=args.limit,
            chunk_size=max(1, args.chunk_size),
            model=args.model,
            worker_run_id=args.worker_run_id,
        )


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()


