from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.news_pages_raw import NewsPageRawCreate
from services import news_pages_raw_service
from services.news_pages_raw_service import (
    fetch_pending_news_pages,
    insert_news_page_raw,
    update_news_page_processing_state,
)


def _create_page(**overrides) -> NewsPageRawCreate:
    """Helper to create test news page."""
    base = {
        "news_source_key": "scrape_turksemedia_nl",
        "page_url": "https://turksemedia.nl/",
        "http_status": 200,
        "response_headers": {"Content-Type": "text/html"},
        "response_body": "<html>News content</html>",
        "content_hash": "a" * 40,
        "processing_state": "pending",
    }
    base.update(overrides)
    return NewsPageRawCreate(**base)


@pytest.mark.asyncio
async def test_insert_news_page_raw_returns_id(monkeypatch):
    """Test that insert_news_page_raw returns ID on success."""
    captured = {}

    async def fake_fetchrow(query, *args):
        captured["query"] = query
        captured["args"] = args
        return {"id": 42}

    monkeypatch.setattr(news_pages_raw_service, "fetchrow", fake_fetchrow)

    payload = _create_page()
    new_id = await insert_news_page_raw(payload)

    assert new_id == 42
    assert "news_pages_raw" in captured["query"]


@pytest.mark.asyncio
async def test_insert_news_page_raw_dedup(monkeypatch):
    """Test that duplicate pages return None."""
    async def fake_fetchrow(query, *args):
        return None

    monkeypatch.setattr(news_pages_raw_service, "fetchrow", fake_fetchrow)

    payload = _create_page()
    new_id = await insert_news_page_raw(payload)

    assert new_id is None


@pytest.mark.asyncio
async def test_fetch_pending_news_pages(monkeypatch):
    """Test fetching pending news pages."""
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    fake_row = {
        "id": 5,
        "news_source_key": "scrape_turksemedia_nl",
        "page_url": "https://turksemedia.nl/",
        "http_status": 200,
        "response_headers": {"Content-Type": "text/html"},
        "response_body": "<html>News</html>",
        "content_hash": "b" * 40,
        "processing_state": "pending",
        "processing_errors": None,
        "fetched_at": now,
        "created_at": now,
    }

    async def fake_fetch(query, *args):
        assert "FROM news_pages_raw" in query
        return [dict(fake_row)]

    monkeypatch.setattr(news_pages_raw_service, "fetch", fake_fetch)

    pages = await fetch_pending_news_pages(limit=10)
    assert len(pages) == 1
    assert pages[0].id == 5
    assert pages[0].news_source_key == "scrape_turksemedia_nl"


@pytest.mark.asyncio
async def test_update_news_page_processing_state(monkeypatch):
    """Test updating processing state."""
    captured = {}

    async def fake_execute(query, *args):
        captured["query"] = query
        captured["args"] = args

    monkeypatch.setattr(news_pages_raw_service, "execute", fake_execute)

    await update_news_page_processing_state(
        page_id=1,
        state="extracted",
        errors=None,
    )

    assert "UPDATE news_pages_raw" in captured["query"]
    assert captured["args"][0] == 1
    assert captured["args"][1] == "extracted"


@pytest.mark.asyncio
async def test_update_news_page_processing_state_invalid(monkeypatch):
    """Test that invalid state raises ValueError."""
    with pytest.raises(ValueError, match="Invalid page state"):
        await update_news_page_processing_state(
            page_id=1,
            state="invalid_state",
            errors=None,
        )







