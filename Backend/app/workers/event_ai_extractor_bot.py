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


def _is_location_only_city_name(location_text: Optional[str]) -> bool:
    """
    Check if location_text contains only a city name (no full address).
    A full address typically contains:
    - Street name + number (digits)
    - Postal code (4 digits + 2 letters in NL, or similar patterns)
    - Venue name + address combination
    """
    if not location_text:
        return False
    
    location = location_text.strip()
    
    # If it contains digits, it's likely an address (street number or postal code)
    if any(char.isdigit() for char in location):
        return False
    
    # If it contains common address indicators
    address_indicators = [
        'straat', 'street', 'weg', 'laan', 'plein', 'square', 'boulevard',
        'avenue', 'dreef', 'kade', 'quay', 'hof', 'court', 'park', 'park',
        'road', 'drive', 'lane', 'place', 'plaza'
    ]
    location_lower = location.lower()
    if any(indicator in location_lower for indicator in address_indicators):
        return False
    
    # If it contains a comma, it might be "venue, address" or "address, city"
    if ',' in location:
        return False
    
    # If it's very short (likely just a city name)
    # Most city names are 3-20 characters, but addresses are longer
    if len(location) < 30 and not any(char.isdigit() for char in location):
        # Check if it looks like a single word or simple city name
        words = location.split()
        if len(words) <= 3:  # "Rotterdam", "New York", "Den Haag"
            return True
    
    return False


def _is_location_better_than_current(
    current_location: Optional[str],
    new_location: Optional[str],
) -> bool:
    """
    Check if new_location is better (more complete) than current_location.
    A location is better if:
    - It contains a full address (street + number + postal code) vs just city name
    - It contains venue information
    """
    if not new_location:
        return False
    
    if not current_location:
        return True
    
    # If current is only a city name and new has more info, it's better
    if _is_location_only_city_name(current_location):
        if not _is_location_only_city_name(new_location):
            return True
        # Both are city names, prefer the one with more info
        if len(new_location) > len(current_location):
            return True
    
    # If new location has digits (address/postal code) and current doesn't
    if any(char.isdigit() for char in new_location) and not any(char.isdigit() for char in current_location):
        return True
    
    return False


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
    For events that have event_url, fetch detail pages if:
    - Missing start_at
    - Missing location_text OR location_text is only a city name
    - Missing venue
    Then extract missing data and update the corresponding event_raw records.
    """
    for event in events:
        if not event.event_url:
            continue
        
        # Check if we need to fetch detail page
        needs_start_at = not event.start_at
        needs_location = not event.location_text or _is_location_only_city_name(event.location_text)
        needs_venue = not event.venue
        
        needs_enrichment = needs_start_at or needs_location or needs_venue
        
        if not needs_enrichment:
            continue
            
        counters["detail_pages_fetched"] = counters.get("detail_pages_fetched", 0) + 1

        # Fetch and extract from detail page
        detail_event = await _fetch_and_extract_detail_page(
            event.event_url,
            extraction_service=extraction_service,
            source=source,
        )

        if not detail_event:
            counters["detail_pages_no_data"] = counters.get("detail_pages_no_data", 0) + 1
            continue

        # Find the corresponding event_raw_id
        key = (event.title.strip().lower(), event.event_url.strip().lower())
        event_raw_id = event_raw_ids.get(key)

        if not event_raw_id:
            counters["detail_pages_no_event_raw_id"] = counters.get("detail_pages_no_event_raw_id", 0) + 1
            continue

        # Determine what we need to update
        update_start_at = needs_start_at and detail_event.start_at
        update_location = (
            needs_location and detail_event.location_text and
            _is_location_better_than_current(event.location_text, detail_event.location_text)
        ) or (not event.location_text and detail_event.location_text)
        update_venue = needs_venue and detail_event.venue
        
        # Also update location if detail page has a better location (even if current exists)
        if not update_location and event.location_text and detail_event.location_text:
            if _is_location_better_than_current(event.location_text, detail_event.location_text):
                update_location = True
        
        if not update_start_at and not update_location and not update_venue:
            # Detail page didn't provide the missing data
            if needs_start_at:
                counters["detail_pages_no_start_at"] = counters.get("detail_pages_no_start_at", 0) + 1
            if needs_location:
                counters["detail_pages_no_location_text"] = counters.get("detail_pages_no_location_text", 0) + 1
            if needs_venue:
                counters["detail_pages_no_venue"] = counters.get("detail_pages_no_venue", 0) + 1
            continue

        # Update event_raw with data from detail page
        raw_payload_updates = {
            "detail_page_extracted": True,
            "detail_page_url": event.event_url,
            "detail_page_extracted_event": detail_event.model_dump(mode="json"),
        }

        # Determine final values to use
        final_location_text = (
            detail_event.location_text if update_location else event.location_text
        )
        final_venue = (
            detail_event.venue if update_venue else event.venue
        )

        await update_event_raw_from_detail_page(
            event_raw_id,
            start_at=detail_event.start_at if update_start_at else None,
            end_at=detail_event.end_at if update_start_at else None,
            description=detail_event.description or event.description,
            location_text=final_location_text,
            venue=final_venue,
            image_url=detail_event.image_url or event.image_url,
            raw_payload_updates=raw_payload_updates,
        )

        counters["detail_pages_success"] = counters.get("detail_pages_success", 0) + 1
        logger.info(
            "event_enriched_from_detail_page",
            event_raw_id=event_raw_id,
            event_url=event.event_url,
            start_at=detail_event.start_at.isoformat() if detail_event.start_at else None,
            location_text=final_location_text,
            venue=final_venue,
            updated_start_at=update_start_at,
            updated_location_text=update_location,
            updated_venue=update_venue,
        )


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
            # For existing events, we might still want to enrich if start_at, location_text is missing/only city, or venue is missing
            # Fetch the existing event_raw_id
            if event.event_url and (not event.start_at or not event.location_text or _is_location_only_city_name(event.location_text) or not event.venue):
                existing = await fetchrow(
                    """
                    SELECT id FROM event_raw
                    WHERE event_source_id = $1
                      AND event_url = $2
                      AND title = $3
                      AND (start_at IS NULL OR location_text IS NULL OR location_text = '' OR venue IS NULL)
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
        "detail_pages_no_location_text": 0,
        "detail_pages_no_venue": 0,
        "detail_pages_no_data": 0,
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


