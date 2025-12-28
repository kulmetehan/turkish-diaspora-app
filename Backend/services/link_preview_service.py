# Backend/services/link_preview_service.py
from __future__ import annotations

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse, parse_qs
import httpx
from bs4 import BeautifulSoup
import re

from app.core.logging import logger


class Platform(str, Enum):
    MARKTPLAATS = "marktplaats"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    NEWS = "news"
    EVENT = "event"
    OTHER = "other"


@dataclass
class LinkPreview:
    url: str
    platform: Platform
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    preview_method: str = "fallback"  # 'oembed', 'opengraph', 'fallback'


class LinkPreviewService:
    """Service for generating link previews using oEmbed, Open Graph, or fallback."""
    
    def __init__(self):
        self.timeout = httpx.Timeout(10.0)
        # Use a real browser user agent to avoid Facebook blocking
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    
    def detect_platform(self, url: str) -> Platform:
        """Detect platform from URL."""
        url_lower = url.lower()
        
        if "marktplaats.nl" in url_lower:
            return Platform.MARKTPLAATS
        elif "instagram.com" in url_lower:
            return Platform.INSTAGRAM
        elif "facebook.com" in url_lower or "fb.com" in url_lower:
            return Platform.FACEBOOK
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return Platform.YOUTUBE
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            return Platform.TWITTER
        elif "tiktok.com" in url_lower:
            return Platform.TIKTOK
        elif any(news_domain in url_lower for news_domain in [
            "nu.nl", "nos.nl", "ad.nl", "telegraaf.nl", "rtl.nl",
            "hurriyet.com.tr", "sozcu.com.tr", "haberturk.com", "cnnturk.com"
        ]):
            return Platform.NEWS
        elif any(event_domain in url_lower for event_domain in [
            "eventbrite.com", "facebook.com/events", "meetup.com"
        ]):
            return Platform.EVENT
        else:
            return Platform.OTHER
    
    def extract_facebook_page_name(self, url: str) -> Optional[str]:
        """Extract Facebook page name from URL if possible."""
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split("/") if p]
            
            # Try to extract page name from URL patterns:
            # facebook.com/PAGENAME/posts/...
            # facebook.com/PAGENAME
            if len(path_parts) > 0:
                page_name = path_parts[0]
                # Skip common Facebook paths
                if page_name not in ["permalink.php", "watch", "photo", "video", "events"]:
                    return page_name
        except:
            pass
        return None
    
    def format_facebook_page_name(self, page_name: str) -> str:
        """Format Facebook page name nicely (e.g., 'St.Strandinzicht' -> 'St. Strandinzicht')."""
        # Replace dots and underscores with spaces, but preserve existing spaces
        formatted = page_name.replace(".", " ").replace("_", " ")
        # Clean up multiple spaces
        formatted = " ".join(formatted.split())
        # Capitalize first letter of each word
        return formatted.title()
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL: ensure https, convert YouTube short URLs, preserve query params.
        Only lowercases domain, preserves path and query case (especially YouTube video IDs).
        """
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        # Parse URL to handle YouTube short URLs properly
        parsed = urlparse(url)
        
        # Convert YouTube short URLs (youtu.be) to full format
        if parsed.netloc.lower() in ("youtu.be", "www.youtu.be"):
            # Extract video ID from path (preserve case - YouTube IDs are case-sensitive!)
            video_id = parsed.path.lstrip("/")
            # Preserve query parameters (also preserve case)
            query = parsed.query
            # Build full YouTube URL with preserved case
            if query:
                normalized = f"https://www.youtube.com/watch?v={video_id}&{query}"
            else:
                normalized = f"https://www.youtube.com/watch?v={video_id}"
            return normalized
        
        # For YouTube watch URLs, preserve video ID case
        if parsed.netloc.lower() in ("youtube.com", "www.youtube.com"):
            if "/watch" in parsed.path.lower():
                # Parse query to preserve video ID case
                query_params = parse_qs(parsed.query, keep_blank_values=True)
                # Rebuild query string preserving case
                query_parts = []
                for key, values in query_params.items():
                    for value in values:
                        query_parts.append(f"{key}={value}")
                query_str = "&".join(query_parts)
                
                # Reconstruct with preserved case
                normalized = urlunparse((
                    "https",
                    "www.youtube.com",
                    "/watch",
                    "",
                    query_str,
                    parsed.fragment
                ))
                return normalized
        
        # For other URLs, normalize domain to lowercase but preserve path/query case
        # Remove trailing slash from path (but preserve query/fragment)
        path = parsed.path.rstrip("/") if parsed.path != "/" else parsed.path
        
        # Reconstruct URL with normalized domain
        normalized = urlunparse((
            parsed.scheme.lower() if parsed.scheme else "https",
            parsed.netloc.lower(),
            path,
            parsed.params,
            parsed.query,  # Preserve query parameters as-is
            parsed.fragment
        ))
        
        return normalized
    
    async def fetch_oembed(self, url: str, platform: Platform) -> Optional[Dict[str, Any]]:
        """Try to fetch oEmbed data (Niveau A)."""
        oembed_endpoints = {
            Platform.YOUTUBE: "https://www.youtube.com/oembed",
            Platform.TWITTER: "https://publish.twitter.com/oembed",
            # Instagram doesn't support public oEmbed anymore
        }
        
        endpoint = oembed_endpoints.get(platform)
        if not endpoint:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # For YouTube oEmbed, extract just the video ID (oEmbed doesn't need query params like si=)
                # But preserve the full URL with params for storage
                oembed_url = url
                if platform == Platform.YOUTUBE:
                    parsed = urlparse(url)
                    if "watch" in parsed.path.lower():
                        query_params = parse_qs(parsed.query, keep_blank_values=True)
                        if "v" in query_params:
                            # Use just the video ID for oEmbed (cleaner, works better)
                            video_id = query_params["v"][0]
                            oembed_url = f"https://www.youtube.com/watch?v={video_id}"
                
                params = {"url": oembed_url, "format": "json"}
                response = await client.get(endpoint, params=params, headers={"User-Agent": self.user_agent})
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.debug("oembed_fetch_failed", url=url, platform=platform.value, error=str(e))
        return None
    
    def _get_headers_for_url(self, url: str) -> Dict[str, str]:
        """Get appropriate headers for fetching a URL."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,nl;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Add referer for Facebook to make requests look more legitimate
        parsed = urlparse(url)
        if "facebook.com" in parsed.netloc.lower():
            headers["Referer"] = "https://www.facebook.com/"
        
        return headers
    
    async def fetch_facebook_graph_api(self, url: str) -> Optional[Dict[str, Any]]:
        """Try to fetch Facebook post data via Graph API (for public posts)."""
        try:
            # Facebook Graph API scrape endpoint - works for public posts without token
            # The scrape endpoint caches the post and returns og_object data
            graph_url = "https://graph.facebook.com/v18.0/"
            
            # Method 1: Try scrape endpoint (POST) which caches and returns data
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                scrape_params = {
                    "id": url,
                    "scrape": "true"
                }
                
                try:
                    # POST to scrape endpoint - this caches the post
                    scrape_response = await client.post(graph_url, params=scrape_params)
                    if scrape_response.status_code == 200:
                        scrape_data = scrape_response.json()
                        og_object = scrape_data.get("og_object")
                        if og_object:
                            preview = {}
                            if og_object.get("title"):
                                preview["title"] = og_object["title"]
                            if og_object.get("description"):
                                preview["description"] = og_object["description"]
                            if og_object.get("image"):
                                image_data = og_object["image"]
                                if isinstance(image_data, dict) and image_data.get("url"):
                                    preview["image_url"] = image_data["url"]
                                elif isinstance(image_data, list) and len(image_data) > 0:
                                    first_img = image_data[0]
                                    if isinstance(first_img, dict) and first_img.get("url"):
                                        preview["image_url"] = first_img["url"]
                            if og_object.get("url"):
                                preview["video_url"] = og_object["url"]
                            if preview:
                                return preview
                except Exception as scrape_err:
                    logger.debug("facebook_scrape_failed", url=url, error=str(scrape_err))
                
                # Method 2: Try GET with fields parameter (might work if post is already cached)
                try:
                    fetch_params = {
                        "id": url,
                        "fields": "og_object{title,description,image{url},url}"
                    }
                    fetch_response = await client.get(graph_url, params=fetch_params)
                    if fetch_response.status_code == 200:
                        fetch_data = fetch_response.json()
                        og_object = fetch_data.get("og_object")
                        if og_object:
                            preview = {}
                            if og_object.get("title"):
                                preview["title"] = og_object["title"]
                            if og_object.get("description"):
                                preview["description"] = og_object["description"]
                            if og_object.get("image"):
                                image_data = og_object["image"]
                                if isinstance(image_data, dict) and image_data.get("url"):
                                    preview["image_url"] = image_data["url"]
                                elif isinstance(image_data, list) and len(image_data) > 0:
                                    first_img = image_data[0]
                                    if isinstance(first_img, dict) and first_img.get("url"):
                                        preview["image_url"] = first_img["url"]
                            if og_object.get("url"):
                                preview["video_url"] = og_object["url"]
                            if preview:
                                return preview
                except Exception as fetch_err:
                    logger.debug("facebook_fetch_failed", url=url, error=str(fetch_err))
                    
        except Exception as e:
            logger.debug("facebook_graph_api_failed", url=url, error=str(e))
        return None
    
    async def fetch_opengraph(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch Open Graph metadata (Niveau B)."""
        # For Facebook URLs, try Graph API first (works better for public posts)
        if "facebook.com" in url.lower():
            graph_preview = await self.fetch_facebook_graph_api(url)
            if graph_preview:
                return graph_preview
        
        try:
            headers = self._get_headers_for_url(url)
            
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                html_text = response.text
                html_lower = html_text.lower()
                
                # Check if Facebook is asking us to log in
                if "facebook.com" in url.lower():
                    if any(phrase in html_lower for phrase in [
                        "log in to continue",
                        "aanmelden bij facebook",
                        "you must log in",
                        "meld je aan",
                        "sign up for facebook"
                    ]):
                        logger.debug("facebook_login_required", url=url)
                        # Try to extract basic info from the page anyway
                        # Sometimes Facebook shows some info even on login page
                        soup = BeautifulSoup(html_text, "html.parser")
                        
                        # Try to find page name or post author from meta tags
                        preview = {}
                        page_name = None
                        
                        # Look for page name in various meta tags
                        for meta in soup.find_all("meta"):
                            prop = meta.get("property", "")
                            content = meta.get("content", "")
                            if "og:site_name" in prop.lower():
                                page_name = content
                            elif "og:title" in prop.lower() and content:
                                # Sometimes og:title has useful info even on login page
                                if not any(phrase in content.lower() for phrase in ["log in", "aanmelden", "facebook"]):
                                    preview["title"] = content.strip()
                        
                        # If we found a page name, use it as title
                        if page_name and not preview.get("title"):
                            preview["title"] = page_name
                        
                        # Try to get description from meta
                        og_desc = soup.find("meta", property="og:description")
                        if og_desc:
                            desc = og_desc.get("content", "").strip()
                            if desc and not any(phrase in desc.lower() for phrase in [
                                "log in to continue", "meld je aan", "you must log in"
                            ]):
                                preview["description"] = desc
                        
                        # Try to get image
                        og_image = soup.find("meta", property="og:image")
                        if og_image:
                            image_url = og_image.get("content", "").strip()
                            if image_url and image_url.startswith(("http://", "https://")):
                                preview["image_url"] = image_url
                        
                        return preview if preview else None
                
                soup = BeautifulSoup(html_text, "html.parser")
                
                preview = {}
                
                # Open Graph tags
                og_title = soup.find("meta", property="og:title")
                if og_title:
                    preview["title"] = og_title.get("content", "").strip()
                
                og_description = soup.find("meta", property="og:description")
                if og_description:
                    preview["description"] = og_description.get("content", "").strip()
                
                og_image = soup.find("meta", property="og:image")
                if og_image:
                    image_url = og_image.get("content", "").strip()
                    # Make relative URLs absolute
                    if image_url and not image_url.startswith(("http://", "https://")):
                        parsed = urlparse(url)
                        base_url = f"{parsed.scheme}://{parsed.netloc}"
                        if image_url.startswith("/"):
                            image_url = base_url + image_url
                        else:
                            image_url = base_url + "/" + image_url
                    preview["image_url"] = image_url
                
                og_video = soup.find("meta", property="og:video")
                if og_video:
                    preview["video_url"] = og_video.get("content", "").strip()
                
                # Fallback to standard meta tags
                if not preview.get("title"):
                    title_tag = soup.find("title")
                    if title_tag:
                        title_text = title_tag.get_text().strip()
                        # Skip generic Facebook login titles
                        if title_text and not any(phrase in title_text.lower() for phrase in [
                            "log in", "aanmelden", "facebook"
                        ]):
                            preview["title"] = title_text
                
                if not preview.get("description"):
                    meta_desc = soup.find("meta", attrs={"name": "description"})
                    if meta_desc:
                        desc_text = meta_desc.get("content", "").strip()
                        # Skip generic Facebook login descriptions
                        if desc_text and not any(phrase in desc_text.lower() for phrase in [
                            "log in to continue", "meld je aan", "you must log in"
                        ]):
                            preview["description"] = desc_text
                
                return preview if preview else None
                
        except Exception as e:
            logger.debug("opengraph_fetch_failed", url=url, error=str(e))
            return None
    
    async def generate_preview(self, url: str) -> LinkPreview:
        """Generate preview using 3-level fallback strategy."""
        normalized_url = self.normalize_url(url)
        platform = self.detect_platform(normalized_url)
        
        preview = LinkPreview(url=normalized_url, platform=platform)
        
        # Niveau A: Try oEmbed
        oembed_data = await self.fetch_oembed(normalized_url, platform)
        if oembed_data:
            preview.title = oembed_data.get("title")
            preview.description = oembed_data.get("description")
            preview.image_url = oembed_data.get("thumbnail_url") or oembed_data.get("thumbnail")
            # For YouTube, use the normalized URL as video URL (already in correct format)
            if platform == Platform.YOUTUBE:
                preview.video_url = normalized_url
            preview.preview_method = "oembed"
            return preview
        
        # Niveau B: Try Open Graph
        og_data = await self.fetch_opengraph(normalized_url)
        if og_data:
            preview.title = og_data.get("title")
            preview.description = og_data.get("description")
            preview.image_url = og_data.get("image_url")
            preview.video_url = og_data.get("video_url")
            preview.preview_method = "opengraph"
            return preview
        
        # Niveau C: Fallback - try to extract useful info from URL
        parsed = urlparse(normalized_url)
        
        # For Facebook, try to extract page name
        if platform == Platform.FACEBOOK:
            page_name = self.extract_facebook_page_name(normalized_url)
            if page_name:
                # Format page name nicely
                preview.title = self.format_facebook_page_name(page_name)
                # Add a helpful description
                preview.description = f"Bekijk deze post van {preview.title} op Facebook"
            else:
                preview.title = "Facebook Post"
                preview.description = "Bekijk deze post op Facebook"
        else:
            preview.title = parsed.netloc.replace("www.", "")
        
        preview.preview_method = "fallback"
        return preview


# Singleton instance
_link_preview_service: Optional[LinkPreviewService] = None


def get_link_preview_service() -> LinkPreviewService:
    """Get or create LinkPreviewService singleton."""
    global _link_preview_service
    if _link_preview_service is None:
        _link_preview_service = LinkPreviewService()
    return _link_preview_service

