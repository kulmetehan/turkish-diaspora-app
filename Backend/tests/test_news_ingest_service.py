from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from app.models.news_sources import NewsSource
from services import news_ingest_service
from services.news_ingest_service import NewsIngestService, ingest_all_sources


def _make_source(name: str = "Test Source") -> NewsSource:
    return NewsSource(
        name=name,
        url=f"https://{name.replace(' ', '').lower()}.example/rss",
        language="nl",
        category="nl_local",
        license="test-license",
        redistribution_allowed=True,
        robots_policy="ignore",
        raw={
            "region": "rotterdam",
            "_defaults": {"refresh_minutes": 30},
        },
    )


@pytest.mark.asyncio
async def test_ingest_source_persists_entries(monkeypatch):
    inserts: list[str] = []

    async def fake_execute(query, *args):
        inserts.append(query)
        return "INSERT 0 1"

    async def fake_fetchrow(query, *args):
        return None

    async def fake_fetch_feed(self, source):
        return b"<rss></rss>"

    dummy_entry = {
        "title": "Hello World",
        "link": "https://example.com/hello",
        "summary": "Short summary",
        "content": [{"value": "Full body"}],
        "published_parsed": time.gmtime(0),
        "author": "Editor",
    }
    dummy_feed = SimpleNamespace(entries=[dummy_entry])

    monkeypatch.setattr(news_ingest_service, "execute", fake_execute)
    monkeypatch.setattr(news_ingest_service, "fetchrow", fake_fetchrow)
    monkeypatch.setattr(NewsIngestService, "_fetch_feed", fake_fetch_feed, raising=False)
    monkeypatch.setattr(news_ingest_service.feedparser, "parse", lambda raw: dummy_feed)

    source = _make_source()
    service = NewsIngestService()
    result = await service.ingest_source(source)

    assert result["inserted"] == 1
    assert result["failed_items"] == 0
    assert any("raw_ingested_news" in query for query in inserts)


@pytest.mark.asyncio
async def test_ingest_all_sources_flags_degraded(monkeypatch):
    source = _make_source()

    class DummyService:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def ingest_source(self, source):
            return {
                "source_key": source.url,
                "skipped": False,
                "inserted": 0,
                "failed_items": 3,
            }

    monkeypatch.setattr(news_ingest_service, "get_all_news_sources", lambda: [source])
    monkeypatch.setattr(news_ingest_service, "NewsIngestService", DummyService)

    result = await ingest_all_sources()

    assert result["failed_feeds"] == 1
    assert result["degraded"] is True

