"""
Spotify Viral 50 playlist scraper.

This scraper fetches tracks from Spotify Viral 50 playlists using browser automation
to handle JavaScript-rendered content.

**Data Sources (in order of attempt):**

1. **Playwright Browser Automation** (Primary):
   - Uses Playwright to load playlist pages in headless browser
   - Waits for JavaScript rendering to complete
   - Extracts track data from DOM elements
   - Most reliable method for JavaScript-rendered content

2. **Embedded JSON Parsing** (Fallback):
   - Extracts JSON data from script tags after page load
   - Parses playlist tracks from embedded JSON structures
   - Fallback if DOM scraping fails

**Rate Limiting:**
- Uses caching (3 minutes) to minimize requests
- Single concurrent request (max_concurrency=1)
- Respectful delays between requests
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from app.core.logging import get_logger
from services.base_scraper_service import BaseScraperService

logger = get_logger().bind(module="news_trending_spotify_scraper")

_DEFAULT_CACHE_TTL_SECONDS = 180  # 3 minutes cache
_cache: dict[str, dict[str, object]] = {}

# Spotify Viral 50 playlist IDs
_SPOTIFY_PLAYLIST_IDS = {
    "nl": "37i9dQZEVXbMQaPQjt027d",  # Netherlands Viral 50
    "tr": "37i9dQZEVXbMIJZxwqzod6",  # Turkey Viral 50
}


@dataclass(frozen=True)
class SpotifyTrack:
    title: str  # Track name
    url: str  # Direct Spotify track URL
    artist: str  # Artist name
    published_at: datetime | None
    image_url: Optional[str] = None  # Album/track thumbnail image URL


@dataclass
class SpotifyResult:
    """Result from Spotify playlist fetch, including unavailability reason if applicable."""
    tracks: List[SpotifyTrack]
    unavailable_reason: Optional[str] = None


class SpotifyScraper(BaseScraperService):
    """Scraper for Spotify Viral 50 playlists using browser automation."""

    def __init__(
        self,
        *,
        timeout_s: int = 30,  # Increased for browser automation
        max_concurrency: int = 1,  # Conservative for scraping
        max_retries: int = 2,
    ) -> None:
        """
        Initialize Spotify scraper.
        
        Args:
            timeout_s: Request timeout in seconds (increased for browser automation)
            max_concurrency: Maximum concurrent requests (set to 1 for scraping)
            max_retries: Maximum retry attempts
        """
        super().__init__(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            timeout_s=timeout_s,
            max_concurrency=max_concurrency,
            max_retries=max_retries,
        )

    async def scrape_playlist_tracks(
        self,
        country: str = "nl",
        limit: int = 20,
    ) -> SpotifyResult:
        """
        Scrape tracks from Spotify Viral 50 playlist using browser automation.
        
        Args:
            country: Country code (e.g., "nl", "tr")
            limit: Maximum number of tracks to return
            
        Returns:
            SpotifyResult with tracks or unavailable_reason
        """
        playlist_id = _SPOTIFY_PLAYLIST_IDS.get(country.lower())
        if not playlist_id:
            return SpotifyResult(
                tracks=[],
                unavailable_reason=f"spotify_unavailable_unknown_country_{country}",
            )
        
        # Try to get cached result
        cache_key = f"{playlist_id}_{limit}"
        now = time.time()
        bucket = _cache.get(cache_key, {})
        
        if bucket.get("expires_at", 0.0) > now:
            cached_result = bucket.get("result")
            if cached_result:
                logger.info("spotify_scraper_cache_hit", country=country, playlist_id=playlist_id)
                return cached_result
        
        playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
        
        # Strategy 1: Playwright browser automation (Primary)
        try:
            logger.info(
                "spotify_scraper_trying_playwright",
                country=country,
                playlist_id=playlist_id,
                url=playlist_url,
            )
            
            tracks = await self._scrape_with_playwright(playlist_url, limit)
            
            if tracks:
                logger.info(
                    "spotify_scraper_playwright_success",
                    tracks_count=len(tracks),
                    country=country,
                )
                result = SpotifyResult(tracks=tracks)
                # Cache the result
                _cache[cache_key] = {
                    "result": result,
                    "expires_at": now + _DEFAULT_CACHE_TTL_SECONDS,
                }
                return result
            else:
                logger.warning(
                    "spotify_scraper_playwright_no_tracks",
                    country=country,
                    playlist_id=playlist_id,
                )
        except Exception as exc:
            logger.warning(
                "spotify_scraper_playwright_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                country=country,
            )
        
        # Strategy 2: Embedded JSON parsing (Fallback)
        try:
            logger.info(
                "spotify_scraper_trying_json_fallback",
                country=country,
                playlist_id=playlist_id,
            )
            
            # Get HTML via HTTP request for JSON parsing
            if self._client is None:
                raise RuntimeError("Scraper client not initialized")
            
            response = await self._client.get(
                playlist_url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://open.spotify.com/",
                },
            )
            
            if response.status_code == 200:
                html = response.text
                tracks = self._parse_spotify_html(html, limit)
                
                if tracks:
                    logger.info(
                        "spotify_scraper_json_success",
                        tracks_count=len(tracks),
                        country=country,
                    )
                    result = SpotifyResult(tracks=tracks)
                    # Cache the result
                    _cache[cache_key] = {
                        "result": result,
                        "expires_at": now + _DEFAULT_CACHE_TTL_SECONDS,
                    }
                    return result
        except Exception as exc:
            logger.warning(
                "spotify_scraper_json_fallback_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                country=country,
            )
        
        # All strategies failed
        logger.warning(
            "spotify_scraper_all_strategies_failed",
            country=country,
            playlist_id=playlist_id,
        )
        
        return SpotifyResult(
            tracks=[],
            unavailable_reason="spotify_unavailable_scraper_all_failed",
        )

    async def _scrape_with_playwright(
        self,
        playlist_url: str,
        limit: int,
    ) -> List[SpotifyTrack]:
        """
        Scrape Spotify playlist using Playwright browser automation.
        
        Args:
            playlist_url: Full URL to Spotify playlist
            limit: Maximum number of tracks to return
            
        Returns:
            List of SpotifyTrack objects
        """
        tracks: List[SpotifyTrack] = []
        
        try:
            async with async_playwright() as p:
                browser: Browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"],  # For CI/CD environments
                )
                
                try:
                    page: Page = await browser.new_page()
                    
                    # Set realistic user agent and headers
                    await page.set_extra_http_headers({
                        "Accept-Language": "en-US,en;q=0.9",
                    })
                    
                    # Load playlist page
                    logger.debug("spotify_playwright_loading_page", url=playlist_url)
                    await page.goto(
                        playlist_url,
                        wait_until="networkidle",
                        timeout=30000,  # 30 seconds timeout
                    )
                    
                    # Wait for track list to render - try multiple selectors
                    selectors_to_try = [
                        '[data-testid="tracklist-row"]',
                        '[data-testid="entityTitle"]',
                        'div[role="row"]',
                        'a[href*="/track/"]',
                    ]
                    
                    track_list_loaded = False
                    for selector in selectors_to_try:
                        try:
                            await page.wait_for_selector(selector, timeout=10000)
                            track_list_loaded = True
                            logger.debug("spotify_playwright_selector_found", selector=selector)
                            break
                        except PlaywrightTimeoutError:
                            continue
                    
                    if not track_list_loaded:
                        logger.warning("spotify_playwright_no_selectors_found")
                        # Try to extract from page content anyway
                    
                    # Extract tracks from DOM using JavaScript
                    logger.debug("spotify_playwright_extracting_tracks")
                    extracted_data = await page.evaluate("""
                        () => {
                            const tracks = [];
                            
                            // Try multiple selector strategies for track rows
                            const rowSelectors = [
                                '[data-testid="tracklist-row"]',
                                'div[role="row"][aria-rowindex]',
                                'div[role="row"]',
                            ];
                            
                            let rows = [];
                            for (const selector of rowSelectors) {
                                rows = Array.from(document.querySelectorAll(selector));
                                if (rows.length > 0) break;
                            }
                            
                            // If no rows found, try finding all track links
                            if (rows.length === 0) {
                                const trackLinks = Array.from(document.querySelectorAll('a[href*="/track/"]'));
                                rows = trackLinks.map(link => link.closest('div[role="row"]') || link.parentElement).filter(Boolean);
                            }
                            
                            // Extract track information
                            for (const row of rows.slice(0, 20)) {
                                let name = null;
                                let artist = null;
                                let link = null;
                                let imageUrl = null;
                                
                                // Try to find track name - look for entityTitle or track name elements
                                const nameSelectors = [
                                    '[data-testid="entityTitle"]',
                                    '[data-testid="track-name"]',
                                    'a[href*="/track/"] span',
                                    'a[href*="/track/"]',
                                ];
                                
                                for (const sel of nameSelectors) {
                                    const elem = row.querySelector(sel);
                                    if (elem) {
                                        const text = elem.textContent?.trim();
                                        if (text && text.length > 0) {
                                            name = text;
                                            break;
                                        }
                                    }
                                }
                                
                                // Try to find artist - look for entitySubtitle or artist elements
                                const artistSelectors = [
                                    '[data-testid="entitySubtitle"]',
                                    '[data-testid="track-artist"]',
                                    'a[href*="/artist/"]',
                                    'span[class*="artist"]',
                                    'div[class*="artist"]',
                                ];
                                
                                for (const sel of artistSelectors) {
                                    const elem = row.querySelector(sel);
                                    if (elem) {
                                        const text = elem.textContent?.trim();
                                        if (text && text.length > 0 && text !== name) {
                                            artist = text;
                                            break;
                                        }
                                    }
                                }
                                
                                // Alternative: look for artist link near track name
                                if (!artist) {
                                    const nameElem = row.querySelector('[data-testid="entityTitle"]');
                                    if (nameElem) {
                                        const parent = nameElem.closest('div');
                                        if (parent) {
                                            const artistLink = parent.querySelector('a[href*="/artist/"]');
                                            if (artistLink) {
                                                artist = artistLink.textContent?.trim();
                                            }
                                        }
                                    }
                                }
                                
                                // Try to find track thumbnail image
                                const imageSelectors = [
                                    '[data-testid="cover-art"] img',
                                    '[data-testid="entityCoverArt"] img',
                                    'img[src*="i.scdn.co"]',
                                    'img[alt*="' + name + '"]',
                                    'img',
                                ];
                                
                                for (const sel of imageSelectors) {
                                    const imgElem = row.querySelector(sel);
                                    if (imgElem) {
                                        const src = imgElem.getAttribute('src');
                                        if (src && (src.includes('i.scdn.co') || src.includes('spotify'))) {
                                            // Get thumbnail size (64x64 for small thumbnail)
                                            // Spotify CDN URLs: https://i.scdn.co/image/{hash} or with size parameter
                                            if (src.includes('i.scdn.co')) {
                                                // Extract hash and construct 64x64 thumbnail URL
                                                const hashMatch = src.match(/image\/([a-zA-Z0-9]+)/);
                                                if (hashMatch) {
                                                    imageUrl = `https://i.scdn.co/image/${hashMatch[1]}`;
                                                } else {
                                                    // If size is already in URL, replace with 64x64
                                                    imageUrl = src.replace(/\/\d+x\d+\./, '/64x64.').replace(/\/\d+x\d+$/, '/64x64');
                                                }
                                            } else {
                                                imageUrl = src;
                                            }
                                            if (imageUrl) break;
                                        }
                                    }
                                }
                                
                                // Alternative: look for image in parent container or row
                                if (!imageUrl) {
                                    const parent = row.closest('div');
                                    if (parent) {
                                        const imgElem = parent.querySelector('[data-testid="cover-art"] img, [data-testid="entityCoverArt"] img, img[src*="i.scdn.co"]');
                                        if (imgElem) {
                                            const src = imgElem.getAttribute('src');
                                            if (src && src.includes('i.scdn.co')) {
                                                const hashMatch = src.match(/image\/([a-zA-Z0-9]+)/);
                                                if (hashMatch) {
                                                    imageUrl = `https://i.scdn.co/image/${hashMatch[1]}`;
                                                } else {
                                                    imageUrl = src.replace(/\/\d+x\d+\./, '/64x64.').replace(/\/\d+x\d+$/, '/64x64');
                                                }
                                            }
                                        }
                                    }
                                }
                                
                                // Try to find track link
                                const linkElem = row.querySelector('a[href*="/track/"]');
                                if (linkElem) {
                                    link = linkElem.href;
                                }
                                
                                if (name) {
                                    tracks.push({
                                        name: name,
                                        artist: artist || null,
                                        link: link || null,
                                        imageUrl: imageUrl || null,
                                    });
                                }
                            }
                            
                            return tracks;
                        }
                    """)
                    
                    # Convert extracted data to SpotifyTrack objects
                    for item in extracted_data[:limit]:
                        if item.get("name"):
                            track_name = item["name"]
                            artist_name = item.get("artist")
                            
                            # If artist is null or empty, try to extract from track name (format: "Artist - Track")
                            if not artist_name or artist_name.strip() == "":
                                if " - " in track_name:
                                    parts = track_name.split(" - ", 1)
                                    if len(parts) == 2:
                                        artist_name = parts[0].strip()
                                        track_name = parts[1].strip()
                                else:
                                    artist_name = "Unknown Artist"
                            else:
                                artist_name = artist_name.strip()
                            
                            track_url = item.get("link")
                            
                            # Construct track URL if not found
                            if not track_url:
                                # Try to extract track ID from any link in the row
                                track_url = f"https://open.spotify.com/search/{quote(f'{artist_name} {track_name}')}"
                            
                            # Get image URL (thumbnail)
                            image_url = item.get("imageUrl")
                            
                            tracks.append(SpotifyTrack(
                                title=track_name,
                                url=track_url,
                                artist=artist_name,
                                published_at=datetime.now(timezone.utc),
                                image_url=image_url,
                            ))
                    
                    # If DOM extraction failed, try embedded JSON
                    if not tracks:
                        logger.debug("spotify_playwright_trying_embedded_json")
                        html_content = await page.content()
                        json_tracks = self._parse_spotify_html(html_content, limit)
                        if json_tracks:
                            tracks = json_tracks
                    
                finally:
                    await browser.close()
                    
        except PlaywrightTimeoutError as exc:
            logger.warning(
                "spotify_playwright_timeout",
                error=str(exc),
                url=playlist_url,
            )
        except Exception as exc:
            logger.error(
                "spotify_playwright_error",
                error=str(exc),
                error_type=type(exc).__name__,
                url=playlist_url,
            )
            raise
        
        return tracks[:limit]  # Ensure we don't exceed limit

    def _parse_spotify_html(self, html: str, limit: int) -> List[SpotifyTrack]:
        """
        Parse Spotify playlist HTML to extract track information from embedded JSON.
        
        Spotify embeds track data in various ways:
        1. JSON-LD structured data
        2. Embedded JSON in script tags
        3. Meta tags with track information
        
        Args:
            html: HTML content from Spotify playlist page
            limit: Maximum tracks to return
            
        Returns:
            List of SpotifyTrack objects
        """
        tracks: List[SpotifyTrack] = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Strategy 1: Look for JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    # Spotify uses schema.org MusicPlaylist structure
                    if isinstance(data, dict):
                        if data.get("@type") == "MusicPlaylist":
                            tracks_data = data.get("track", [])
                            if isinstance(tracks_data, list):
                                for track_data in tracks_data[:limit]:
                                    if isinstance(track_data, dict):
                                        track_name = track_data.get("name") or track_data.get("title")
                                        track_url = track_data.get("url") or track_data.get("@id")
                                        artist_data = track_data.get("byArtist") or track_data.get("artist")
                                        artist_name = None
                                        if isinstance(artist_data, dict):
                                            artist_name = artist_data.get("name")
                                        elif isinstance(artist_data, str):
                                            artist_name = artist_data
                                        
                                        if track_name and track_url:
                                            tracks.append(SpotifyTrack(
                                                title=track_name,
                                                url=track_url if track_url.startswith("http") else f"https://open.spotify.com{track_url}",
                                                artist=artist_name or "Unknown Artist",
                                                published_at=datetime.now(timezone.utc),
                                            ))
                                            if len(tracks) >= limit:
                                                break
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.debug("spotify_json_ld_parse_error", error=str(e))
                    continue
            
            # Strategy 2: Look for embedded JSON in script tags (Spotify web player data)
            if not tracks:
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string:
                        text = script.string
                        
                        # Try to find JSON objects with track data
                        # Pattern: Look for objects with "name", "artists", "uri" fields
                        json_patterns = [
                            r'"name"\s*:\s*"([^"]+)"\s*,\s*"artists"\s*:\s*\[.*?"name"\s*:\s*"([^"]+)"',
                            r'"track"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"[^}]*"artists"\s*:\s*\[[^\]]*"name"\s*:\s*"([^"]+)"',
                        ]
                        
                        for pattern in json_patterns:
                            matches = list(re.finditer(pattern, text, re.DOTALL))
                            for match in matches[:limit]:
                                track_name = match.group(1) if match.groups() >= 1 else None
                                artist_name = match.group(2) if match.groups() >= 2 else "Unknown Artist"
                                
                                if track_name:
                                    # Try to find track URI/URL nearby
                                    uri_match = re.search(r'"uri"\s*:\s*"spotify:track:([^"]+)"', text[match.start():match.end()+500])
                                    track_id = uri_match.group(1) if uri_match else None
                                    track_url = f"https://open.spotify.com/track/{track_id}" if track_id else f"https://open.spotify.com/search/{quote(track_name)}"
                                    
                                    tracks.append(SpotifyTrack(
                                        title=track_name,
                                        url=track_url,
                                        artist=artist_name,
                                        published_at=datetime.now(timezone.utc),
                                    ))
                                    if len(tracks) >= limit:
                                        break
                            if len(tracks) >= limit:
                                break
                        if len(tracks) >= limit:
                            break
            
            # Strategy 3: Regex fallback - look for track URLs and names in HTML
            if not tracks:
                # Look for spotify:track: URIs
                track_uri_pattern = r'spotify:track:([a-zA-Z0-9]+)'
                track_uris = re.findall(track_uri_pattern, html)
                
                # Look for track names near URIs
                for track_id in track_uris[:limit]:
                    # Try to find track name nearby (within 500 chars)
                    track_url = f"https://open.spotify.com/track/{track_id}"
                    
                    # Look for name pattern near the URI
                    uri_index = html.find(f"spotify:track:{track_id}")
                    if uri_index >= 0:
                        context = html[max(0, uri_index-500):uri_index+500]
                        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', context)
                        artist_match = re.search(r'"artists"\s*:\s*\[[^\]]*"name"\s*:\s*"([^"]+)"', context)
                        
                        track_name = name_match.group(1) if name_match else f"Track {track_id[:8]}"
                        artist_name = artist_match.group(1) if artist_match else "Unknown Artist"
                        
                        tracks.append(SpotifyTrack(
                            title=track_name,
                            url=track_url,
                            artist=artist_name,
                            published_at=datetime.now(timezone.utc),
                        ))
                        if len(tracks) >= limit:
                            break
                        
        except Exception as exc:
            logger.warning("spotify_html_parse_error", error=str(exc), error_type=type(exc).__name__)
        
        return tracks[:limit]  # Ensure we don't exceed limit


async def fetch_spotify_tracks_scraper(
    limit: int = 20,
    country: str = "nl",
) -> SpotifyResult:
    """
    Fetch Spotify tracks using scraper.
    
    Args:
        limit: Maximum number of tracks to return
        country: Country code (e.g., "nl", "tr")
        
    Returns:
        SpotifyResult with tracks or unavailable_reason
    """
    async with SpotifyScraper() as scraper:
        return await scraper.scrape_playlist_tracks(country=country, limit=limit)
