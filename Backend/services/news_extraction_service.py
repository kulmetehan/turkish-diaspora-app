from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from app.models.news_extraction import ExtractedNewsPayload
from services.openai_service import OpenAIService


def _build_system_prompt() -> str:
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
        "For published_at, parse dates carefully - use the actual publication date from the article, not the current date. "
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
        self._system_prompt = _build_system_prompt()

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
    ) -> Tuple[ExtractedNewsPayload, Dict[str, Any]]:
        """
        Extract news articles from HTML using AI.
        
        Args:
            html: HTML content to extract from
            source_key: Source identifier (e.g., 'scrape_turksemedia_nl')
            page_url: URL of the page being processed
            
        Returns:
            Tuple of (ExtractedNewsPayload, metadata dict)
            
        Raises:
            ValueError: If html is empty
        """
        if not html or not html.strip():
            raise ValueError("html cannot be empty")

        user_prompt = self._build_user_prompt(
            html=html,
            source_key=source_key,
            page_url=page_url,
        )
        parsed, meta = self._openai.generate_json(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            response_model=ExtractedNewsPayload,
            action_type="news.extract_from_html",
            location_id=None,
            news_id=None,
            event_raw_id=None,
        )
        return parsed, meta


