"""
Google News RSS service for Local and Origin feeds.

Fetches live Google News RSS results for cities without storing in database.
Returns normalized NewsItem DTOs matching the public API contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from urllib.parse import quote_plus

import feedparser
import httpx

from app.models.news_city_config import get_city_by_key, get_city_google_news_query
from app.models.news_public import NewsItem
from app.core.logging import get_logger
from services.rss_normalization import normalize_feed_entries
from app.models.news_sources import NewsSource

logger = get_logger().bind(module="news_google_service")

_DEFAULT_TIMEOUT_S = 10


def _build_google_news_url(query: str, *, language: str, country: str) -> str:
    """Build Google News RSS URL with language and country parameters."""
    encoded = quote_plus(query)
    lang = language.lower()
    country_upper = country.upper()
    return (
        "https://news.google.com/rss/search?"
        f"q={encoded}&hl={lang}&gl={country_upper}&ceid={country_upper}:{lang}"
    )


def _generate_news_id(url: str, published_at: datetime) -> int:
    """Generate a deterministic ID from URL and published_at (same pattern as trending topics)."""
    timestamp = published_at.timestamp() if published_at else 0.0
    return abs(hash((url, timestamp))) % (2**31 - 1)


async def fetch_google_news_for_city(
    *,
    country: str,  # "nl" or "tr"
    city_key: str,
    limit: int = 20,
) -> List[NewsItem]:
    """
    Fetch live Google News RSS results for a city.
    Returns normalized NewsItem DTOs matching the public API contract.
    No DB writes - pure on-demand query.

    Args:
        country: "nl" or "tr"
        city_key: City identifier (e.g., "rotterdam", "istanbul")
        limit: Maximum number of items to return

    Returns:
        List of NewsItem objects, empty list on error
    """
    country_lower = country.strip().lower()
    if country_lower not in ("nl", "tr"):
        logger.warning("news_google_invalid_country", country=country, city_key=city_key)
        return []

    # Resolve city and get Google News query
    city = get_city_by_key(city_key)
    if not city:
        logger.warning("news_google_city_not_found", city_key=city_key, country=country)
        return []

    query = get_city_google_news_query(city_key)
    city_name = city.name

    # Determine language based on country
    language = "nl" if country_lower == "nl" else "tr"
    country_upper = country_lower.upper()

    # Build Google News URL
    url = _build_google_news_url(query, language=language, country=country_upper)

    try:
        # Fetch RSS feed
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "tda-news-google/1.0"},
                follow_redirects=True,
            )
            response.raise_for_status()
            feed_content = response.text
    except Exception as exc:
        logger.warning(
            "news_google_fetch_failed",
            city_key=city_key,
            country=country,
            url=url,
            error=str(exc),
        )
        return []

    try:
        # Parse RSS feed
        parsed = feedparser.parse(feed_content)

        # Create a minimal NewsSource for normalization
        # The normalization function expects a NewsSource object
        source = NewsSource(
            key=f"google_news_{city_key}",
            name=f"Google News – {city_name}",
            url=url,
            language=language,
            category="nl_local" if country_lower == "nl" else "tr_national",
            license="google-news",
            redistribution_allowed=True,
            robots_policy="follow",
            raw={},
        )

        # Normalize feed entries
        normalized_items, norm_errors = normalize_feed_entries(parsed, source)

        # Log normalization errors
        for err in norm_errors:
            logger.debug(
                "news_google_normalization_error",
                city_key=city_key,
                error=str(err),
            )

        # Convert NormalizedNewsItem to NewsItem (public DTO)
        items: List[NewsItem] = []
        for norm_item in normalized_items[:limit]:
            try:
                # Generate deterministic ID
                item_id = _generate_news_id(norm_item.url, norm_item.published_at)

                # Map to public DTO
                news_item = NewsItem(
                    id=item_id,
                    title=norm_item.title,
                    snippet=norm_item.snippet,
                    source=norm_item.source,
                    published_at=norm_item.published_at,
                    url=norm_item.url,
                    image_url=None,  # Google News RSS doesn't typically include images
                    tags=[],  # No tags for Google News items
                )
                items.append(news_item)
            except Exception as exc:
                logger.warning(
                    "news_google_item_conversion_failed",
                    city_key=city_key,
                    url=norm_item.url if hasattr(norm_item, "url") else "unknown",
                    error=str(exc),
                )
                continue

        logger.info(
            "news_google_fetch_success",
            city_key=city_key,
            country=country,
            items_returned=len(items),
            items_normalized=len(normalized_items),
            errors=len(norm_errors),
        )

        return items

    except Exception as exc:
        logger.error(
            "news_google_parse_failed",
            city_key=city_key,
            country=country,
            error=str(exc),
        )
        return []































