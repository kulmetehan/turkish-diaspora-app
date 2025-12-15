"""
X (Twitter) trending topics service.

This service uses trends24.in scraper as the primary (and only) data source.
The X API integration has been removed as it requires paid tier access (Basic/Pro/Enterprise).

The scraper runs hourly via GitHub Actions workflow to keep trending topics up-to-date.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from app.core.logging import get_logger

logger = get_logger().bind(module="news_trending_x")

_DEFAULT_CACHE_TTL_SECONDS = int(os.getenv("X_TRENDING_CACHE_TTL_SECONDS", "180"))
_cache: dict[str, dict[str, object]] = {}


@dataclass(frozen=True)
class TrendingTopic:
    title: str
    url: str
    description: Optional[str]
    published_at: datetime | None


@dataclass
class TrendingResult:
    """Result from trending topics fetch, including unavailability reason if applicable."""
    topics: List[TrendingTopic]
    unavailable_reason: Optional[str] = None


async def fetch_trending_topics(limit: int = 20, country: str = "nl") -> TrendingResult:
    """
    Fetch trending topics using trends24.in scraper (only source).
    
    The X API integration has been removed. This function now exclusively uses
    the trends24.in scraper which works without authentication.
    
    Args:
        limit: Maximum number of topics to return
        country: Country code (e.g., "nl", "tr")
        
    Returns:
        TrendingResult with topics and optional unavailable_reason
    """
    country_key = (country or "nl").lower()
    bucket = _cache.setdefault(country_key, {"expires_at": 0.0, "result": None})
    now = time.time()
    
    # Check cache (3 minutes TTL)
    if bucket.get("result") and now < float(bucket.get("expires_at", 0)):
        cached_result: TrendingResult = bucket["result"]
        logger.debug("x_trending_cache_hit", country=country_key, topics_count=len(cached_result.topics))
        return TrendingResult(
            topics=cached_result.topics[:limit],
            unavailable_reason=cached_result.unavailable_reason,
        )

    # Use scraper as the only source
    try:
        from services.news_trending_x_scraper import fetch_trending_topics_scraper
        
        logger.info("x_trending_fetching_via_scraper", country=country_key, limit=limit)
        result = await fetch_trending_topics_scraper(limit=limit, country=country_key)
        
        if result.topics:
            logger.info("x_trending_scraper_success", country=country_key, topics_count=len(result.topics))
        else:
            logger.warning("x_trending_scraper_no_topics", country=country_key, unavailable_reason=result.unavailable_reason)
        
    except Exception as exc:
        logger.error("x_trending_scraper_error", country=country_key, error=str(exc), error_type=type(exc).__name__)
        result = TrendingResult(
            topics=[],
            unavailable_reason="x_trending_unavailable_scraper_error",
        )
    
    # Cache the result
    bucket["result"] = result
    if result.unavailable_reason:
        # Cache unavailable results for shorter time (30 seconds)
        bucket["expires_at"] = now + 30
    else:
        # Cache successful results for 3 minutes
        bucket["expires_at"] = now + _DEFAULT_CACHE_TTL_SECONDS

    return TrendingResult(
        topics=result.topics[:limit],
        unavailable_reason=result.unavailable_reason,
    )
