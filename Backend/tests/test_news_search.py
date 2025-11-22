from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api.routers import news as news_router
from app.main import app
from app.models.news_public import NewsItem

client = TestClient(app)


def test_news_search_min_length():
    response = client.get("/api/v1/news/search?q=a")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_news_search_happy_path(monkeypatch):
    now = datetime.now(timezone.utc)
    sample_item = NewsItem(
        id=101,
        title="Rotterdam diaspora event",
        snippet="Short summary",
        source="Rotterdam Dagblad",
        published_at=now,
        url="https://example.com/rotterdam",
        image_url=None,
        tags=["diaspora"],
    )

    async def fake_search_news(*, query: str, limit: int, offset: int):
        assert query == "rotterdam"
        assert limit == 5
        assert offset == 0
        return [sample_item], 1

    monkeypatch.setattr(news_router, "search_news_service", fake_search_news)

    response = await news_router.search_news(q="rotterdam", limit=5, offset=0)
    payload = response.model_dump()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == sample_item.title
    assert payload["items"][0]["tags"] == sample_item.tags

