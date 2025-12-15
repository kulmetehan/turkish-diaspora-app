from __future__ import annotations

import hashlib
from typing import List, Optional

from app.core.logging import get_logger
from app.models.news_pages_raw import NewsPageRawCreate
from app.models.news_sources import NewsSource
from services.base_scraper_service import BaseScraperService
from services.news_pages_raw_service import insert_news_page_raw

logger = get_logger()


class NewsScraperService(BaseScraperService):
    """Service for scraping Turkish-Dutch news websites."""

    def __init__(
        self,
        *,
        timeout_s: int = 15,
        max_concurrency: int = 5,
        max_retries: int = 2,
    ) -> None:
        """
        Initialize news scraper service.
        
        Args:
            timeout_s: Request timeout in seconds
            max_concurrency: Maximum concurrent requests
            max_retries: Maximum retry attempts
        """
        super().__init__(
            user_agent="tda-news-scraper/1.0",
            timeout_s=timeout_s,
            max_concurrency=max_concurrency,
            max_retries=max_retries,
        )

    @staticmethod
    def _compute_content_hash(
        *,
        source_key: str,
        page_url: str,
        response_body: str,
    ) -> str:
        """
        Compute SHA1 hash for deduplication.
        
        Args:
            source_key: News source key identifier
            page_url: URL of the page
            response_body: HTML response body
            
        Returns:
            40-character SHA1 hex string
        """
        parts = [
            source_key.strip().lower(),
            page_url.strip().lower(),
            response_body.strip(),
        ]
        joined = "|".join(parts)
        return hashlib.sha1(joined.encode("utf-8", "ignore")).hexdigest()

    async def scrape_turkish_news_site(
        self,
        source: NewsSource,
    ) -> List[NewsPageRawCreate]:
        """
        Scrape a Turkish-Dutch news site and return raw page records.
        
        This method fetches the homepage/main page and stores it as raw HTML
        for later AI extraction. The AI extractor will identify and extract
        the latest 3 articles from the HTML.
        
        Args:
            source: NewsSource configuration
            
        Returns:
            List of NewsPageRawCreate records (typically 1 per source)
        """
        url = source.url
        source_key = source.key

        try:
            logger.info(
                "news_scraper_fetching",
                source_key=source_key,
                url=url,
            )
            response = await self.fetch(url)
            response_body = response.text
            http_status = response.status_code
            response_headers = dict(response.headers)

            content_hash = self._compute_content_hash(
                source_key=source_key,
                page_url=url,
                response_body=response_body,
            )

            page_raw = NewsPageRawCreate(
                news_source_key=source_key,
                page_url=url,
                http_status=http_status,
                response_headers=response_headers,
                response_body=response_body,
                content_hash=content_hash,
                processing_state="pending",
                processing_errors=None,
            )

            logger.info(
                "news_scraper_fetched",
                source_key=source_key,
                url=url,
                content_length=len(response_body),
                http_status=http_status,
            )

            return [page_raw]

        except Exception as exc:
            logger.warning(
                "news_scraper_fetch_failed",
                source_key=source_key,
                url=url,
                error=str(exc),
            )
            # Return error record for tracking
            content_hash = self._compute_content_hash(
                source_key=source_key,
                page_url=url,
                response_body="",
            )
            error_page = NewsPageRawCreate(
                news_source_key=source_key,
                page_url=url,
                http_status=None,
                response_headers={},
                response_body="",
                content_hash=content_hash,
                processing_state="error_fetch",
                processing_errors={"error": str(exc), "type": type(exc).__name__},
            )
            return [error_page]

    async def scrape_and_store(
        self,
        source: NewsSource,
    ) -> int:
        """
        Scrape a source and store raw pages in database.
        
        Convenience method that combines scraping and storage.
        
        Args:
            source: NewsSource configuration
            
        Returns:
            Number of pages successfully inserted
        """
        pages = await self.scrape_turkish_news_site(source)
        inserted = 0
        for page in pages:
            page_id = await insert_news_page_raw(page)
            if page_id is not None:
                inserted += 1
        return inserted







