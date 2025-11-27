import os

import pytest

from services import news_trending_x
from services.news_trending_x import TrendingResult


@pytest.mark.asyncio
async def test_fetch_trending_topics_uses_stub_when_allowed(monkeypatch):
    async def fake_fetch(*_, **__):
        return TrendingResult(topics=[], unavailable_reason=None)

    monkeypatch.setenv("X_TRENDING_ALLOW_STUBS", "1")
    monkeypatch.setattr(news_trending_x, "_fetch_from_x_api", fake_fetch)
    news_trending_x._cache.clear()

    result = await news_trending_x.fetch_trending_topics(limit=3, country="nl")
    assert len(result.topics) == 3
    assert result.unavailable_reason is None


@pytest.mark.asyncio
async def test_fetch_trending_topics_returns_empty_without_stub(monkeypatch):
    async def fake_fetch(*_, **__):
        return TrendingResult(topics=[], unavailable_reason="x_trending_unavailable_error")

    monkeypatch.delenv("X_TRENDING_ALLOW_STUBS", raising=False)
    monkeypatch.setattr(news_trending_x, "_fetch_from_x_api", fake_fetch)
    news_trending_x._cache.clear()

    result = await news_trending_x.fetch_trending_topics(limit=3, country="tr")
    assert len(result.topics) == 0
    assert result.unavailable_reason == "x_trending_unavailable_error"


@pytest.mark.asyncio
async def test_fetch_trending_topics_stub_disabled_by_default(monkeypatch):
    """Stub fallback is disabled by default (X_TRENDING_ALLOW_STUBS defaults to false)."""
    async def fake_fetch(*_, **__):
        return TrendingResult(topics=[], unavailable_reason="x_trending_unavailable_error")

    monkeypatch.delenv("X_TRENDING_ALLOW_STUBS", raising=False)
    monkeypatch.setattr(news_trending_x, "_fetch_from_x_api", fake_fetch)
    news_trending_x._cache.clear()

    result = await news_trending_x.fetch_trending_topics(limit=5, country="nl")
    assert len(result.topics) == 0
    assert result.unavailable_reason is not None


@pytest.mark.asyncio
async def test_fetch_trending_topics_returns_unavailable_reason_on_403(monkeypatch):
    """403 errors should return unavailable_reason with forbidden code."""
    import httpx

    async def fake_fetch(*_, **__):
        # Simulate 403 error
        response = httpx.Response(403, text="Forbidden")
        raise httpx.HTTPStatusError("Forbidden", request=None, response=response)

    monkeypatch.setenv("X_API_BEARER_TOKEN", "test_token")
    monkeypatch.setattr(news_trending_x, "_fetch_from_x_api", fake_fetch)
    news_trending_x._cache.clear()

    result = await news_trending_x.fetch_trending_topics(limit=5, country="nl")
    assert len(result.topics) == 0
    assert result.unavailable_reason == "x_trending_unavailable_forbidden"

