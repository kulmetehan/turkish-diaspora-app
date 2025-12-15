"""
X (Twitter) trending topics scraper.

This scraper fetches trending topics by scraping X/Twitter pages instead of
using the official API (which requires paid tier access - Basic/Pro/Enterprise).

**Data Sources (in order of attempt):**

1. **Trends24.in** (Primary - Third-party aggregator):
   - URL: `https://trends24.in/{country}/`
   - Third-party service that aggregates X trending topics
   - **Works without authentication** - publicly accessible
   - Returns HTML with trending topics in timeline format
   - Based on: Public trends24.in website structure
   - **This is the recommended source** as it avoids X's anti-scraping measures

2. **Internal API Endpoint** (`/i/api/2/guide.json`):
   - URL: `https://twitter.com/i/api/2/guide.json?count=20&candidate_source=trending&woeid={woeid}`
   - This is the internal API endpoint used by X's web client
   - **Likely requires authentication** (cookies/tokens) - may return 403
   - Returns JSON with trending topics in X's internal format
   - Based on: Reverse engineering of X web client network requests
   - **Note: Usually blocked by X anti-scraping**

3. **Public Explore Page** (`/explore/tabs/trending`):
   - URL: `https://twitter.com/explore/tabs/trending`
   - Public HTML page that displays trending topics
   - **May work without auth** but requires HTML parsing
   - X may use JavaScript to load content dynamically (making scraping harder)
   - Based on: Public X explore page structure
   - **Note: Content loaded via JavaScript, difficult to scrape**

**Anti-Scraping Considerations:**
- X may implement rate limiting (429 responses)
- X may block requests without proper authentication (403 responses)
- X may use JavaScript to dynamically load content (requires browser automation)
- X may detect automated requests and block them

**Future Alternatives:**
- Third-party APIs (Trendstools, Apify, TrendsonX)
- RSS feeds (if available)
- Browser automation (Selenium/Playwright) - more complex but more reliable

**Rate Limiting:**
- Uses caching (3 minutes) to minimize requests
- Respectful delays between requests
- Single concurrent request (max_concurrency=1)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from app.core.logging import get_logger
from services.base_scraper_service import BaseScraperService

logger = get_logger().bind(module="news_trending_x_scraper")

_DEFAULT_CACHE_TTL_SECONDS = 180  # 3 minutes cache
_cache: dict[str, dict[str, object]] = {}


@dataclass(frozen=True)
class TrendingTopic:
    title: str
    url: str
    description: Optional[str]
    published_at: datetime | None


@dataclass
class TrendingResult:
    """Result from trending topics fetch, including unavailability reason if applicable."""
    topics: List[TrendingTopic]
    unavailable_reason: Optional[str] = None


def _resolve_woeid(country: str) -> str:
    """Resolve country code to WOEID (Where On Earth ID) for location-based trends."""
    woeids = {
        "nl": "23424909",  # Netherlands
        "tr": "23424969",  # Turkey
        "us": "23424977",  # United States
        "uk": "23424975",  # United Kingdom
        "de": "23424829",  # Germany
    }
    return woeids.get(country.lower(), "1")  # Default to worldwide (WOEID 1)


class XTrendingScraper(BaseScraperService):
    """Scraper for X/Twitter trending topics."""

    def __init__(
        self,
        *,
        timeout_s: int = 20,
        max_concurrency: int = 1,  # Conservative for scraping
        max_retries: int = 2,
    ) -> None:
        """
        Initialize X trending scraper.
        
        Args:
            timeout_s: Request timeout in seconds
            max_concurrency: Maximum concurrent requests (set to 1 for scraping)
            max_retries: Maximum retry attempts
        """
        super().__init__(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            timeout_s=timeout_s,
            max_concurrency=max_concurrency,
            max_retries=max_retries,
        )

    async def scrape_trending_topics(
        self,
        country: str = "nl",
        limit: int = 20,
    ) -> TrendingResult:
        """
        Scrape trending topics from X/Twitter explore page.
        
        Args:
            country: Country code (e.g., "nl", "tr")
            limit: Maximum number of topics to return
            
        Returns:
            TrendingResult with topics or unavailable_reason
        """
        woeid = _resolve_woeid(country)
        
        # Try to get cached result
        cache_key = f"{woeid}_{limit}"
        now = time.time()
        bucket = _cache.get(cache_key, {})
        
        if bucket.get("expires_at", 0.0) > now:
            cached_result = bucket.get("result")
            if cached_result:
                logger.info("x_trending_scraper_cache_hit", country=country, woeid=woeid)
                return cached_result
        
        # Scrape trending page
        # Strategy: Try multiple endpoints in order of likelihood to work
        # 1. Internal API endpoint (used by X web client) - likely requires auth
        # 2. Public explore page HTML - may work but needs parsing
        # 3. Alternative third-party sources (future)
        
        # Map country codes to trends24.in country paths
        country_map = {
            "nl": "netherlands",
            "tr": "turkey",
            "us": "united-states",
            "uk": "united-kingdom",
            "de": "germany",
        }
        trends24_country = country_map.get(country.lower(), "netherlands")
        
        strategies = [
            {
                "name": "trends24_in",
                "url": f"https://trends24.in/{trends24_country}/",
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                "parse_method": "trends24_html",
            },
            {
                "name": "internal_api",
                "url": f"https://twitter.com/i/api/2/guide.json?count=20&candidate_source=trending&woeid={woeid}",
                "headers": {
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://twitter.com/explore/tabs/trending",
                },
                "parse_method": "json",
            },
            {
                "name": "public_explore_page",
                "url": f"https://twitter.com/explore/tabs/trending",
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                "parse_method": "html",
            },
        ]
        
        last_error = None
        for strategy in strategies:
            try:
                url = strategy["url"]
                headers = strategy["headers"]
                parse_method = strategy["parse_method"]
                
                logger.info(
                    "x_trending_scraper_trying_strategy",
                    strategy=strategy["name"],
                    country=country,
                    woeid=woeid,
                    url=url,
                )
                
                if self._client is None:
                    raise RuntimeError("Scraper client not initialized")
                
                response = await self._client.get(url, headers=headers)
            
                # Check if we got blocked or rate limited
                if response.status_code == 403:
                    logger.warning(
                        "x_trending_scraper_blocked",
                        strategy=strategy["name"],
                        status_code=403,
                        response_preview=response.text[:200],
                    )
                    last_error = "x_trending_unavailable_scraper_blocked"
                    continue  # Try next strategy
                
                if response.status_code == 429:
                    logger.warning(
                        "x_trending_scraper_rate_limited",
                        strategy=strategy["name"],
                        status_code=429,
                    )
                    last_error = "x_trending_unavailable_rate_limited"
                    continue  # Try next strategy
                
                if response.status_code != 200:
                    logger.warning(
                        "x_trending_scraper_unexpected_status",
                        strategy=strategy["name"],
                        status_code=response.status_code,
                        response_preview=response.text[:200],
                    )
                    last_error = f"x_trending_unavailable_http_{response.status_code}"
                    continue  # Try next strategy
                
                # Parse response based on strategy
                if parse_method == "json":
                    try:
                        data = response.json()
                        topics = self._parse_api_response(data, limit)
                        if topics:
                            logger.info(
                                "x_trending_scraper_success",
                                strategy=strategy["name"],
                                topics_count=len(topics),
                            )
                            result = TrendingResult(topics=topics)
                            # Cache the result
                            _cache[cache_key] = {
                                "result": result,
                                "expires_at": now + _DEFAULT_CACHE_TTL_SECONDS,
                            }
                            return result
                    except (ValueError, KeyError) as e:
                        logger.warning(
                            "x_trending_scraper_json_parse_failed",
                            strategy=strategy["name"],
                            error=str(e),
                            response_preview=response.text[:500],
                        )
                        continue  # Try next strategy
                
                elif parse_method == "trends24_html":
                    html = response.text
                    topics = self._parse_trends24_html(html, limit)
                    if topics:
                        logger.info(
                            "x_trending_scraper_success",
                            strategy=strategy["name"],
                            topics_count=len(topics),
                        )
                        result = TrendingResult(topics=topics)
                        # Cache the result
                        _cache[cache_key] = {
                            "result": result,
                            "expires_at": now + _DEFAULT_CACHE_TTL_SECONDS,
                        }
                        return result
                    else:
                        logger.warning(
                            "x_trending_scraper_trends24_no_topics",
                            strategy=strategy["name"],
                            html_length=len(html),
                        )
                        continue  # Try next strategy
                
                elif parse_method == "html":
                    html = response.text
                    topics = self._parse_html_response(html, limit)
                    if topics:
                        logger.info(
                            "x_trending_scraper_success",
                            strategy=strategy["name"],
                            topics_count=len(topics),
                        )
                        result = TrendingResult(topics=topics)
                        # Cache the result
                        _cache[cache_key] = {
                            "result": result,
                            "expires_at": now + _DEFAULT_CACHE_TTL_SECONDS,
                        }
                        return result
                    else:
                        logger.warning(
                            "x_trending_scraper_html_no_topics",
                            strategy=strategy["name"],
                            html_length=len(html),
                        )
                        continue  # Try next strategy
                        
            except Exception as exc:
                logger.warning(
                    "x_trending_scraper_strategy_error",
                    strategy=strategy["name"],
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                last_error = f"x_trending_unavailable_scraper_error_{strategy['name']}"
                continue  # Try next strategy
        
        # All strategies failed
        logger.warning(
            "x_trending_scraper_all_strategies_failed",
            country=country,
            woeid=woeid,
            last_error=last_error,
        )
            
        # If we get here, all strategies failed
        return TrendingResult(
            topics=[],
            unavailable_reason=last_error or "x_trending_unavailable_scraper_all_failed",
        )

    def _parse_api_response(self, data: dict, limit: int) -> List[TrendingTopic]:
        """
        Parse X API-like JSON response.
        
        Args:
            data: JSON response data
            limit: Maximum topics to return
            
        Returns:
            List of TrendingTopic objects
        """
        topics: List[TrendingTopic] = []
        
        try:
            # Try to extract from various possible response formats
            # X API v2 format: {"data": [{"trend_name": "...", ...}]}
            if "data" in data:
                trends = data["data"]
            elif "timeline" in data and "instructions" in data["timeline"]:
                # Alternative format from guide.json
                trends = self._extract_from_timeline(data.get("timeline", {}))
            else:
                trends = []
            
            for trend in trends[:limit]:
                if isinstance(trend, dict):
                    name = trend.get("trend_name") or trend.get("name") or trend.get("query")
                    if name:
                        url = trend.get("url") or f"https://twitter.com/search?q={quote(name)}"
                        topics.append(TrendingTopic(
                            title=str(name).strip(),
                            url=url,
                            description=None,
                            published_at=datetime.now(timezone.utc),
                        ))
        except Exception as exc:
            logger.warning("x_trending_scraper_parse_error", error=str(exc))
        
        return topics

    def _extract_from_timeline(self, timeline: dict) -> List[dict]:
        """Extract trending topics from X timeline format."""
        trends = []
        try:
            instructions = timeline.get("instructions", [])
            for instruction in instructions:
                if instruction.get("type") == "TimelineAddEntries":
                    entries = instruction.get("entries", [])
                    for entry in entries:
                        content = entry.get("content", {})
                        if content.get("entryType") == "TimelineTimelineItem":
                            item = content.get("itemContent", {})
                            trend = item.get("trend", {})
                            if trend:
                                trends.append(trend)
        except Exception:
            pass
        return trends

    def _parse_trends24_html(self, html: str, limit: int) -> List[TrendingTopic]:
        """
        Parse trends24.in HTML response.
        
        Based on the trends24.in structure:
        - Topics are shown in timeline sections with timestamps
        - Each section has a numbered list (1. TopicName, 2. TopicName, etc.)
        - Topics can be hashtags (#topic) or plain text
        - The most recent timeline section contains current trends
        
        Args:
            html: HTML content from trends24.in
            limit: Maximum topics to return
            
        Returns:
            List of TrendingTopic objects
        """
        topics: List[TrendingTopic] = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Strategy 1: Look for the most recent timeline section
            # trends24.in shows trends in sections like "Mon Dec 15 2025 16:57:11 GMT+0000"
            # Each section has an ordered list (<ol>) with trending topics
            
            # Find all timeline sections (they typically have timestamps as headers)
            timeline_sections = soup.find_all(['div', 'section'], class_=re.compile(r'timeline|trend', re.I))
            
            # If no specific sections found, look for ordered lists directly
            if not timeline_sections:
                # Look for the first <ol> or <ul> that contains numbered items
                lists = soup.find_all(['ol', 'ul'])
                for list_elem in lists:
                    items = list_elem.find_all('li', limit=limit * 2)
                    for item in items:
                        text = item.get_text(strip=True)
                        # Extract topic name (remove leading number like "1. " or "#1 ")
                        # Pattern: "1. TopicName" or "#1 TopicName" or just "TopicName"
                        topic_match = re.match(r'^#?\d+\.\s*(.+)$', text)
                        if topic_match:
                            topic = topic_match.group(1).strip()
                        else:
                            topic = text.strip()
                        
                        if topic and len(topic) > 1:
                            # Clean topic name: remove tweet counts (e.g., "14K", "1M", "405K")
                            topic_clean = re.sub(r'\d+[KMkm]$', '', topic).strip()
                            if not topic_clean:
                                topic_clean = topic  # Fallback if cleaning removed everything
                            
                            # Skip common non-topic words
                            skip_words = ["trending", "topics", "hashtags", "twitter", "x", "netherlands", "turkey", "view all"]
                            if not any(word in topic_clean.lower() for word in skip_words):
                                topics.append(TrendingTopic(
                                    title=topic_clean,
                                    url=f"https://twitter.com/search?q={quote(topic_clean)}",
                                    description=None,
                                    published_at=datetime.now(timezone.utc),
                                ))
                                if len(topics) >= limit:
                                    break
                    if len(topics) >= limit:
                        break
            else:
                # Parse timeline sections
                for section in timeline_sections[:1]:  # Only use the first (most recent) section
                    lists = section.find_all(['ol', 'ul'])
                    for list_elem in lists:
                        items = list_elem.find_all('li', limit=limit * 2)
                        for item in items:
                            text = item.get_text(strip=True)
                            # Extract topic name
                            topic_match = re.match(r'^#?\d+\.\s*(.+)$', text)
                            if topic_match:
                                topic = topic_match.group(1).strip()
                            else:
                                topic = text.strip()
                            
                            if topic and len(topic) > 1:
                                # Clean topic name: remove tweet counts (e.g., "14K", "1M", "405K")
                                # Pattern: topic name followed by numbers and K/M (e.g., "Joden14K" -> "Joden")
                                topic_clean = re.sub(r'\d+[KMkm]$', '', topic).strip()
                                if not topic_clean:
                                    topic_clean = topic  # Fallback if cleaning removed everything
                                
                                skip_words = ["trending", "topics", "hashtags", "twitter", "x", "netherlands", "turkey", "view all"]
                                if not any(word in topic_clean.lower() for word in skip_words):
                                    topics.append(TrendingTopic(
                                        title=topic_clean,
                                        url=f"https://twitter.com/search?q={quote(topic_clean)}",
                                        description=None,
                                        published_at=datetime.now(timezone.utc),
                                    ))
                                    if len(topics) >= limit:
                                        break
                        if len(topics) >= limit:
                            break
                    if len(topics) >= limit:
                        break
            
            # Strategy 2: Fallback to regex if BeautifulSoup didn't find anything
            if not topics:
                # Look for numbered list patterns in raw HTML
                numbered_pattern = r'<li[^>]*>\s*\d+\.\s*([^<]+)</li>'
                matches = re.findall(numbered_pattern, html, re.IGNORECASE)
                
                seen = set()
                for match in matches[:limit * 2]:
                    topic = match.strip()
                    if topic and len(topic) > 1 and topic.lower() not in seen:
                        seen.add(topic.lower())
                        # Clean topic name: remove tweet counts
                        topic_clean = re.sub(r'\d+[KMkm]$', '', topic).strip()
                        if not topic_clean:
                            topic_clean = topic
                        
                        skip_words = ["trending", "topics", "hashtags", "twitter", "x", "netherlands", "turkey"]
                        if not any(word in topic_clean.lower() for word in skip_words):
                            topics.append(TrendingTopic(
                                title=topic_clean,
                                url=f"https://twitter.com/search?q={quote(topic_clean)}",
                                description=None,
                                published_at=datetime.now(timezone.utc),
                            ))
                            if len(topics) >= limit:
                                break
                        
        except Exception as exc:
            logger.warning("x_trending_scraper_trends24_parse_error", error=str(exc), error_type=type(exc).__name__)
        
        return topics[:limit]  # Ensure we don't exceed limit

    def _parse_html_response(self, html: str, limit: int) -> List[TrendingTopic]:
        """
        Parse HTML response (fallback method for X pages).
        
        Args:
            html: HTML content
            limit: Maximum topics to return
            
        Returns:
            List of TrendingTopic objects
        """
        topics: List[TrendingTopic] = []
        
        try:
            # Try to find trending topics in HTML
            # This is a fallback and may need adjustment based on X's HTML structure
            # Look for common patterns like data-trend-name or similar attributes
            pattern = r'data-trend-name="([^"]+)"'
            matches = re.findall(pattern, html)
            
            for match in matches[:limit]:
                if match.strip():
                    topics.append(TrendingTopic(
                        title=match.strip(),
                        url=f"https://twitter.com/search?q={quote(match)}",
                        description=None,
                        published_at=datetime.now(timezone.utc),
                    ))
        except Exception as exc:
            logger.warning("x_trending_scraper_html_parse_error", error=str(exc))
        
        return topics


async def fetch_trending_topics_scraper(
    limit: int = 20,
    country: str = "nl",
) -> TrendingResult:
    """
    Fetch trending topics using scraper (fallback when API is unavailable).
    
    Args:
        limit: Maximum number of topics to return
        country: Country code (e.g., "nl", "tr")
        
    Returns:
        TrendingResult with topics or unavailable_reason
    """
    async with XTrendingScraper() as scraper:
        return await scraper.scrape_trending_topics(country=country, limit=limit)
