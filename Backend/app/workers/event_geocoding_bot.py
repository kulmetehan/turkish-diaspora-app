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


def _normalize_location_text(location_text: str) -> str:
    """
    Normalize location_text by removing incorrect country suffixes.

    Examples:
    - "Hannover Netherlands" -> "Hannover"
    - "Stuttgart Netherlands" -> "Stuttgart"
    - "Offenbach Netherlands" -> "Offenbach"
    """
    if not location_text:
        return location_text

    location_lower = location_text.lower().strip()

    # List of known foreign cities that should NOT have "Netherlands" suffix
    foreign_cities = [
        "hannover", "stuttgart", "offenbach", "berlin", "düsseldorf", "dusseldorf",
        "köln", "koln", "hamburg", "münchen", "munich", "london", "vienna", "wien",
        "zürich", "zurich", "antwerpen", "antwerp", "brussel", "brussels",
        "heusden-zolder", "heusden zolder"
    ]

    # Check if location_text contains a foreign city name
    for city in foreign_cities:
        if city in location_lower:
            # Remove common incorrect suffixes
            normalized = location_text
            for suffix in [" netherlands", ", netherlands"]:
                if normalized.lower().endswith(suffix.lower()):
                    normalized = normalized[:-len(suffix)].strip()
            return normalized

    return location_text


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
                    # Normalize location_text to remove incorrect country suffixes
                    normalized_location = _normalize_location_text(location_text)
                    
                    # Try to detect city from location_text (for logging purposes)
                    detected_city = _detect_city_from_location(location_text)
                    city_key = detected_city or source_city_key
                    
                    # CRITICAL FIX: Geocode WITHOUT country_codes first to get accurate results
                    # Using country_codes forces Nominatim to only search within those countries,
                    # which can lead to wrong matches (e.g., "Vienna" → Netherlands, "London" → Germany)
                    # By searching worldwide first, we get the correct country, then filter by country
                    coords = await geocoder.geocode(
                        normalized_location,  # Use normalized location
                        country_codes=None,  # Search worldwide first - this ensures accurate country detection
                    )

                    if coords:
                        lat, lng, country = coords
                        
                        # Always save geocoding results, even for foreign countries
                        # The events_public view will filter by country = 'netherlands'
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
                        # If geocoding fails, log but don't block
                        # The event will remain without coordinates and won't appear in events_public
                        counters["errors"] += 1
                        logger.warning(
                            "event_geocoding_failed",
                            event_id=event_id,
                            location=location_text,
                            normalized_location=normalized_location,
                            reason="Nominatim returned None (no results, out of bounds, or blocked)",
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


