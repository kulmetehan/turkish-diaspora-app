from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from app.models.news_extraction import ExtractedNewsItem, ExtractedNewsPayload
from services.openai_service import OpenAIService


def _build_system_prompt(scrape_timestamp: Optional[datetime] = None) -> str:
    scrape_date_hint = ""
    if scrape_timestamp:
        scrape_date_str = scrape_timestamp.strftime("%Y-%m-%d")
        scrape_date_hint = (
            f"\nIMPORTANT: This page was scraped on {scrape_date_str}. "
            f"The publication date (published_at) should NOT be later than this date. "
            f"If you see dates in the future (like event dates, election dates, etc.), "
            f"those are NOT publication dates - ignore them and use the actual article publication date instead."
        )
    
    return (
        "You extract structured news article information from raw HTML snippets. "
        "Return ONLY valid JSON with the schema:\n"
        "{\n"
        '  "articles": [\n'
        "    {\n"
        '      "title": string (required),\n'
        '      "snippet": string | null (first 200 words recommended),\n'
        '      "published_at": ISO 8601 datetime (required, use Europe/Amsterdam if ambiguous),\n'
        '      "url": string (required, full article URL),\n'
        '      "image_url": string | null (featured image URL if available),\n'
        '      "source": string (required, source name like "Turkse Media")\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Extract the latest 3 news articles from the HTML. "
        "Ignore navigation, ads, footer content, or non-article content. "
        "Focus on main article listings or recent posts. "
        "If the page contains article listings, extract the most recent ones. "
        "For published_at, parse dates carefully:\n"
        "- Use the ACTUAL publication date of the article (when it was published on the website)\n"
        "- DO NOT use event dates mentioned in the article (e.g., election dates, meeting dates, future events)\n"
        "- DO NOT use dates that are in the future relative to when the article was published\n"
        "- Look for publication date metadata (e.g., <time>, <meta property='article:published_time'>, date classes)\n"
        "- If no clear publication date is found, use a date that makes sense (recent past, not future)\n"
        f"{scrape_date_hint}"
        "If multiple articles are present, include up to 3 most recent ones. "
        "Ensure URLs are absolute (include http:// or https://). "
        "Extract snippet from article summary, excerpt, or first paragraph (max 200 words)."
    )


class NewsExtractionService:
    """Service for extracting news articles from HTML using AI."""

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        openai_client: Optional[OpenAIService] = None,
    ) -> None:
        """
        Initialize news extraction service.
        
        Args:
            model: Optional OpenAI model override
            openai_client: Optional pre-initialized OpenAIService instance
        """
        self._openai = openai_client or OpenAIService(model=model)

    def _build_user_prompt(
        self,
        *,
        html: str,
        source_key: str,
        page_url: str,
    ) -> str:
        """
        Build user prompt for AI extraction.
        
        Args:
            html: HTML content to extract from
            source_key: Source identifier (e.g., 'scrape_turksemedia_nl')
            page_url: URL of the page being processed
            
        Returns:
            Formatted user prompt string
        """
        return (
            f"Source key: {source_key}\n"
            f"Page URL: {page_url}\n"
            "HTML snippet:\n"
            f"{html.strip()}\n"
        )

    def extract_news_from_html(
        self,
        *,
        html: str,
        source_key: str,
        page_url: str,
        scrape_timestamp: Optional[datetime] = None,
    ) -> Tuple[ExtractedNewsPayload, Dict[str, Any]]:
        """
        Extract news articles from HTML using AI.
        
        Args:
            html: HTML content to extract from
            source_key: Source identifier (e.g., 'scrape_turksemedia_nl')
            page_url: URL of the page being processed
            scrape_timestamp: Optional timestamp when the page was scraped (for date validation)
            
        Returns:
            Tuple of (ExtractedNewsPayload, metadata dict)
            
        Raises:
            ValueError: If html is empty
        """
        if not html or not html.strip():
            raise ValueError("html cannot be empty")

        system_prompt = _build_system_prompt(scrape_timestamp=scrape_timestamp)
        user_prompt = self._build_user_prompt(
            html=html,
            source_key=source_key,
            page_url=page_url,
        )
        parsed, meta = self._openai.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ExtractedNewsPayload,
            action_type="news.extract_from_html",
            location_id=None,
            news_id=None,
            event_raw_id=None,
        )
        return parsed, meta

    @staticmethod
    def validate_and_fix_published_at(
        article: ExtractedNewsItem,
        scrape_timestamp: datetime,
        max_future_days: int = 7,
    ) -> datetime:
        """
        Validate and fix published_at date if it's unreasonably far in the future.
        
        If the extracted published_at is more than max_future_days in the future
        relative to scrape_timestamp, use scrape_timestamp as fallback.
        
        Args:
            article: ExtractedNewsItem with published_at to validate
            scrape_timestamp: Timestamp when the page was scraped
            max_future_days: Maximum allowed days in the future (default: 7)
            
        Returns:
            Corrected published_at datetime
        """
        published_at = article.published_at
        
        # Ensure both datetimes are timezone-aware
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        if scrape_timestamp.tzinfo is None:
            scrape_timestamp = scrape_timestamp.replace(tzinfo=timezone.utc)
        
        # Calculate difference
        time_diff = published_at - scrape_timestamp
        
        # If published_at is more than max_future_days in the future, use scrape_timestamp
        if time_diff > timedelta(days=max_future_days):
            return scrape_timestamp
        
        return published_at


















