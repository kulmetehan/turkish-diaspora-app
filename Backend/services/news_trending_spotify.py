"""
Spotify Viral 50 tracks service.

This service uses Spotify playlist scraper as the primary data source.
The scraper runs daily via GitHub Actions workflow to keep tracks up-to-date.
Tracks are stored in feed_curated_content table for persistence across processes.
"""

from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from app.core.logging import get_logger
from services.db_service import fetchrow, init_db_pool

logger = get_logger().bind(module="news_trending_spotify")

# Increase cache TTL to 30 minutes (1800 seconds) to ensure tracks persist longer
# This helps when worker and API run in separate processes
_DEFAULT_CACHE_TTL_SECONDS = int(os.getenv("SPOTIFY_CACHE_TTL_SECONDS", "1800"))
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
    Fetch Spotify Viral 50 tracks from database (preferred) or scraper (fallback).
    
    Args:
        limit: Maximum number of tracks to return
        country: Country code (e.g., "nl", "tr")
        
    Returns:
        SpotifyResult with tracks and optional unavailable_reason
    """
    country_key = (country or "nl").lower()
    bucket = _cache.setdefault(country_key, {"expires_at": 0.0, "result": None})
    now = time.time()
    
    # Check in-memory cache first (30 minutes TTL by default)
    if bucket.get("result") and now < float(bucket.get("expires_at", 0)):
        cached_result: SpotifyResult = bucket["result"]
        logger.info("spotify_cache_hit", country=country_key, tracks_count=len(cached_result.tracks), cache_age_seconds=int(now - bucket.get("cached_at", now)))
        return SpotifyResult(
            tracks=cached_result.tracks[:limit],
            unavailable_reason=cached_result.unavailable_reason,
        )

    # Try to fetch from database first (preferred method)
    try:
        await init_db_pool()
        row = await fetchrow(
            """
            SELECT ranked_items, metadata
            FROM feed_curated_content
            WHERE content_type = 'music'
              AND metadata->>'country' = $1
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
            """,
            country_key,
        )
        
        if row:
            ranked_items_raw = row.get("ranked_items")
            metadata_raw = row.get("metadata")
            
            # Parse JSONB
            try:
                if isinstance(ranked_items_raw, str):
                    tracks_data = json.loads(ranked_items_raw)
                else:
                    tracks_data = ranked_items_raw or []
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("spotify_db_parse_error", country=country_key, error=str(e))
                tracks_data = []
            
            try:
                if isinstance(metadata_raw, str):
                    metadata = json.loads(metadata_raw)
                else:
                    metadata = metadata_raw or {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}
            
            # Convert to SpotifyTrack objects
            tracks: List[SpotifyTrack] = []
            for track_data in tracks_data[:limit]:
                try:
                    published_at = None
                    if track_data.get("published_at"):
                        try:
                            published_at = datetime.fromisoformat(track_data["published_at"].replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            pass
                    
                    tracks.append(SpotifyTrack(
                        title=track_data.get("title", ""),
                        url=track_data.get("url", ""),
                        artist=track_data.get("artist", ""),
                        published_at=published_at,
                        image_url=track_data.get("image_url"),
                    ))
                except Exception as e:
                    logger.warning("spotify_track_parse_error", country=country_key, error=str(e))
                    continue
            
            unavailable_reason = metadata.get("unavailable_reason")
            result = SpotifyResult(
                tracks=tracks,
                unavailable_reason=unavailable_reason,
            )
            
            # Cache in memory
            bucket["result"] = result
            bucket["cached_at"] = now
            bucket["expires_at"] = now + _DEFAULT_CACHE_TTL_SECONDS
            
            logger.info("spotify_db_hit", country=country_key, tracks_count=len(tracks))
            return result
        else:
            logger.info("spotify_db_miss", country=country_key, reason="no_valid_cache")
    except Exception as db_exc:
        logger.warning("spotify_db_fetch_error", country=country_key, error=str(db_exc), error_type=type(db_exc).__name__)
        # Fall through to scraper

    # Fallback to scraper if database doesn't have valid data
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
    
    # Cache the result in memory
    bucket["result"] = result
    bucket["cached_at"] = now  # Track when we cached this
    if result.unavailable_reason:
        # Cache unavailable results for shorter time (30 seconds)
        bucket["expires_at"] = now + 30
        logger.warning("spotify_cached_unavailable", country=country_key, reason=result.unavailable_reason)
    else:
        # Cache successful results for 30 minutes (configurable via env var)
        bucket["expires_at"] = now + _DEFAULT_CACHE_TTL_SECONDS
        logger.info("spotify_cached_success", country=country_key, tracks_count=len(result.tracks), ttl_seconds=_DEFAULT_CACHE_TTL_SECONDS)

    return SpotifyResult(
        tracks=result.tracks[:limit],
        unavailable_reason=result.unavailable_reason,
    )

