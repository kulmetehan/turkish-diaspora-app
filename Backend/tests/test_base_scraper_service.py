from __future__ import annotations

import pytest

import httpx

from services.base_scraper_service import BaseScraperService


@pytest.mark.asyncio
async def test_base_scraper_context_manager():
    """Test that BaseScraperService works as async context manager."""
    async with BaseScraperService(user_agent="test-agent/1.0") as service:
        assert service._client is not None
        assert isinstance(service._client, httpx.AsyncClient)
    
    # Client should be closed after context exit
    assert service._client is None or service._client.is_closed


@pytest.mark.asyncio
async def test_base_scraper_fetch_requires_context():
    """Test that fetch() raises error if client not initialized."""
    service = BaseScraperService(user_agent="test-agent/1.0")
    with pytest.raises(RuntimeError, match="not initialized"):
        await service.fetch("https://example.com")


@pytest.mark.asyncio
async def test_base_scraper_fetch_html(httpx_mock):
    """Test fetch_html convenience method."""
    httpx_mock.add_response(
        url="https://example.com",
        text="<html>Test</html>",
    )
    
    async with BaseScraperService(user_agent="test-agent/1.0") as service:
        html = await service.fetch_html("https://example.com")
        assert html == "<html>Test</html>"


@pytest.mark.asyncio
async def test_base_scraper_retry_logic(httpx_mock):
    """Test that retry logic works on failures."""
    # First two requests fail, third succeeds
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(text="Success")
    
    async with BaseScraperService(
        user_agent="test-agent/1.0",
        max_retries=2,
    ) as service:
        response = await service.fetch("https://example.com")
        assert response.text == "Success"
        assert len(httpx_mock.get_requests()) == 3


@pytest.mark.asyncio
async def test_base_scraper_retry_exhausted(httpx_mock):
    """Test that exception is raised when retries exhausted."""
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    
    async with BaseScraperService(
        user_agent="test-agent/1.0",
        max_retries=2,
    ) as service:
        with pytest.raises(Exception):
            await service.fetch("https://example.com")


