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


def test_normalize_category_filters_nl_mapping():
    """Verify NL category keys map to RSS categories."""
    result = news_service.normalize_category_filters(
        ["general", "sport", "economie", "cultuur"],
        FeedType.NL,
    )
    assert result == ["nl_national", "nl_national_sport", "nl_national_economie", "nl_national_cultuur"]


def test_normalize_category_filters_tr_mapping():
    """Verify TR category keys map to RSS categories."""
    result = news_service.normalize_category_filters(
        ["general", "sport", "economie", "magazin"],
        FeedType.TR,
    )
    assert result == ["tr_national", "tr_national_sport", "tr_national_economie", "tr_national_magazin"]


def test_normalize_category_filters_ignores_invalid():
    """Invalid category keys are ignored (not mapped)."""
    result = news_service.normalize_category_filters(
        ["general", "unknown", "sport"],
        FeedType.NL,
    )
    assert result == ["nl_national", "nl_national_sport"]


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
async def test_list_news_by_feed_applies_category_filter(monkeypatch):
    """Verify category filter is applied to SQL query for NL feed."""
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
                "topics": [],
                "location_tag": None,
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
        FeedType.NL,
        limit=5,
        offset=0,
        categories=["sport"],
    )

    assert total == 1
    # Verify category filter is in SQL (not topics JSONB)
    assert "category" in captured["query"].lower()
    assert "nl_national_sport" in str(captured["params"])
    assert "COALESCE(topics" not in captured["query"]  # Should not use topics
    assert len(items) == 1
    assert items[0].title == "Nieuws 2"


@pytest.mark.asyncio
async def test_get_news_invalid_feed():
    with pytest.raises(HTTPException) as exc:
        await news_router.get_news(feed="invalid", limit=5, offset=0)
    assert exc.value.status_code == 400
    assert "invalid feed" in exc.value.detail.lower()




@pytest.mark.asyncio
async def test_get_news_trending_response(monkeypatch):
    from services.news_trending_x import TrendingTopic, TrendingResult
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    sample_topic = TrendingTopic(
        title="Trending Story",
        url="https://example.com/trending",
        description="Description",
        published_at=now,
    )

    async def fake_trending(limit: int, country: str):
        return TrendingResult(topics=[sample_topic], unavailable_reason=None)

    monkeypatch.setattr(news_router, "fetch_trending_topics", fake_trending)

    response = await news_router.get_news(feed="trending", limit=1, offset=0)
    payload = response.model_dump()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Trending Story"
    assert payload.get("meta") is None  # No unavailable_reason when successful

# Note: trending test monkeypatches router-level list_trending_news to avoid DB access.


@pytest.mark.asyncio
async def test_get_news_trending_rejects_categories():
    """Trending feed should reject category filters."""
    with pytest.raises(HTTPException) as exc:
        await news_router.get_news(feed="trending", limit=1, offset=0, categories=["sport"])
    assert exc.value.status_code == 400
    assert "not supported" in exc.value.detail or "categories" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_get_trending_news_route(monkeypatch):
    from services.news_trending_x import TrendingTopic, TrendingResult

    now = datetime.now(timezone.utc)
    sample_topic = TrendingTopic(
        title="Geo Highlight",
        url="https://example.com/geo",
        description="Snippet",
        published_at=now,
    )

    async def fake_trending(limit: int, country: str):
        assert limit == 2
        return TrendingResult(topics=[sample_topic], unavailable_reason=None)

    monkeypatch.setattr(news_router, "fetch_trending_topics", fake_trending)

    response = await news_router.get_trending_news(limit=2, offset=0)
    payload = response.model_dump()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Geo Highlight"
    assert payload["items"][0]["tags"] == ["trending"]


@pytest.mark.asyncio
async def test_get_trending_news_returns_unavailable_meta(monkeypatch):
    """Trending endpoint should include meta.unavailable_reason when X API fails."""
    from services.news_trending_x import TrendingResult

    async def fake_trending(limit: int, country: str):
        return TrendingResult(
            topics=[],
            unavailable_reason="x_trending_unavailable_forbidden",
        )

    monkeypatch.setattr(news_router, "fetch_trending_topics", fake_trending)

    response = await news_router.get_trending_news(limit=5, offset=0)
    payload = response.model_dump()
    assert payload["total"] == 0
    assert len(payload["items"]) == 0
    assert payload["meta"] is not None
    assert payload["meta"]["unavailable_reason"] == "x_trending_unavailable_forbidden"


@pytest.mark.asyncio
async def test_get_news_local_requires_cities_nl(monkeypatch):
    """Local feed requires cities_nl parameter."""
    with pytest.raises(HTTPException) as exc:
        await news_router.get_news(feed="local", limit=10, offset=0, cities_nl=None)
    assert exc.value.status_code == 400
    assert "cities_nl" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_get_news_origin_requires_cities_tr(monkeypatch):
    """Origin feed requires cities_tr parameter."""
    with pytest.raises(HTTPException) as exc:
        await news_router.get_news(feed="origin", limit=10, offset=0, cities_tr=None)
    assert exc.value.status_code == 400
    assert "cities_tr" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_get_news_local_calls_google_service(monkeypatch):
    """Local feed should call Google News service."""
    from app.models.news_public import NewsItem

    mock_item = NewsItem(
        id=1,
        title="Local News",
        snippet="Snippet",
        source="Google News – Rotterdam",
        published_at=datetime.now(timezone.utc),
        url="https://example.com/local",
        image_url=None,
        tags=[],
    )

    async def fake_google_news(*, country: str, city_key: str, limit: int):
        assert country == "nl"
        assert city_key == "rotterdam"
        return [mock_item]

    monkeypatch.setattr(news_router, "fetch_google_news_for_city", fake_google_news)

    response = await news_router.get_news(
        feed="local",
        limit=10,
        offset=0,
        cities_nl=["rotterdam"],
    )
    payload = response.model_dump()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Local News"
    assert payload["items"][0]["source"] == "Google News – Rotterdam"


@pytest.mark.asyncio
async def test_get_news_origin_calls_google_service(monkeypatch):
    """Origin feed should call Google News service."""
    from app.models.news_public import NewsItem

    mock_item = NewsItem(
        id=2,
        title="Origin News",
        snippet="Snippet",
        source="Google News – Istanbul",
        published_at=datetime.now(timezone.utc),
        url="https://example.com/origin",
        image_url=None,
        tags=[],
    )

    async def fake_google_news(*, country: str, city_key: str, limit: int):
        assert country == "tr"
        assert city_key == "istanbul"
        return [mock_item]

    monkeypatch.setattr(news_router, "fetch_google_news_for_city", fake_google_news)

    response = await news_router.get_news(
        feed="origin",
        limit=10,
        offset=0,
        cities_tr=["istanbul"],
    )
    payload = response.model_dump()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Origin News"
    assert payload["items"][0]["source"] == "Google News – Istanbul"


