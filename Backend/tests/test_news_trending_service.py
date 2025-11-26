from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services import news_service
from services.news_feed_rules import FeedThresholds


@pytest.mark.asyncio
async def test_list_trending_news_applies_thresholds(monkeypatch):
    thresholds = FeedThresholds(
        news_diaspora_min_score=0.8,
        news_nl_min_score=0.7,
        news_tr_min_score=0.6,
        news_local_min_score=0.5,
        news_origin_min_score=0.4,
        news_geo_min_score=0.3,
    )

    async def fake_load_feed_thresholds() -> FeedThresholds:
        return thresholds

    captured: dict = {}

    async def fake_fetch(query: str, *params):
        captured["query"] = query
        captured["params"] = params
        return [
            {
                "id": 42,
                "title": "Trending Geo Story",
                "summary": "summary",
                "content": None,
                "source_name": "News Source",
                "link": "https://example.com/article",
                "image_url": None,
                "published_at": datetime.now(timezone.utc),
                "topics": ["geo"],
                "location_tag": "origin",
                "trending_score": 0.87,
                "hours_since": 1.2,
                "source_freq": 3,
            }
        ]

    async def fake_fetchrow(query: str, *params):
        captured["count_query"] = query
        captured["count_params"] = params
        return {"total": 1}

    monkeypatch.setattr(news_service, "_load_feed_thresholds", fake_load_feed_thresholds)
    monkeypatch.setattr(news_service, "fetch", fake_fetch)
    monkeypatch.setattr(news_service, "fetchrow", fake_fetchrow)

    items, total = await news_service.list_trending_news(limit=1, offset=0, window_hours=48)

    assert total == 1
    assert items[0].title == "Trending Geo Story"
    assert "COALESCE(relevance_diaspora, 0) >= $2" in captured["query"]
    assert captured["params"][1] == thresholds.news_diaspora_min_score
    assert captured["params"][2] == thresholds.news_geo_min_score
    assert items[0].tags == ["origin", "geo"]





