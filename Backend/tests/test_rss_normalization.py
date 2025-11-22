from __future__ import annotations

import feedparser

from app.models.news_sources import NewsSource
from services.rss_normalization import normalize_feed_entries


def _make_dummy_source() -> NewsSource:
    return NewsSource(
        name="dummy",
        url="https://example.com/feed",
        language="nl",
        category="nl_local",
        license="test-license",
        redistribution_allowed=True,
        robots_policy="ignore",
        raw={},
    )


def test_rss_normalization_happy_path():
    xml = """
    <rss version="2.0">
      <channel>
        <title>Example RSS</title>
        <item>
          <title>First item</title>
          <link>https://example.com/1</link>
          <description><![CDATA[<p>Hello world</p>]]></description>
          <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """
    parsed = feedparser.parse(xml)
    source = _make_dummy_source()

    items, errors = normalize_feed_entries(parsed, source)

    assert errors == []
    assert len(items) == 1
    item = items[0]
    assert item.title == "First item"
    assert item.url == "https://example.com/1"
    assert "Hello world" in item.snippet
    assert item.source == "dummy"
    assert item.published_at.tzinfo is not None


def test_atom_normalization_happy_path():
    xml = """
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Example Atom</title>
      <entry>
        <title>Atom entry</title>
        <id>tag:example.com,2024:1</id>
        <updated>2024-01-01T10:00:00Z</updated>
        <summary>Summary text</summary>
        <link rel="alternate" href="https://example.com/atom/1" />
      </entry>
    </feed>
    """
    parsed = feedparser.parse(xml)
    source = _make_dummy_source()

    items, errors = normalize_feed_entries(parsed, source)

    assert errors == []
    assert len(items) == 1
    item = items[0]
    assert item.title == "Atom entry"
    assert item.url == "https://example.com/atom/1"
    assert "Summary text" in item.snippet


def test_missing_fields_receive_defaults():
    xml = """
    <rss version="2.0">
      <channel>
        <title>Example RSS</title>
        <item>
          <link>https://example.com/item-without-title</link>
        </item>
      </channel>
    </rss>
    """
    parsed = feedparser.parse(xml)
    source = _make_dummy_source()

    items, errors = normalize_feed_entries(parsed, source)

    assert errors == []
    assert len(items) == 1
    item = items[0]
    assert item.title == "Untitled"
    assert item.url == "https://example.com/item-without-title"
    assert item.snippet == "No summary"


def test_corrupt_entry_yields_error_not_exception():
    parsed_feed = {
        "version": "rss20",
        "entries": [object()],
    }
    source = _make_dummy_source()

    items, errors = normalize_feed_entries(parsed_feed, source)

    assert items == []
    assert len(errors) == 1
    assert "object has no attribute" in str(errors[0]).lower()

