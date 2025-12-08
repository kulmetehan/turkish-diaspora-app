"""Tests for Google News service (Local/Origin feeds)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import feedparser
import httpx
import pytest

from services.news_google_service import fetch_google_news_for_city


@pytest.mark.asyncio
async def test_fetch_google_news_for_city_success(monkeypatch):
    """Test successful Google News fetch and normalization."""
    # Mock city config
    mock_city = MagicMock()
    mock_city.name = "Rotterdam"
    mock_city.google_news_query = "Rotterdam"

    with patch("services.news_google_service.get_city_by_key", return_value=mock_city):
        with patch("services.news_google_service.get_city_google_news_query", return_value="Rotterdam"):
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.text = """<?xml version="1.0"?>
                <rss version="2.0">
                    <channel>
                        <item>
                            <title>Test News</title>
                            <link>https://example.com/news</link>
                            <description>Test description</description>
                            <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                        </item>
                    </channel>
                </rss>
            """
            mock_response.raise_for_status = MagicMock()

            async def mock_get(*args, **kwargs):
                return mock_response

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
                mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()

                # Mock normalization
                from app.models.news_normalized import NormalizedNewsItem
                mock_normalized = NormalizedNewsItem(
                    title="Test News",
                    url="https://example.com/news",
                    snippet="Test description",
                    source="Google News – Rotterdam",
                    published_at=datetime.now(timezone.utc),
                    raw_metadata={},
                )

                with patch("services.news_google_service.normalize_feed_entries") as mock_norm:
                    mock_norm.return_value = ([mock_normalized], [])

                    items = await fetch_google_news_for_city(
                        country="nl",
                        city_key="rotterdam",
                        limit=10,
                    )

                    assert len(items) == 1
                    assert items[0].title == "Test News"
                    assert items[0].source == "Google News – Rotterdam"
                    assert items[0].url == "https://example.com/news"


@pytest.mark.asyncio
async def test_fetch_google_news_for_city_http_error(monkeypatch):
    """Test handling of HTTP errors."""
    mock_city = MagicMock()
    mock_city.name = "Rotterdam"

    with patch("services.news_google_service.get_city_by_key", return_value=mock_city):
        with patch("services.news_google_service.get_city_google_news_query", return_value="Rotterdam"):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=httpx.HTTPError("Connection error")
                )
                mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()

                items = await fetch_google_news_for_city(
                    country="nl",
                    city_key="rotterdam",
                    limit=10,
                )

                assert len(items) == 0  # Should return empty list on error


@pytest.mark.asyncio
async def test_fetch_google_news_for_city_invalid_country(monkeypatch):
    """Test handling of invalid country parameter."""
    items = await fetch_google_news_for_city(
        country="invalid",
        city_key="rotterdam",
        limit=10,
    )

    assert len(items) == 0


@pytest.mark.asyncio
async def test_fetch_google_news_for_city_city_not_found(monkeypatch):
    """Test handling of unknown city."""
    with patch("services.news_google_service.get_city_by_key", return_value=None):
        items = await fetch_google_news_for_city(
            country="nl",
            city_key="unknown_city",
            limit=10,
        )

        assert len(items) == 0


















