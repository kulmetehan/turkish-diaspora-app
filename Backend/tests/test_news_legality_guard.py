from __future__ import annotations

import textwrap
from datetime import datetime, timezone

import pytest

import app.models.news_sources as news_sources_module
from app.models.news_normalized import NormalizedNewsItem
from app.models.news_sources import NewsSource, clear_news_sources_cache, get_all_news_sources
from services.news_ingest_service import NewsIngestService
from services.news_legal_sanitizer import sanitize_ingested_entry


def _make_source(**overrides) -> NewsSource:
    data = {
        "name": overrides.get("name", "Legal Source"),
        "url": overrides.get("url", "https://example.com/rss"),
        "language": overrides.get("language", "nl"),
        "category": overrides.get("category", "nl_local"),
        "license": overrides.get("license", "test-license"),
        "redistribution_allowed": overrides.get("redistribution_allowed", True),
        "robots_policy": overrides.get("robots_policy", "follow"),
        "raw": overrides.get(
            "raw",
            {
                "region": "rotterdam",
                "_defaults": {"refresh_minutes": 5},
            },
        ),
    }
    return NewsSource(**data)


def test_missing_legal_metadata_logs_warning(tmp_path, monkeypatch):
    cfg = tmp_path / "news_sources.yml"
    cfg.write_text(
        textwrap.dedent(
            """
            version: 1
            sources:
              - name: "No Legal"
                url: "https://example.com/rss"
                language: "nl"
                category: "nl_local"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    events = []

    def fake_warning(event_name, **kwargs):
        events.append({"event": event_name, **kwargs})

    monkeypatch.setattr(news_sources_module.logger, "warning", fake_warning)
    clear_news_sources_cache()
    get_all_news_sources(path=cfg)

    assert any(event["event"] == "news_source_missing_legal_metadata" for event in events)


@pytest.mark.asyncio
async def test_ingest_skips_when_redistribution_forbidden(monkeypatch):
    service = NewsIngestService()
    source = _make_source(redistribution_allowed=False)

    async def fake_should_fetch_now(self, _source):
        return True

    async def fake_mark_failure(self, _source, reason):
        fake_mark_failure.reason = reason

    fake_mark_failure.reason = None

    async def fake_fetch_feed(self, _source):
        raise AssertionError("fetch_feed should not be called when legal gate fails")

    monkeypatch.setattr(NewsIngestService, "_should_fetch_now", fake_should_fetch_now, raising=False)
    monkeypatch.setattr(NewsIngestService, "_mark_source_failure", fake_mark_failure, raising=False)
    monkeypatch.setattr(NewsIngestService, "_fetch_feed", fake_fetch_feed, raising=False)

    result = await service.ingest_source(source)

    assert result["skipped"] is True
    assert fake_mark_failure.reason == "redistribution_not_allowed"


@pytest.mark.asyncio
async def test_robots_policy_blocks_ingest(monkeypatch):
    service = NewsIngestService()
    source = _make_source(url="https://example.com/feed.xml", robots_policy="follow")

    async def fake_fetch_robots_txt(self, parsed_feed_url):
        return "User-agent: *\nDisallow: /feed"

    monkeypatch.setattr(NewsIngestService, "_fetch_robots_txt", fake_fetch_robots_txt, raising=False)

    reason = await service._check_robots_policy(source)

    assert reason == "robots_txt_block"


def test_sanitizer_detects_full_article(monkeypatch):
    from services import news_legal_sanitizer

    events = []

    def fake_warning(event_name, **kwargs):
        events.append({"event": event_name, **kwargs})

    monkeypatch.setattr(news_legal_sanitizer.logger, "warning", fake_warning)

    normalized = NormalizedNewsItem(
        title="Full Article",
        url="https://example.com/full",
        snippet="",
        source="Example",
        published_at=datetime.now(timezone.utc),
        raw_metadata={},
    )
    long_html = "<p>" + ("Sentence. " * 200) + "</p>"

    sanitize_ingested_entry({"content": long_html}, normalized, {"license": "x"})

    assert any(event["event"] == "news_ingest_full_article_detected" for event in events)


def test_sanitizer_strips_content_and_truncates_snippet():
    normalized = NormalizedNewsItem(
        title="Snippet Title",
        url="https://example.com/item",
        snippet="<div>" + ("word " * 500) + "</div>",
        source="Example",
        published_at=datetime.now(timezone.utc),
        raw_metadata={},
    )
    sanitized = sanitize_ingested_entry(
        {
            "content": [{"value": "long text"}],
            "media_content": [{"url": "https://example.com/image.jpg"}],
        },
        normalized,
        {"license": "x"},
    )

    assert len(sanitized.snippet) <= 360
    assert set(sanitized.raw_metadata.keys()) == {"title", "snippet", "url", "source", "published_at"}
    assert sanitized.raw_metadata["snippet"] == sanitized.snippet

