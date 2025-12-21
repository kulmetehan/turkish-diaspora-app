from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from app.core.logging import get_logger

logger = get_logger()


class BaseScraperService:
    """
    Shared base class for HTTP scraping services.
    
    Provides common HTTP client management, retry logic, and concurrency control
    that can be reused by both EventScraperService and NewsScraperService.
    """

    def __init__(
        self,
        *,
        user_agent: str,
        timeout_s: int = 15,
        max_concurrency: int = 5,
        max_retries: int = 2,
    ) -> None:
        """
        Initialize base scraper service.
        
        Args:
            user_agent: User-Agent string for HTTP requests
            timeout_s: Request timeout in seconds
            max_concurrency: Maximum concurrent requests (semaphore limit)
            max_retries: Maximum retry attempts for failed requests
        """
        self.user_agent = user_agent
        self.timeout_s = timeout_s
        self.max_concurrency = max(1, max_concurrency)
        self.max_retries = max(0, max_retries)
        self._client: Optional[httpx.AsyncClient] = None
        self._sem = asyncio.Semaphore(self.max_concurrency)

    async def __aenter__(self) -> "BaseScraperService":
        """Initialize HTTP client on context entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout_s,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Close HTTP client on context exit."""
        if self._client:
            await self._client.aclose()

    async def fetch(self, url: str) -> httpx.Response:
        """
        Fetch URL with retry logic and concurrency control.
        
        Args:
            url: URL to fetch
            
        Returns:
            httpx.Response object
            
        Raises:
            httpx.HTTPError: If all retry attempts fail
        """
        if self._client is None:
            raise RuntimeError(f"{self.__class__.__name__} HTTP client not initialized")
        
        attempt = 0
        delay = 1.0
        last_exc: Optional[Exception] = None
        
        while attempt <= self.max_retries:
            try:
                async with self._sem:
                    response = await self._client.get(url)
                response.raise_for_status()
                return response
            except Exception as exc:
                last_exc = exc
                attempt += 1
                if attempt > self.max_retries:
                    break
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10)
        
        assert last_exc is not None
        raise last_exc

    async def fetch_html(self, url: str) -> str:
        """
        Fetch URL and return response text (HTML).
        
        Convenience method that calls fetch() and returns .text.
        
        Args:
            url: URL to fetch
            
        Returns:
            Response text content
        """
        response = await self.fetch(url)
        return response.text
















