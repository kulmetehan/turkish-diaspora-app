from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.news_extraction import ExtractedNewsItem, ExtractedNewsPayload
from services.news_extraction_service import NewsExtractionService


class DummyOpenAI:
    """Mock OpenAI service for testing."""

    def __init__(self, articles: list[ExtractedNewsItem] | None = None) -> None:
        self.calls = []
        if articles is None:
            articles = [
                ExtractedNewsItem(
                    title="Test Article",
                    snippet="Test snippet",
                    published_at=datetime(2025, 1, 1, 12, tzinfo=timezone.utc),
                    url="https://example.com/article",
                    image_url=None,
                    source="Test Source",
                )
            ]
        self.articles = articles

    def generate_json(self, **kwargs):
        self.calls.append(kwargs)
        payload = ExtractedNewsPayload(articles=self.articles)
        return payload, {"ok": True}


def test_extract_news_from_html_calls_openai():
    """Test that extract_news_from_html calls OpenAI service."""
    dummy = DummyOpenAI()
    service = NewsExtractionService(openai_client=dummy)

    payload, meta = service.extract_news_from_html(
        html="<div>News Article</div>",
        source_key="scrape_turksemedia_nl",
        page_url="https://turksemedia.nl/",
    )

    assert payload.articles
    assert meta["ok"] is True
    assert dummy.calls
    call = dummy.calls[0]
    assert call["action_type"] == "news.extract_from_html"
    assert "scrape_turksemedia_nl" in call["user_prompt"]


def test_extract_news_requires_html():
    """Test that empty HTML raises ValueError."""
    service = NewsExtractionService(openai_client=DummyOpenAI())
    with pytest.raises(ValueError, match="cannot be empty"):
        service.extract_news_from_html(
            html="   ",
            source_key="scrape_turksemedia_nl",
            page_url="https://turksemedia.nl/",
        )


def test_extract_news_model_dump_json_is_serializable():
    """Test that extracted payload can be serialized to JSON."""
    dummy = DummyOpenAI()
    service = NewsExtractionService(openai_client=dummy)
    payload, _ = service.extract_news_from_html(
        html="<div>Article</div>",
        source_key="scrape_turksemedia_nl",
        page_url="https://turksemedia.nl/",
    )
    data = payload.model_dump(mode="json")
    assert isinstance(data["articles"][0]["published_at"], str)
    assert data["articles"][0]["title"] == "Test Article"


def test_extract_news_multiple_articles():
    """Test extraction of multiple articles."""
    articles = [
        ExtractedNewsItem(
            title=f"Article {i}",
            snippet=f"Snippet {i}",
            published_at=datetime(2025, 1, 1, 12 + i, tzinfo=timezone.utc),
            url=f"https://example.com/article{i}",
            source="Test Source",
        )
        for i in range(3)
    ]
    dummy = DummyOpenAI(articles=articles)
    service = NewsExtractionService(openai_client=dummy)
    
    payload, _ = service.extract_news_from_html(
        html="<div>Multiple articles</div>",
        source_key="scrape_turksemedia_nl",
        page_url="https://turksemedia.nl/",
    )
    
    assert len(payload.articles) == 3
    assert payload.articles[0].title == "Article 0"










