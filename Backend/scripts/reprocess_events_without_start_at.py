#!/usr/bin/env python3
"""
Script om bestaande events zonder start_at te reprocessen met detail page extraction.

Gebruik:
  cd Backend
  source .venv/bin/activate
  python scripts/reprocess_events_without_start_at.py --limit 10
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Path setup
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from urllib.parse import urljoin

from services.db_service import init_db_pool, fetch, fetchrow
from services.event_sources_service import get_event_source
from services.event_raw_service import update_event_raw_from_detail_page
from services.event_extraction_service import EventExtractionService
from app.workers.event_ai_extractor_bot import _fetch_and_extract_detail_page

configure_logging(service_name="script")
logger = get_logger()


async def fetch_events_without_start_at(
    limit: int, 
    include_midnight_times: bool = False,
    source_key: Optional[str] = None,
    event_ids: Optional[List[int]] = None
) -> List[Dict]:
    """
    Fetch events that have event_url but no start_at, or have midnight times (00:00) that might be incorrect.
    
    Args:
        limit: Maximum number of events to return
        include_midnight_times: If True, also include events with midnight times that might need reprocessing
        source_key: Optional source key filter (e.g., 'sahmeran_events')
        event_ids: Optional list of specific event_raw IDs to process
    """
    params: List[Any] = []
    param_num = 1
    
    # Build event_ids filter (highest priority)
    if event_ids:
        event_ids_condition = f"AND er.id = ANY(${param_num}::int[])"
        params.append(event_ids)
        param_num += 1
    else:
        event_ids_condition = ""
    
    # Build time condition
    if include_midnight_times and not event_ids:
        time_condition = """
            AND (
                er.start_at IS NULL
                OR (
                    EXTRACT(HOUR FROM er.start_at AT TIME ZONE 'Europe/Amsterdam') = 0
                    AND EXTRACT(MINUTE FROM er.start_at AT TIME ZONE 'Europe/Amsterdam') = 0
                )
            )
        """
    elif not event_ids:
        time_condition = "AND er.start_at IS NULL"
    else:
        time_condition = ""  # Skip time filter when using specific event_ids
    
    # Build source filter
    if source_key:
        source_condition = f"AND er.event_source_id = (SELECT id FROM event_sources WHERE key = ${param_num})"
        params.append(source_key)
        param_num += 1
    else:
        source_condition = ""
    
    if not event_ids:
        params.append(limit)
        limit_clause = f"LIMIT ${param_num}"
    else:
        limit_clause = ""
    
    # Build detail_page_extracted filter (skip if using specific event_ids)
    if event_ids:
        detail_extracted_condition = ""  # Allow reprocessing even if already processed
    else:
        detail_extracted_condition = "COALESCE(er.raw_payload->>'detail_page_extracted', 'false') != 'true'"
    
    # Build WHERE clause
    where_parts = [
        "er.event_url IS NOT NULL",
        "er.event_url != ''",
        "er.event_url != 'null'",
    ]
    if detail_extracted_condition:
        where_parts.append(detail_extracted_condition)
    if time_condition:
        where_parts.append(time_condition.strip().replace("AND ", ""))
    if source_condition:
        where_parts.append(source_condition.strip().replace("AND ", ""))
    if event_ids_condition:
        where_parts.append(event_ids_condition.strip().replace("AND ", ""))
    
    where_clause = " AND ".join(where_parts)
    
    query = f"""
        SELECT 
            er.id,
            er.event_source_id,
            er.title,
            er.event_url,
            er.start_at,
            er.description
        FROM event_raw er
        WHERE {where_clause}
        ORDER BY er.created_at DESC
        {limit_clause}
    """
    
    rows = await fetch(query, *params)
    return [dict(row) for row in rows or []]


async def count_events_without_start_at() -> Dict[str, int]:
    """Helper to count events by status."""
    rows = await fetch(
        """
        SELECT 
            COUNT(*) FILTER (WHERE event_url IS NOT NULL AND event_url != '' AND start_at IS NULL) as without_start_at,
            COUNT(*) FILTER (WHERE event_url IS NOT NULL AND event_url != '' AND start_at IS NULL AND COALESCE(raw_payload->>'detail_page_extracted', 'false') != 'true') as needs_reprocess,
            COUNT(*) FILTER (WHERE event_url IS NOT NULL AND event_url != '' AND start_at IS NULL AND raw_payload->>'detail_page_extracted' = 'true') as already_processed,
            COUNT(*) as total
        FROM event_raw
        """
    )
    return dict(rows[0]) if rows else {}


async def check_events_in_candidate() -> Dict[str, int]:
    """Check events_candidate for issues."""
    rows = await fetch(
        """
        SELECT 
            COUNT(*) as total_candidate,
            COUNT(*) FILTER (WHERE start_time_utc < NOW() - INTERVAL '1 year') as very_old,
            COUNT(*) FILTER (WHERE start_time_utc > NOW() + INTERVAL '2 years') as very_future
        FROM events_candidate
        """
    )
    return dict(rows[0]) if rows else {}


async def reprocess_event(event: Dict, extraction_service: EventExtractionService) -> bool:
    """Reprocess a single event by fetching its detail page."""
    event_raw_id = event["id"]
    event_url = event["event_url"]
    event_source_id = event["event_source_id"]

    # Get event source
    source = await get_event_source(event_source_id)
    if not source:
        print(f"❌ Event {event_raw_id}: source {event_source_id} not found")
        return False

    # Normalize URL: convert relative to absolute if needed
    if event_url and not event_url.startswith(("http://", "https://")):
        base_url = source.base_url or source.list_url or ""
        if base_url:
            # Remove trailing slash from base and ensure event_url starts with /
            base_url = base_url.rstrip("/")
            if not event_url.startswith("/"):
                event_url = "/" + event_url
            event_url = urljoin(base_url, event_url)
        else:
            print(f"⚠️  Event {event_raw_id}: Cannot absolutize URL, missing base_url")
            return False

    print(f"🔄 Processing event {event_raw_id}: {event['title'][:50]}...")
    print(f"   URL: {event_url}")

    # Fetch and extract from detail page
    detail_event = await _fetch_and_extract_detail_page(
        event_url,
        extraction_service=extraction_service,
        source=source,
        event_raw_id=event_raw_id,
    )

    if not detail_event:
        print(f"   ⚠️  Could not extract event data from detail page")
        return False

    if not detail_event.start_at:
        print(f"   ⚠️  Detail page extraction did not find start_at")
        return False

    # Check if the extracted time is midnight (00:00) - this might indicate missing time info
    extracted_time_local = detail_event.start_at
    if hasattr(extracted_time_local, 'astimezone'):
        import zoneinfo
        amsterdam_tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
        local_time = extracted_time_local.astimezone(amsterdam_tz)
        if local_time.hour == 0 and local_time.minute == 0:
            print(f"   ⚠️  Warning: Extracted time is midnight (00:00), might indicate missing time on detail page")

    # Update event_raw with data from detail page
    raw_payload_updates = {
        "detail_page_extracted": True,
        "detail_page_url": event_url,
        "detail_page_extracted_event": detail_event.model_dump(mode="json"),
        "reprocessed_via": "reprocess_events_without_start_at",
    }

    await update_event_raw_from_detail_page(
        event_raw_id,
        start_at=detail_event.start_at,
        end_at=detail_event.end_at,
        description=detail_event.description or event.get("description"),
        location_text=detail_event.location_text,
        venue=detail_event.venue,
        image_url=detail_event.image_url,
        raw_payload_updates=raw_payload_updates,
    )

    print(f"   ✅ Updated with start_at: {detail_event.start_at.isoformat()}")
    return True


async def main():
    parser = argparse.ArgumentParser(
        description="Reprocess events without start_at by fetching detail pages"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of events to process (default: 10)",
    )
    parser.add_argument(
        "--include-midnight",
        action="store_true",
        help="Also reprocess events with midnight (00:00) times that might be missing actual event times",
    )
    parser.add_argument(
        "--source-key",
        type=str,
        default=None,
        help="Optional source key filter (e.g., 'sahmeran_events')",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Optional OpenAI model override",
    )
    parser.add_argument(
        "--event-ids",
        type=str,
        default=None,
        help="Comma-separated list of specific event_raw IDs to reprocess (e.g., '6,9,25')",
    )
    args = parser.parse_args()
    
    # Parse event IDs if provided
    event_ids = None
    if args.event_ids:
        try:
            event_ids = [int(id_str.strip()) for id_str in args.event_ids.split(",")]
        except ValueError as e:
            print(f"❌ Error parsing --event-ids: {e}")
            print("   Expected format: --event-ids '6,9,25'")
            return

    await init_db_pool()

    # First, show statistics
    print(f"📊 Checking event statistics...")
    stats = await count_events_without_start_at()
    print(f"   [event_raw] Total events: {stats.get('total', 0)}")
    print(f"   [event_raw] Events without start_at: {stats.get('without_start_at', 0)}")
    print(f"   [event_raw] Already processed (detail_page_extracted): {stats.get('already_processed', 0)}")
    print(f"   [event_raw] Need reprocessing: {stats.get('needs_reprocess', 0)}")
    
    candidate_stats = await check_events_in_candidate()
    print(f"   [events_candidate] Total: {candidate_stats.get('total_candidate', 0)}")
    print(f"   [events_candidate] Very old (year ago): {candidate_stats.get('very_old', 0)}")
    print(f"   [events_candidate] Very future (2+ years): {candidate_stats.get('very_future', 0)}\n")

    print(f"🔍 Finding events to reprocess (limit={args.limit}, include_midnight={args.include_midnight}, source_key={args.source_key}, event_ids={event_ids})...")
    events = await fetch_events_without_start_at(
        args.limit, 
        include_midnight_times=args.include_midnight,
        source_key=args.source_key,
        event_ids=event_ids
    )
    print(f"Found {len(events)} event(s) to process\n")

    if not events:
        print("No events to process. Exiting.")
        print("\n💡 Tip: Check if there are events without start_at using this SQL:")
        print("   SELECT id, title, event_url, start_at FROM event_raw")
        print("   WHERE event_url IS NOT NULL AND event_url != '' AND start_at IS NULL")
        print("   ORDER BY created_at DESC LIMIT 10;")
        return

    extraction_service = EventExtractionService(model=args.model)
    success_count = 0
    fail_count = 0

    for event in events:
        try:
            success = await reprocess_event(event, extraction_service)
            if success:
                success_count += 1
            else:
                fail_count += 1
            print()  # Empty line between events
        except Exception as e:
            print(f"   ❌ Error processing event {event['id']}: {e}\n")
            fail_count += 1

    print(f"\n📊 Summary:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    print(f"   Total: {len(events)}")


if __name__ == "__main__":
    asyncio.run(main())
