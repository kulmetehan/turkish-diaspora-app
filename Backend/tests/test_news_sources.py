import textwrap
from pathlib import Path

import pytest

from app.models.news_sources import (
    ALLOWED_NEWS_CATEGORIES,
    clear_news_sources_cache,
    get_all_news_sources,
)


def _write_config(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_news_sources_cache()
    yield
    clear_news_sources_cache()


def test_news_sources_happy_path(tmp_path):
    cfg = tmp_path / "news_sources.yml"
    _write_config(
        cfg,
        """
        version: 1
        sources:
          - name: "Sample Feed"
            url: "https://example.com/rss"
            language: "nl"
            category: "nl_local"
        """,
    )

    sources = get_all_news_sources(path=cfg)
    assert len(sources) == 1
    src = sources[0]
    assert src.name == "Sample Feed"
    assert src.url == "https://example.com/rss"
    assert src.language == "nl"
    assert src.category in ALLOWED_NEWS_CATEGORIES


def test_news_sources_skips_invalid_entries(tmp_path):
    cfg = tmp_path / "news_sources.yml"
    _write_config(
        cfg,
        """
        version: 1
        sources:
          - name: "Missing Url"
            language: "nl"
            category: "nl_local"
          - name: "Bad Category"
            url: "https://example.com/rss"
            language: "nl"
            category: "unknown"
          - name: "Valid"
            url: "https://valid.example/rss"
            language: "en"
            category: "international"
        """,
    )

    sources = get_all_news_sources(path=cfg)
    assert len(sources) == 1
    assert sources[0].name == "Valid"
    assert sources[0].category == "international"


def test_news_sources_invalid_sources_type(tmp_path):
    cfg = tmp_path / "news_sources.yml"
    _write_config(
        cfg,
        """
        version: 1
        sources:
          name: "should be list"
        """,
    )

    sources = get_all_news_sources(path=cfg)
    assert sources == []


def test_news_source_refresh_minutes_overrides(tmp_path):
    cfg = tmp_path / "news_sources.yml"
    _write_config(
        cfg,
        """
        version: 1
        defaults:
          refresh_minutes: 45
        sources:
          - name: "With Override"
            url: "https://override.example/rss"
            language: "nl"
            category: "nl_local"
            refresh_minutes: 10
          - name: "Uses Default"
            url: "https://default.example/rss"
            language: "nl"
            category: "nl_local"
        """,
    )

    sources = get_all_news_sources(path=cfg)
    assert len(sources) == 2
    override, default = sources
    assert override.refresh_minutes == 10
    assert default.refresh_minutes == 45


def test_news_source_region_and_refresh_fallback(tmp_path):
    cfg = tmp_path / "news_sources.yml"
    _write_config(
        cfg,
        """
        version: 1
        sources:
          - name: "No Defaults"
            url: "https://nodefault.example/rss"
            language: "nl"
            category: "nl_local"
            region: "rotterdam"
        """,
    )

    sources = get_all_news_sources(path=cfg)
    assert len(sources) == 1
    src = sources[0]
    assert src.region == "rotterdam"
    assert src.refresh_minutes == 30

