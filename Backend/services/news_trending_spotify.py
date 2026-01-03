"""
Spotify Viral 50 tracks service.

This service uses Spotify playlist scraper as the primary data source.
The scraper runs daily via GitHub Actions workflow to keep tracks up-to-date.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from app.core.logging import get_logger

logger = get_logger().bind(module="news_trending_spotify")

_DEFAULT_CACHE_TTL_SECONDS = int(os.getenv("SPOTIFY_CACHE_TTL_SECONDS", "180"))
_cache: dict[str, dict[str, object]] = {}


@dataclass(frozen=True)
class SpotifyTrack:
    title: str
    url: str
    artist: str
    published_at: datetime | None
    image_url: Optional[str] = None  # Album/track thumbnail image URL


@dataclass
class SpotifyResult:
    """Result from Spotify tracks fetch, including unavailability reason if applicable."""
    tracks: List[SpotifyTrack]
    unavailable_reason: Optional[str] = None


async def fetch_spotify_tracks(limit: int = 20, country: str = "nl") -> SpotifyResult:
    """
    Fetch Spotify Viral 50 tracks using scraper.
    
    Args:
        limit: Maximum number of tracks to return
        country: Country code (e.g., "nl", "tr")
        
    Returns:
        SpotifyResult with tracks and optional unavailable_reason
    """
    country_key = (country or "nl").lower()
    bucket = _cache.setdefault(country_key, {"expires_at": 0.0, "result": None})
    now = time.time()
    
    # Check cache (3 minutes TTL)
    if bucket.get("result") and now < float(bucket.get("expires_at", 0)):
        cached_result: SpotifyResult = bucket["result"]
        logger.debug("spotify_cache_hit", country=country_key, tracks_count=len(cached_result.tracks))
        return SpotifyResult(
            tracks=cached_result.tracks[:limit],
            unavailable_reason=cached_result.unavailable_reason,
        )

    # Use scraper as the only source
    try:
        from services.news_trending_spotify_scraper import fetch_spotify_tracks_scraper
        
        logger.info("spotify_fetching_via_scraper", country=country_key, limit=limit)
        result = await fetch_spotify_tracks_scraper(limit=limit, country=country_key)
        
        if result.tracks:
            logger.info("spotify_scraper_success", country=country_key, tracks_count=len(result.tracks))
        else:
            logger.warning("spotify_scraper_no_tracks", country=country_key, unavailable_reason=result.unavailable_reason)
        
    except Exception as exc:
        logger.error("spotify_scraper_error", country=country_key, error=str(exc), error_type=type(exc).__name__)
        result = SpotifyResult(
            tracks=[],
            unavailable_reason="spotify_unavailable_scraper_error",
        )
    
    # Cache the result
    bucket["result"] = result
    if result.unavailable_reason:
        # Cache unavailable results for shorter time (30 seconds)
        bucket["expires_at"] = now + 30
    else:
        # Cache successful results for 3 minutes
        bucket["expires_at"] = now + _DEFAULT_CACHE_TTL_SECONDS

    return SpotifyResult(
        tracks=result.tracks[:limit],
        unavailable_reason=result.unavailable_reason,
    )

