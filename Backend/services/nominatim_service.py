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

# Module-level rate limiting (shared across all instances)
_nominatim_last_request: float = 0
_nominatim_lock = asyncio.Lock()


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
                await asyncio.sleep(sleep_time)
            _nominatim_last_request = time.time()

    async def geocode(
        self,
        location_text: str,
        country_codes: Optional[list[str]] = None
    ) -> Optional[Tuple[float, float]]:
        """
        Geocode location text to (lat, lng).

        Args:
            location_text: Address or location name
            country_codes: Preferred countries (e.g., ["nl", "be", "de"])

        Returns:
            (lat, lng) tuple or None if geocoding fails or location is blocked
        """
        if not location_text or not location_text.strip():
            return None

        await self._enforce_rate_limit()

        params = {
            "q": location_text.strip(),
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }

        if country_codes:
            params["countrycodes"] = ",".join(country_codes)

        try:
            response = await self._client.get(
                NOMINATIM_BASE_URL,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            if not data or len(data) == 0:
                logger.debug("geocoding_no_results", location=location_text)
                return None

            result = data[0]
            lat = float(result.get("lat", 0))
            lng = float(result.get("lon", 0))

            # Validate coordinates are in Europe
            if not (EUROPE_LAT_MIN <= lat <= EUROPE_LAT_MAX and
                    EUROPE_LNG_MIN <= lng <= EUROPE_LNG_MAX):
                logger.warning(
                    "geocoding_out_of_bounds",
                    location=location_text,
                    lat=lat,
                    lng=lng
                )
                return None

            # Extract country from address details and block if in blocked list
            address = result.get("address", {})
            country = address.get("country", "").lower()
            if country and any(blocked in country for blocked in BLOCKED_COUNTRIES):
                logger.info(
                    "geocoding_blocked_country",
                    location=location_text,
                    country=country
                )
                return None

            logger.debug(
                "geocoding_success",
                location=location_text,
                lat=lat,
                lng=lng,
                country=country
            )
            return (lat, lng)

        except httpx.HTTPStatusError as e:
            logger.warning(
                "geocoding_http_error",
                location=location_text,
                status_code=e.response.status_code,
                error=str(e)
            )
            return None
        except Exception as e:
            logger.warning("geocoding_failed", location=location_text, error=str(e))
            return None

