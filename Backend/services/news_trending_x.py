"""
X (Twitter) trending topics service.

To enable real X trending topics, set the X_API_BEARER_TOKEN environment variable
in your Backend environment (local .env and production).

Without this token, the system falls back to stub topics and does NOT call the X API.
Stub topics are enabled by default (X_TRENDING_ALLOW_STUBS defaults to "true").
"""

from __future__ import annotations

import os
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


async def fetch_trending_topics(limit: int = 20, country: str = "nl") -> List[TrendingTopic]:
    country_key = (country or "nl").lower()
    bucket = _cache.setdefault(country_key, {"expires_at": 0.0, "topics": []})
    now = time.time()
    if bucket["topics"] and now < float(bucket["expires_at"]):
        return list(bucket["topics"])[:limit]

    topics = await _fetch_from_x_api(limit=limit, country=country_key)
    if not topics:
        if _allow_stub_topics():
            topics = _build_stub_topics(country_key)
            bucket["topics"] = topics
            bucket["expires_at"] = now + min(_DEFAULT_CACHE_TTL_SECONDS, 120)
        else:
            logger.info("x_trending_topics_unavailable", country=country_key)
            bucket["topics"] = []
            bucket["expires_at"] = now + 30
            return []
    else:
        bucket["topics"] = topics
        bucket["expires_at"] = now + _DEFAULT_CACHE_TTL_SECONDS

    return topics[:limit]


async def _fetch_from_x_api(limit: int, country: str) -> List[TrendingTopic]:
    bearer_token = os.getenv("X_API_BEARER_TOKEN")
    woeid = _resolve_woeid(country)

    if not bearer_token:
        logger.info("x_api_bearer_token_missing")
        return []

    url = "https://api.x.com/1.1/trends/place.json"
    params = {"id": woeid}
    headers = {"Authorization": f"Bearer {bearer_token}"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # pragma: no cover - network best effort
        logger.warning("x_trending_fetch_failed", error=str(exc))
        return []

    try:
        trends = payload[0]["trends"]
    except (IndexError, KeyError, TypeError):
        logger.warning("x_trending_payload_invalid", payload=payload)
        return []

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
    return topics


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
    """Check if stub topics are allowed. Defaults to True to provide fallback content."""
    value = os.getenv("X_TRENDING_ALLOW_STUBS", "true").lower()
    return value in {"1", "true", "yes", "on"}

