# -*- coding: utf-8 -*-
"""
NominatimService — OSM Nominatim geocoding integration for events
- Geocodes location text to lat/lng coordinates
- Reuses rate limiting patterns from OsmPlacesService
- Validates coordinates are within Europe bounds
- Blocks events from blocked countries (USA, Canada, Mexico)
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Optional, Tuple

import httpx
from app.core.logging import get_logger

logger = get_logger()

# Environment configuration
DEFAULT_USER_AGENT = "TurkishDiasporaApp/1.0 (contact: m.kul@lamarka.nl)"
DEFAULT_TIMEOUT_S = int(os.getenv("NOMINATIM_TIMEOUT_S", "5"))
DEFAULT_MIN_DELAY_SECONDS = float(os.getenv("NOMINATIM_RATE_LIMIT_DELAY", "1.0"))
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org/search"

# Europe bounds for coordinate validation
EUROPE_LAT_MIN = 35.0
EUROPE_LAT_MAX = 72.0
EUROPE_LNG_MIN = -10.0
EUROPE_LNG_MAX = 40.0

# Blocked countries (too far from Netherlands)
BLOCKED_COUNTRIES = {"united states", "usa", "america", "canada", "mexico"}

# Country name normalization: map various language spellings to English
COUNTRY_NORMALIZATION = {
    "nederland": "netherlands",
    "holland": "netherlands",
    "deutschland": "germany",
    "duitsland": "germany",
    "belgië": "belgium",
    "belgie": "belgium",
    "belgique": "belgium",
    "österreich": "austria",
    "oostenrijk": "austria",
    "schweiz": "switzerland",
    "suisse": "switzerland",
    "zwitserland": "switzerland",
    "united kingdom": "united kingdom",
    "uk": "united kingdom",
    "great britain": "united kingdom",
}

# Known city to country mappings for validation
KNOWN_CITY_COUNTRIES = {
    "london": "united kingdom",
    "vienna": "austria",
    "wien": "austria",
    "zürich": "switzerland",
    "zurich": "switzerland",
    "berlin": "germany",
    "stuttgart": "germany",
    "offenbach": "germany",
    "düsseldorf": "germany",
    "dusseldorf": "germany",
    "köln": "germany",
    "koln": "germany",
    "hamburg": "germany",
    "münchen": "germany",
    "munich": "germany",
    "rotterdam": "netherlands",
    "amsterdam": "netherlands",
    "antwerpen": "belgium",
    "antwerp": "belgium",
    "brussel": "belgium",
    "brussels": "belgium",
    "hannover": "germany",
    "heusden-zolder": "belgium",
    "heusden zolder": "belgium",
}

# Module-level rate limiting (shared across all instances)
_nominatim_last_request: float = 0
_nominatim_lock = asyncio.Lock()


def _normalize_country(country_raw: str) -> str:
    """
    Normalize country name to English, handling various formats including
    multi-language strings like "schweiz/suisse/svizzera/svizra"
    """
    if not country_raw:
        return country_raw
    
    country_lower = country_raw.lower().strip()
    
    # Try exact match first
    if country_lower in COUNTRY_NORMALIZATION:
        return COUNTRY_NORMALIZATION[country_lower]
    
    # Handle multi-language formats (e.g., "schweiz/suisse/svizzera/svizra")
    # Check if any part of the string matches a known country
    for key, normalized in COUNTRY_NORMALIZATION.items():
        if key in country_lower or country_lower in key:
            return normalized
    
    # Handle specific multi-language patterns
    if "schweiz" in country_lower or "suisse" in country_lower or "svizzera" in country_lower or "svizra" in country_lower:
        return "switzerland"
    if "belgië" in country_lower or "belgique" in country_lower or "belgien" in country_lower:
        return "belgium"
    if "österreich" in country_lower or "oostenrijk" in country_lower:
        return "austria"
    if "deutschland" in country_lower or "duitsland" in country_lower:
        return "germany"
    if "nederland" in country_lower or "holland" in country_lower:
        return "netherlands"
    if "united kingdom" in country_lower or "uk" in country_lower or "great britain" in country_lower:
        return "united kingdom"
    
    return country_lower


def _validate_city_country(location_text: str, country: str) -> Optional[str]:
    """
    Validate that a known city matches the expected country.
    Returns corrected country if mismatch detected, None if OK.
    
    Handles partial matches (e.g., "Hannover Netherlands" will match "hannover").
    """
    if not location_text or not country:
        return None
    
    location_lower = location_text.lower().strip()
    
    # First try exact match
    expected_country = KNOWN_CITY_COUNTRIES.get(location_lower)
    
    # If no exact match, check for partial matches (city name within location_text)
    if not expected_country:
        for city_name, city_country in KNOWN_CITY_COUNTRIES.items():
            # Check if city name appears in location_text (handles "Hannover Netherlands" case)
            if city_name in location_lower:
                expected_country = city_country
                break
    
    if expected_country and country != expected_country:
        logger.warning(
            "geocoding_city_country_mismatch",
            location=location_text,
            geocoded_country=country,
            expected_country=expected_country,
        )
        return expected_country
    
    return None


def _simplify_address_for_geocoding(location_text: str) -> list[str]:
    """
    Generate simplified versions of an address for fallback geocoding attempts.
    Removes venue/room names and keeps only the essential address parts.
    
    Returns a list of simplified addresses to try, from most specific to least specific.
    """
    if not location_text:
        return []
    
    # Common venue/room name patterns to remove
    venue_patterns = [
        r',\s*(Grote|Kleine|Rode|Blauwe|Groene)\s+Zaal[,\s]*',  # "Grote Zaal", "Rode Zaal"
        r',\s*[A-Z][a-z]+\s+Zaal[,\s]*',  # Any "X Zaal"
        r'\s*\|\s*[^,]+',  # Remove parts after "|" (e.g., "IKON | ANTWERPEN, IKON" -> "ANTWERPEN")
    ]
    
    simplified = location_text.strip()
    
    # Remove venue/room names
    for pattern in venue_patterns:
        simplified = re.sub(pattern, ', ', simplified, flags=re.IGNORECASE)
    
    # Clean up multiple commas/spaces
    simplified = re.sub(r',\s*,+', ', ', simplified)
    simplified = re.sub(r'\s+', ' ', simplified).strip()
    
    # Generate fallback versions
    versions = [location_text.strip()]  # Original first
    
    if simplified != location_text.strip():
        versions.append(simplified)
    
    # Try to extract street address + postcode + city
    # Pattern: "Street, Postcode City" or "Street Number, Postcode City"
    postcode_match = re.search(r'(\d{4}\s*[A-Z]{2})', simplified, re.IGNORECASE)
    if postcode_match:
        postcode = postcode_match.group(1)
        # Get everything before the postcode (street address)
        parts = simplified.split(postcode)
        if len(parts) >= 2:
            street_part = parts[0].strip().rstrip(',').strip()
            city_part = parts[1].strip()
            # Try: "Street, Postcode City"
            if street_part and city_part:
                versions.append(f"{street_part}, {postcode} {city_part}")
            # Try: "Postcode City"
            if city_part:
                versions.append(f"{postcode} {city_part}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_versions = []
    for v in versions:
        if v and v not in seen:
            seen.add(v)
            unique_versions.append(v)
    
    return unique_versions


class NominatimService:
    """
    Geocoding service using OSM's Nominatim API.
    Reuses rate limiting patterns from OsmPlacesService.
    """

    def __init__(self, timeout_s: int = DEFAULT_TIMEOUT_S):
        self.timeout_s = timeout_s
        self.user_agent = os.getenv("NOMINATIM_USER_AGENT", DEFAULT_USER_AGENT)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_s),
            headers={"User-Agent": self.user_agent}
        )

    async def __aenter__(self) -> "NominatimService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.aclose()

    async def aclose(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def _enforce_rate_limit(self) -> None:
        """
        Enforce Nominatim rate limit (1 request/second).
        Reuses pattern from OsmPlacesService._enforce_min_delay().
        """
        global _nominatim_last_request
        async with _nominatim_lock:
            elapsed = time.time() - _nominatim_last_request
            if elapsed < DEFAULT_MIN_DELAY_SECONDS:
                sleep_time = DEFAULT_MIN_DELAY_SECONDS - elapsed
                logger.debug(
                    "geocoding_rate_limit_delay",
                    elapsed_s=round(elapsed, 3),
                    sleep_time_s=round(sleep_time, 3),
                    min_delay_s=DEFAULT_MIN_DELAY_SECONDS,
                )
                await asyncio.sleep(sleep_time)
            _nominatim_last_request = time.time()

    async def _geocode_single(
        self,
        query: str,
        country_codes: Optional[list[str]] = None
    ) -> Optional[Tuple[float, float, Optional[str], str]]:
        """
        Internal method to geocode a single query string.
        Returns (lat, lng, country, display_name) or None.
        """
        await self._enforce_rate_limit()

        params = {
            "q": query.strip(),
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }

        if country_codes:
            params["countrycodes"] = ",".join(country_codes)

        try:
            logger.debug(
                "geocoding_request_start",
                query=query,
                country_codes=country_codes,
            )
            response = await self._client.get(
                NOMINATIM_BASE_URL,
                params=params,
            )
            # Log response headers (especially useful for rate limiting - Retry-After header)
            response_headers = dict(response.headers)
            logger.debug(
                "geocoding_response_received",
                query=query,
                status_code=response.status_code,
                retry_after=response_headers.get("Retry-After"),
                x_rate_limit_limit=response_headers.get("X-Rate-Limit-Limit"),
                x_rate_limit_remaining=response_headers.get("X-Rate-Limit-Remaining"),
            )
            response.raise_for_status()
            data = response.json()

            if not data or len(data) == 0:
                logger.debug(
                    "geocoding_empty_response",
                    query=query,
                    country_codes=country_codes,
                )
                return None

            result = data[0]
            lat = float(result.get("lat", 0))
            lng = float(result.get("lon", 0))
            display_name = result.get("display_name", "")

            # Validate coordinates are in Europe
            if not (EUROPE_LAT_MIN <= lat <= EUROPE_LAT_MAX and
                    EUROPE_LNG_MIN <= lng <= EUROPE_LNG_MAX):
                logger.debug(
                    "geocoding_outside_europe_bounds",
                    query=query,
                    lat=lat,
                    lng=lng,
                    country_codes=country_codes,
                )
                return None

            # Extract country from address details and normalize to English
            address = result.get("address", {})
            country_raw = address.get("country", "").lower()
            
            # Normalize country name to English (handles multi-language formats)
            country = _normalize_country(country_raw)
            
            # Validate known cities against expected country
            corrected_country = _validate_city_country(query, country)
            if corrected_country:
                country = corrected_country
            
            # Block if in blocked list
            if country and any(blocked in country for blocked in BLOCKED_COUNTRIES):
                logger.debug(
                    "geocoding_blocked_country",
                    query=query,
                    country=country,
                )
                return None

            return (lat, lng, country or None, display_name)

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response else None
            response_text = None
            retry_after = None
            
            # Try to extract error details from response
            if e.response:
                try:
                    response_text = e.response.text[:500]  # Limit length
                    # Check for Retry-After header (common in rate limiting)
                    retry_after = e.response.headers.get("Retry-After")
                except Exception:
                    pass
            
            logger.warning(
                "geocoding_http_error",
                query=query,
                country_codes=country_codes,
                status_code=status_code,
                retry_after=retry_after,
                response_preview=response_text,
                error=str(e),
            )
            return None
        except httpx.TimeoutException as e:
            logger.warning(
                "geocoding_timeout",
                query=query,
                country_codes=country_codes,
                timeout_s=self.timeout_s,
                error=str(e),
            )
            return None
        except httpx.NetworkError as e:
            logger.warning(
                "geocoding_network_error",
                query=query,
                country_codes=country_codes,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.warning(
                "geocoding_exception",
                query=query,
                country_codes=country_codes,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return None

    async def geocode(
        self,
        location_text: str,
        country_codes: Optional[list[str]] = None
    ) -> Optional[Tuple[float, float, Optional[str]]]:
        """
        Geocode location text to (lat, lng, country).
        Tries multiple simplified versions if the original query fails.

        Args:
            location_text: Address or location name
            country_codes: Preferred countries (e.g., ["nl", "be", "de"])

        Returns:
            (lat, lng, country) tuple or None if geocoding fails or location is blocked
            country is lowercase English (e.g., "netherlands", "belgium") or None
        """
        if not location_text or not location_text.strip():
            return None

        # Generate simplified versions to try
        versions_to_try = _simplify_address_for_geocoding(location_text)
        
        for attempt, query in enumerate(versions_to_try):
            result = await self._geocode_single(query, country_codes)
            
            if result:
                lat, lng, country, display_name = result
                
                # Log success (with attempt info if not first try)
                if attempt > 0:
                    logger.info(
                        "geocoding_success_with_fallback",
                        original_location=location_text,
                        successful_query=query,
                        attempt=attempt + 1,
                        lat=lat,
                        lng=lng,
                        country=country,
                        display_name=display_name
                    )
                else:
                    logger.debug(
                        "geocoding_success",
                        location=location_text,
                        lat=lat,
                        lng=lng,
                        country=country
                    )
                
                return (lat, lng, country)
            else:
                # Log why this attempt failed (only for first attempt to avoid spam)
                if attempt == 0:
                    logger.warning(
                        "geocoding_no_results",
                        location=location_text,
                        query=query,
                        will_try_fallback=len(versions_to_try) > 1
                    )
        
        # All attempts failed
        logger.warning(
            "geocoding_all_attempts_failed",
            location=location_text,
            attempts=len(versions_to_try),
            queries_tried=versions_to_try
        )
        return None
