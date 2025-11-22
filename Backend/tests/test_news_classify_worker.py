from __future__ import annotations

from typing import Any, Dict, List

import pytest

from app.workers import news_classify_bot
from services.news_classification_service import LocationMention, NewsClassificationResult
from services.news_feed_rules import FeedThresholds


class DummyService:
    def __init__(self, responses: List[tuple[Any, Dict[str, Any]]]) -> None:
        self._responses = responses
        self.calls: List[int] = []

    def classify_news_item(
        self,
        *,
        news_id: int,
        title: str,
        summary: str | None,
        content: str | None,
        source_key: str,
        language_hint: str | None,
    ):
        self.calls.append(news_id)
        return self._responses[len(self.calls) - 1]


@pytest.mark.asyncio
async def test_process_pending_news_success_and_error(monkeypatch):
    rows = [
        {
            "id": 1,
            "title": "Nieuws 1",
            "summary": "Samenvatting over Rotterdam",
            "content": "Volledige tekst",
            "source_key": "source-1",
            "language": "nl",
            "category": "nl_local",
            "region": "rotterdam",
            "raw_entry": {},
        },
        {
            "id": 2,
            "title": "Nieuws 2",
            "summary": None,
            "content": None,
            "source_key": "source-2",
            "language": "nl",
            "category": "nl_local",
            "region": "rotterdam",
            "raw_entry": {},
        },
    ]

    async def fake_fetch(limit: int):
        return rows

    successes: List[tuple[int, NewsClassificationResult, str, Dict[str, Any]]] = []
    errors: List[tuple[int, Dict[str, Any]]] = []

    async def fake_success(row_id: int, result: NewsClassificationResult, location_tag: str, location_context: Dict[str, Any]):
        successes.append((row_id, result, location_tag, location_context))

    async def fake_error(row_id: int, error_meta: Dict[str, Any]):
        errors.append((row_id, error_meta))

    service = DummyService(
        responses=[
            (
                NewsClassificationResult(
                    relevance_diaspora=0.8,
                    relevance_nl=0.7,
                    relevance_tr=0.2,
                    relevance_geo=0.3,
                    topics=["diaspora", "community"],
                    language="nl",
                    location_mentions=[LocationMention(city_key="rotterdam", country="nl", confidence=0.92)],
                ),
                {"raw": "ok"},
            ),
            (None, {"error": "boom"}),
        ]
    )

    monkeypatch.setattr(news_classify_bot, "_fetch_pending_news", fake_fetch)
    monkeypatch.setattr(news_classify_bot, "_mark_classification_success", fake_success)
    monkeypatch.setattr(news_classify_bot, "_mark_classification_error", fake_error)
    async def fake_load_feed_thresholds():
        return FeedThresholds(
            news_diaspora_min_score=0.75,
            news_nl_min_score=0.75,
            news_tr_min_score=0.75,
            news_local_min_score=0.70,
            news_origin_min_score=0.70,
            news_geo_min_score=0.80,
        )

    monkeypatch.setattr(news_classify_bot, "_load_feed_thresholds", fake_load_feed_thresholds)

    counters = await news_classify_bot.process_pending_news(
        limit=10,
        model=None,
        worker_run_id=None,
        service=service,
    )

    assert counters == {"total": 2, "classified": 1, "errors": 1}
    assert len(successes) == 1
    assert successes[0][0] == 1
    assert successes[0][1].topics == ["diaspora", "community"]
    assert successes[0][2] == "local"
    assert successes[0][3]["matches"]
    assert len(errors) == 1
    assert errors[0][0] == 2
    assert errors[0][1]["error"] == "boom"


@pytest.mark.asyncio
async def test_process_pending_news_empty(monkeypatch):
    async def fake_fetch(limit: int):
        return []

    monkeypatch.setattr(news_classify_bot, "_fetch_pending_news", fake_fetch)

    counters = await news_classify_bot.process_pending_news(
        limit=5,
        model=None,
        worker_run_id=None,
        service=DummyService([]),
    )

    assert counters == {"total": 0, "classified": 0, "errors": 0}

