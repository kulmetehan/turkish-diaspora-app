from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import pytest
from fastapi import HTTPException

from api.routers import news as news_router
from app.models.news_public import NewsItem
from services import news_service
from services.news_feed_rules import FeedThresholds, FeedType


def _sample_thresholds() -> FeedThresholds:
    return FeedThresholds(
        news_diaspora_min_score=0.75,
        news_nl_min_score=0.75,
        news_tr_min_score=0.75,
        news_local_min_score=0.70,
        news_origin_min_score=0.70,
        news_geo_min_score=0.80,
    )


def test_normalize_theme_filters_deduplicates():
    result = news_service.normalize_theme_filters(
        ["Politics", "economy", "culture,politics", "economy"]
    )
    assert result == ["politics", "economy", "culture"]


def test_normalize_theme_filters_invalid_value():
    with pytest.raises(ValueError):
        news_service.normalize_theme_filters(["unknown"])


@pytest.mark.asyncio
async def test_list_news_by_feed_returns_items(monkeypatch):
    async def fake_thresholds() -> FeedThresholds:
        return _sample_thresholds()

    async def fake_fetch(query: str, *params: Any) -> List[Dict[str, Any]]:
        return [
            {
                "id": 1,
                "title": "Nieuws 1",
                "summary": "Korte samenvatting",
                "content": None,
                "source_name": "Test Source",
                "link": "https://example.com/n1",
                "image_url": None,
                "published_at": datetime.now(timezone.utc),
                "topics": ["community", "culture"],
                "location_tag": "local",
            }
        ]

    async def fake_fetchrow(query: str, *params: Any) -> Dict[str, Any]:
        return {"total": 1}

    monkeypatch.setattr(news_service, "_load_feed_thresholds", fake_thresholds)
    monkeypatch.setattr(news_service, "fetch", fake_fetch)
    monkeypatch.setattr(news_service, "fetchrow", fake_fetchrow)

    items, total = await news_service.list_news_by_feed(
        FeedType.DIASPORA, limit=5, offset=0
    )
    assert total == 1
    assert len(items) == 1
    assert items[0].snippet == "Korte samenvatting"
    assert items[0].source == "Test Source"
    assert "local" in items[0].tags
    assert "community" in items[0].tags


@pytest.mark.asyncio
async def test_list_news_by_feed_applies_theme_filter(monkeypatch):
    async def fake_thresholds() -> FeedThresholds:
        return _sample_thresholds()

    captured: Dict[str, Any] = {}

    async def fake_fetch(query: str, *params: Any) -> List[Dict[str, Any]]:
        captured["query"] = query
        captured["params"] = params
        return [
            {
                "id": 2,
                "title": "Nieuws 2",
                "summary": "Samenvatting",
                "content": None,
                "source_name": "Source",
                "link": "https://example.com/n2",
                "image_url": None,
                "published_at": datetime.now(timezone.utc),
                "topics": ["politics"],
                "location_tag": "local",
            }
        ]

    async def fake_fetchrow(query: str, *params: Any) -> Dict[str, Any]:
        captured["count_query"] = query
        captured["count_params"] = params
        return {"total": 1}

    monkeypatch.setattr(news_service, "_load_feed_thresholds", fake_thresholds)
    monkeypatch.setattr(news_service, "fetch", fake_fetch)
    monkeypatch.setattr(news_service, "fetchrow", fake_fetchrow)

    items, total = await news_service.list_news_by_feed(
        FeedType.DIASPORA,
        limit=5,
        offset=0,
        themes=["politics", "economy"],
    )

    assert total == 1
    assert captured["params"][-3] == ["politics", "economy"]
    assert captured["count_params"][-1] == ["politics", "economy"]
    assert "COALESCE(topics" in captured["query"]
    assert len(items) == 1
    assert items[0].title == "Nieuws 2"


@pytest.mark.asyncio
async def test_get_news_invalid_feed():
    with pytest.raises(HTTPException) as exc:
        await news_router.get_news(feed="invalid", limit=5, offset=0)
    assert exc.value.status_code == 400
    assert "invalid feed" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_get_news_invalid_theme():
    with pytest.raises(HTTPException) as exc:
        await news_router.get_news(feed="diaspora", limit=5, offset=0, themes=["unknown"])
    assert exc.value.status_code == 400
    assert "invalid theme" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_get_news_trending_response(monkeypatch):
    now = datetime.now(timezone.utc)
    sample_item = NewsItem(
        id=42,
        title="Trending Story",
        snippet="Snippet",
        source="Source",
        published_at=now,
        url="https://example.com/trending",
        image_url=None,
        tags=["geo"],
    )

    async def fake_trending(*, limit: int, offset: int) -> Tuple[List[NewsItem], int]:
        return [sample_item], 1

    monkeypatch.setattr(news_router, "list_trending_news", fake_trending)

    response = await news_router.get_news(feed="trending", limit=1, offset=0)
    payload = response.model_dump()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Trending Story"
    assert "raw_entry" not in payload["items"][0]
    assert payload["items"][0]["tags"] == ["geo"]

# Note: trending test monkeypatches router-level list_trending_news to avoid DB access.


@pytest.mark.asyncio
async def test_get_news_trending_rejects_themes():
    with pytest.raises(HTTPException) as exc:
        await news_router.get_news(feed="trending", limit=1, offset=0, themes=["politics"])
    assert exc.value.status_code == 400
    assert "not supported" in exc.value.detail


@pytest.mark.asyncio
async def test_get_trending_news_route(monkeypatch):
    now = datetime.now(timezone.utc)
    sample_item = NewsItem(
        id=7,
        title="Geo Highlight",
        snippet="Snippet",
        source="Geo Source",
        published_at=now,
        url="https://example.com/geo",
        image_url=None,
        tags=["geo"],
    )

    async def fake_trending(*, limit: int, offset: int):
        assert limit == 2
        return [sample_item], 1

    monkeypatch.setattr(news_router, "list_trending_news", fake_trending)

    response = await news_router.get_trending_news(limit=2, offset=0)
    payload = response.model_dump()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Geo Highlight"
    assert payload["items"][0]["tags"] == ["geo"]


