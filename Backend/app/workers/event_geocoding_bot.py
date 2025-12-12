from __future__ import annotations

import argparse
import asyncio
from typing import Dict, Optional
from uuid import UUID

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.db_service import init_db_pool, fetch, execute
from services.nominatim_service import NominatimService
from services.worker_runs_service import (
    finish_worker_run,
    mark_worker_run_running,
    start_worker_run,
    update_worker_run_progress,
)

configure_logging(service_name="worker")
logger = get_logger().bind(worker="event_geocoding_bot")


def _detect_city_from_location(location_text: str) -> Optional[str]:
    """
    Detect city_key from location_text using text matching.
    Returns city_key (e.g., 'rotterdam', 'amsterdam', 'antwerpen') or None.
    """
    if not location_text:
        return None
    
    location_lower = location_text.lower()
    
    # Map common city names to city_keys
    city_patterns = {
        'rotterdam': ['rotterdam'],
        'amsterdam': ['amsterdam'],
        'den_haag': ['den haag', 'the hague', "'s-gravenhage", 's-gravenhage'],
        'utrecht': ['utrecht'],
        'eindhoven': ['eindhoven'],
        'groningen': ['groningen'],
        'tilburg': ['tilburg'],
        'almere': ['almere'],
        'breda': ['breda'],
        'nijmegen': ['nijmegen'],
        'enschede': ['enschede'],
        'haarlem': ['haarlem'],
        'arnhem': ['arnhem'],
        'zaanstad': ['zaanstad'],
        'amersfoort': ['amersfoort'],
        'apeldoorn': ['apeldoorn'],
        'antwerpen': ['antwerpen', 'antwerp'],
        'brussel': ['brussel', 'brussels', 'bruxelles'],
        'gent': ['gent', 'ghent'],
    }
    
    for city_key, patterns in city_patterns.items():
        for pattern in patterns:
            if pattern in location_lower:
                return city_key
    
    return None


def _should_block_location(location_text: str) -> bool:
    """
    Check if location should be blocked due to invalid patterns.
    Blocks locations like "Washington, Netherlands", "Berlin, Netherlands", etc.
    Also blocks standalone foreign cities (German, UK, Austrian, Swiss, US).
    Matches SQL function is_location_blocked() logic.
    """
    if not location_text:
        return False
    
    location_lower = location_text.lower().strip()
    
    # Block US cities with "Netherlands" suffix
    us_cities = ['washington', 'houston', 'lodi', 'new york', 'los angeles', 'chicago']
    for city in us_cities:
        if city in location_lower and 'netherlands' in location_lower:
            return True
    
    # Block German cities with "Netherlands" suffix
    german_cities = ['berlin', 'münchen', 'munchen', 'köln', 'koln', 'hamburg', 'frankfurt']
    for city in german_cities:
        if city in location_lower and 'netherlands' in location_lower:
            return True
    
    # Block standalone US cities without context (likely errors)
    standalone_us = ['washington', 'houston', 'lodi']
    for city in standalone_us:
        if location_lower == city:
            return True
        if location_lower.startswith(city) and ', netherlands' in location_lower:
            return True
    
    # Block standalone German cities (without Netherlands suffix, but still foreign)
    standalone_german = ['berlin', 'münchen', 'munchen', 'köln', 'koln', 'hamburg', 
                         'frankfurt', 'stuttgart', 'düsseldorf', 'dusseldorf', 'offenbach', 
                         'mannheim', 'hannover', 'bochum', 'nürnberg', 'nurnberg']
    if location_lower in standalone_german:
        return True
    
    # Block UK cities
    if location_lower == 'london':
        return True
    
    # Block Austrian cities
    if location_lower in ('vienna', 'wien'):
        return True
    
    # Block Swiss cities
    if location_lower in ('zürich', 'zurich'):
        return True
    
    return False


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EventGeocodingBot — Geocode event locations to lat/lng.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of events to geocode.")
    parser.add_argument(
        "--worker-run-id",
        type=_parse_worker_run_id,
        default=None,
        help="Existing worker_runs UUID (optional).",
    )
    return parser.parse_args()


async def run_geocoding(
    *,
    limit: int,
    worker_run_id: Optional[UUID],
) -> int:
    await init_db_pool()
    run_id = worker_run_id or await start_worker_run(bot="event_geocoding", city=None, category=None)
    await mark_worker_run_running(run_id)
    counters: Dict[str, int] = {
        "total": 0,
        "geocoded": 0,
        "errors": 0,
        "blocked": 0,
        "no_location": 0,
    }
    progress = 5
    await update_worker_run_progress(run_id, progress)

    try:
        # Fetch events without coordinates from events_candidate
        events = await fetch(
            """
            SELECT ec.id, ec.location_text, er.title, es.city_key
            FROM events_candidate ec
            JOIN event_raw er ON er.id = ec.event_raw_id
            LEFT JOIN event_sources es ON es.id = ec.event_source_id
            WHERE ec.lat IS NULL AND ec.lng IS NULL
              AND ec.location_text IS NOT NULL
              AND ec.location_text != ''
            ORDER BY ec.created_at ASC
            LIMIT $1
            """,
            max(0, int(limit)),
        )
        counters["total"] = len(events) if events else 0

        if not events or len(events) == 0:
            await finish_worker_run(run_id, "finished", 100, counters, None)
            logger.info("event_geocoding_no_events_to_process")
            return 0

        async with NominatimService() as geocoder:
            for idx, event_row in enumerate(events, start=1):
                percent = min(99, max(5, int(idx * 100 / max(len(events), 1))))
                await update_worker_run_progress(run_id, percent)

                event_id = int(event_row["id"])
                location_text = event_row.get("location_text")
                title = event_row.get("title")
                source_city_key = event_row.get("city_key")

                if not location_text:
                    counters["no_location"] += 1
                    continue

                try:
                    # FIRST: Check if location should be blocked
                    if _should_block_location(location_text):
                        logger.info(
                            "event_geocoding_blocked_invalid_location",
                            event_id=event_id,
                            location=location_text,
                            title=title,
                        )
                        counters["blocked"] += 1
                        continue

                    # SECOND: Try to detect city from location_text
                    detected_city = _detect_city_from_location(location_text)
                    city_key = detected_city or source_city_key
                    
                    # Geocode with country preference based on detected/source city_key
                    country_codes = ["nl", "be", "de"]
                    if city_key:
                        city_lower = city_key.lower()
                        if "amsterdam" in city_lower or "rotterdam" in city_lower or "den_haag" in city_lower:
                            country_codes = ["nl"]
                        elif "brussel" in city_lower or "antwerpen" in city_lower or "gent" in city_lower:
                            country_codes = ["be"]
                        elif "berlin" in city_lower or "hamburg" in city_lower:
                            country_codes = ["de"]

                    coords = await geocoder.geocode(
                        location_text,
                        country_codes=country_codes,
                    )

                    if coords:
                        lat, lng, country = coords
                        
                        # Block if country is not Netherlands, Belgium, or Germany
                        if country and country not in ["netherlands", "belgium", "germany"]:
                            logger.info(
                                "event_geocoding_blocked_wrong_country",
                                event_id=event_id,
                                location=location_text,
                                country=country,
                            )
                            counters["blocked"] += 1
                            continue
                        
                        await execute(
                            """
                            UPDATE events_candidate
                            SET lat = $1, lng = $2, country = $4
                            WHERE id = $3
                            """,
                            lat,
                            lng,
                            event_id,
                            country,
                        )
                        counters["geocoded"] += 1
                        logger.info(
                            "event_geocoding_success",
                            event_id=event_id,
                            location=location_text,
                            detected_city=detected_city,
                            source_city=source_city_key,
                            lat=lat,
                            lng=lng,
                            country=country,
                        )
                    else:
                        counters["blocked"] += 1
                        logger.info(
                            "event_geocoding_blocked",
                            event_id=event_id,
                            location=location_text,
                        )
                except Exception as exc:
                    counters["errors"] += 1
                    logger.warning(
                        "event_geocoding_error",
                        event_id=event_id,
                        location=location_text,
                        error=str(exc),
                    )

        await finish_worker_run(run_id, "finished", 100, counters, None)
        logger.info(
            "event_geocoding_bot_finished",
            total=counters["total"],
            geocoded=counters["geocoded"],
            blocked=counters["blocked"],
            errors=counters["errors"],
        )
        return 0
    except Exception as exc:
        logger.error("event_geocoding_bot_failed", error=str(exc))
        await finish_worker_run(run_id, "failed", progress, counters or None, str(exc))
        return 1


async def main_async() -> int:
    args = parse_args()
    with with_run_id():
        return await run_geocoding(
            limit=args.limit,
            worker_run_id=args.worker_run_id,
        )


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()


