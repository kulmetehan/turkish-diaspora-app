"""
X (Twitter) trending topics service.

To enable real X trending topics, set the X_API_BEARER_TOKEN environment variable
in your Backend environment (local .env and production).

Stub topics are disabled by default. Set X_TRENDING_ALLOW_STUBS=true to enable fallback stubs.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx

from app.core.logging import get_logger

logger = get_logger().bind(module="news_trending_x")

_DEFAULT_CACHE_TTL_SECONDS = int(os.getenv("X_TRENDING_CACHE_TTL_SECONDS", "180"))
_DEFAULT_WOEIDS = {
    "nl": "734047",  # Amsterdam
    "tr": "2343732",  # Turkey
}
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
    unavailable_reason: Optional[str] = None  # e.g., "x_trending_unavailable_forbidden", "x_trending_unavailable_error"


async def fetch_trending_topics(limit: int = 20, country: str = "nl") -> TrendingResult:
    """
    Fetch trending topics from X API.
    Returns TrendingResult with topics and optional unavailable_reason.
    """
    country_key = (country or "nl").lower()
    bucket = _cache.setdefault(country_key, {"expires_at": 0.0, "result": None})
    now = time.time()
    
    # Check cache
    if bucket.get("result") and now < float(bucket.get("expires_at", 0)):
        cached_result: TrendingResult = bucket["result"]
        return TrendingResult(
            topics=cached_result.topics[:limit],
            unavailable_reason=cached_result.unavailable_reason,
        )

    # Fetch from X API
    result = await _fetch_from_x_api(limit=limit, country=country_key)
    
    # Handle stub fallback only if explicitly enabled and no error reason
    if not result.topics and not result.unavailable_reason and _allow_stub_topics():
        logger.info("x_trending_using_stubs", country=country_key)
        stub_topics = _build_stub_topics(country_key)
        result = TrendingResult(topics=stub_topics, unavailable_reason=None)
        bucket["result"] = result
        bucket["expires_at"] = now + min(_DEFAULT_CACHE_TTL_SECONDS, 120)
    else:
        bucket["result"] = result
        if result.unavailable_reason:
            # Cache unavailable results for shorter time
            bucket["expires_at"] = now + 30
        else:
            bucket["expires_at"] = now + _DEFAULT_CACHE_TTL_SECONDS

    return TrendingResult(
        topics=result.topics[:limit],
        unavailable_reason=result.unavailable_reason,
    )


def _sanitize_response_body(body: str, max_len: int = 200) -> str:
    """Sanitize response body, removing bearer token if present."""
    if not body:
        return ""
    # Remove bearer token patterns (defensive)
    sanitized = re.sub(r'bearer\s+[a-zA-Z0-9_-]+', 'bearer [REDACTED]', body, flags=re.IGNORECASE)
    return sanitized[:max_len]


async def _fetch_from_x_api(limit: int, country: str) -> TrendingResult:
    """
    Fetch trending topics from X API.
    Returns TrendingResult with topics or unavailable_reason on failure.
    """
    bearer_token = os.getenv("X_API_BEARER_TOKEN")
    woeid = _resolve_woeid(country)

    if not bearer_token:
        logger.info("x_api_bearer_token_missing")
        return TrendingResult(
            topics=[],
            unavailable_reason="x_trending_unavailable_no_token",
        )

    url = "https://api.x.com/1.1/trends/place.json"
    params = {"id": woeid}
    headers = {"Authorization": f"Bearer {bearer_token}"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        # Extract status code and response body
        status_code = exc.response.status_code
        body_preview = ""
        try:
            body_text = exc.response.text
            body_preview = _sanitize_response_body(body_text)
        except Exception:
            pass
        
        # Determine reason code based on status
        if status_code == 403:
            reason = "x_trending_unavailable_forbidden"
        elif status_code == 401:
            reason = "x_trending_unavailable_unauthorized"
        else:
            reason = f"x_trending_unavailable_error_{status_code}"
        
        logger.warning(
            "x_trending_fetch_failed",
            status_code=status_code,
            error=str(exc),
            body_preview=body_preview,
        )
        return TrendingResult(topics=[], unavailable_reason=reason)
    except Exception as exc:
        logger.warning("x_trending_fetch_failed", error=str(exc))
        return TrendingResult(
            topics=[],
            unavailable_reason="x_trending_unavailable_error",
        )

    try:
        trends = payload[0]["trends"]
    except (IndexError, KeyError, TypeError):
        logger.warning("x_trending_payload_invalid", payload=payload)
        return TrendingResult(
            topics=[],
            unavailable_reason="x_trending_unavailable_invalid_payload",
        )

    topics: List[TrendingTopic] = []
    for trend in trends:
        name = trend.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        url = trend.get("url") or f"https://twitter.com/search?q={name}"
        topic = TrendingTopic(
            title=name.strip(),
            url=url,
            description=trend.get("query"),
            published_at=datetime.now(timezone.utc),
        )
        topics.append(topic)
        if len(topics) >= limit:
            break
    
    return TrendingResult(topics=topics, unavailable_reason=None)


def _resolve_woeid(country: str) -> str:
    country_key = (country or "nl").lower()
    env_override = os.getenv(f"X_API_WOEID_{country_key.upper()}")
    if env_override:
        return env_override
    fallback = os.getenv("X_API_WOEID")
    if fallback:
        return fallback
    return _DEFAULT_WOEIDS.get(country_key, _DEFAULT_WOEIDS["nl"])


def _build_stub_topics(country: str) -> List[TrendingTopic]:
    now = datetime.now(timezone.utc)
    if country == "tr":
        sample_titles = [
            "İstanbul trafiği",
            "Ankara gündemi",
            "Habertürk ekonomi",
            "Galatasaray maçı",
            "Deprem uyarısı",
        ]
    else:
        sample_titles = [
            "Rotterdam marathon",
            "Nieuw kabinet",
            "NOS breaking",
            "Eredivisie nieuws",
            "Den Haag debat",
        ]
    return [
        TrendingTopic(
            title=title,
            url=f"https://twitter.com/search?q={title.replace(' ', '%20')}",
            description=None,
            published_at=now - timedelta(minutes=index * 5),
        )
        for index, title in enumerate(sample_titles)
    ]


def _allow_stub_topics() -> bool:
    """Check if stub topics are allowed. Defaults to False (disabled)."""
    value = os.getenv("X_TRENDING_ALLOW_STUBS", "false").lower()
    return value in {"1", "true", "yes", "on"}

