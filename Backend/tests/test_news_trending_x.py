import os

import pytest

from services import news_trending_x


@pytest.mark.asyncio
async def test_fetch_trending_topics_uses_stub_when_allowed(monkeypatch):
    async def fake_fetch(*_, **__):
        return []

    monkeypatch.setenv("X_TRENDING_ALLOW_STUBS", "1")
    monkeypatch.setattr(news_trending_x, "_fetch_from_x_api", fake_fetch)
    news_trending_x._cache.clear()

    topics = await news_trending_x.fetch_trending_topics(limit=3, country="nl")
    assert len(topics) == 3


@pytest.mark.asyncio
async def test_fetch_trending_topics_returns_empty_without_stub(monkeypatch):
    async def fake_fetch(*_, **__):
        return []

    monkeypatch.delenv("X_TRENDING_ALLOW_STUBS", raising=False)
    monkeypatch.setattr(news_trending_x, "_fetch_from_x_api", fake_fetch)
    news_trending_x._cache.clear()

    topics = await news_trending_x.fetch_trending_topics(limit=3, country="tr")
    assert topics == []

