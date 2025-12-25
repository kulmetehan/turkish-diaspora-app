# -*- coding: utf-8 -*-
"""
Website Scraper Service voor Contact Discovery.

Scraped contact pagina's van websites om e-mailadressen te vinden.
Respecteert robots.txt en rate limiting.
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional
from urllib.parse import urlparse, urljoin, urlunparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger

logger = get_logger()

# Configuration
DEFAULT_TIMEOUT_S = 5
DEFAULT_RATE_LIMIT_DELAY_S = 2.0  # 1 request per 2 seconds
USER_AGENT = "TurkishDiasporaApp/1.0 (contact: m.kul@lamarka.nl)"

# Email regex pattern (basic, matches most common formats)
EMAIL_PATTERN = re.compile(
    r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    re.IGNORECASE
)

# Common contact page paths to try
CONTACT_PATHS = [
    "/contact",
    "/contact-us",
    "/contacten",
    "/iletişim",
    "/over-ons",
    "/about",
    "/about-us",
    "/info",
]


class WebsiteScraperService:
    """Service voor het scrapen van websites om e-mailadressen te vinden."""
    
    def __init__(
        self,
        timeout_s: int = DEFAULT_TIMEOUT_S,
        rate_limit_delay_s: float = DEFAULT_RATE_LIMIT_DELAY_S,
    ):
        """
        Initialize website scraper service.
        
        Args:
            timeout_s: Request timeout in seconds
            rate_limit_delay_s: Minimum delay between requests (seconds)
        """
        self.timeout_s = timeout_s
        self.rate_limit_delay_s = rate_limit_delay_s
        self._last_request_time: Optional[float] = None
        self._robots_cache: dict[str, Optional[RobotFileParser]] = {}
    
    async def scrape_contact_email(self, website_url: str) -> Optional[str]:
        """
        Scrape website voor contact email adres.
        
        Strategie:
        1. Check robots.txt
        2. Probeer contact pagina's (contact, contact-us, etc.)
        3. Extract email via mailto links (BeautifulSoup)
        4. Fallback naar regex in HTML text content
        
        Args:
            website_url: Website URL (mag http:// of https:// zijn)
            
        Returns:
            Email address if found, None otherwise
        """
        if not website_url:
            return None
        
        # Normalize URL
        website_url = website_url.strip()
        if not website_url.startswith(('http://', 'https://')):
            website_url = 'https://' + website_url
        
        try:
            parsed = urlparse(website_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # Check robots.txt
            if not await self._can_fetch(base_url, "/"):
                logger.debug(
                    "website_scraper_robots_disallow",
                    website=base_url
                )
                return None
            
            # Enforce rate limiting
            await self._enforce_rate_limit()
            
            # Try contact pages first (most likely to have email)
            for path in CONTACT_PATHS:
                contact_url = urljoin(base_url, path)
                
                try:
                    email = await self._scrape_page_for_email(contact_url)
                    if email:
                        logger.info(
                            "website_scraper_email_found",
                            website=base_url,
                            path=path,
                            email=email[:3] + "***"
                        )
                        return email
                except Exception as e:
                    logger.debug(
                        "website_scraper_path_failed",
                        website=base_url,
                        path=path,
                        error=str(e)
                    )
                    continue
            
            # Fallback: try homepage
            try:
                email = await self._scrape_page_for_email(base_url)
                if email:
                    logger.info(
                        "website_scraper_email_found_homepage",
                        website=base_url,
                        email=email[:3] + "***"
                    )
                    return email
            except Exception as e:
                logger.debug(
                    "website_scraper_homepage_failed",
                    website=base_url,
                    error=str(e)
                )
            
            return None
            
        except Exception as e:
            logger.error(
                "website_scraper_error",
                website=website_url,
                error=str(e),
                exc_info=True
            )
            return None
    
    async def _scrape_page_for_email(self, url: str) -> Optional[str]:
        """
        Scrape een specifieke pagina voor email adres.
        
        Args:
            url: URL van de pagina om te scrapen
            
        Returns:
            Email address if found, None otherwise
        """
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_s),
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                html_content = response.text
                
                # Strategy 1: BeautifulSoup parsing voor mailto links
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find all mailto links
                mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
                for link in mailto_links:
                    href = link.get('href', '')
                    if href.startswith('mailto:'):
                        email = href.replace('mailto:', '').strip().split('?')[0].split('&')[0]
                        if self._is_valid_email(email):
                            return email.lower()
                
                # Strategy 2: Regex in text content (fallback)
                # Get text content (excluding scripts and styles)
                for element in soup(['script', 'style']):
                    element.decompose()
                
                text_content = soup.get_text()
                emails = EMAIL_PATTERN.findall(text_content)
                
                # Filter and return first valid email
                for email in emails:
                    if self._is_valid_email(email):
                        # Prefer emails that don't look like examples or placeholders
                        if not self._is_example_email(email):
                            return email.lower()
                
                return None
                
        except httpx.HTTPError as e:
            logger.debug(
                "website_scraper_http_error",
                url=url,
                error=str(e)
            )
            return None
        except Exception as e:
            logger.debug(
                "website_scraper_parse_error",
                url=url,
                error=str(e)
            )
            return None
    
    async def _can_fetch(self, base_url: str, path: str) -> bool:
        """
        Check of robots.txt toestaat om deze URL te fetchen.
        
        Args:
            base_url: Base URL (scheme://domain)
            path: Path to check
            
        Returns:
            True if allowed, False otherwise
        """
        try:
            # Check cache first
            if base_url in self._robots_cache:
                rp = self._robots_cache[base_url]
                if rp is None:
                    return True  # No robots.txt found, allow
                return rp.can_fetch(USER_AGENT, path)
            
            # Fetch robots.txt
            robots_url = urljoin(base_url, '/robots.txt')
            
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(5.0),
                    headers={"User-Agent": USER_AGENT},
                ) as client:
                    response = await client.get(robots_url)
                    if response.status_code == 200:
                        rp = RobotFileParser()
                        rp.set_url(robots_url)
                        rp.read()
                        self._robots_cache[base_url] = rp
                        return rp.can_fetch(USER_AGENT, path)
                    else:
                        # No robots.txt or not accessible, allow
                        self._robots_cache[base_url] = None
                        return True
            except Exception:
                # Failed to fetch robots.txt, allow (fail open)
                self._robots_cache[base_url] = None
                return True
                
        except Exception as e:
            logger.debug(
                "website_scraper_robots_check_error",
                base_url=base_url,
                path=path,
                error=str(e)
            )
            # Fail open: if robots.txt check fails, allow
            return True
    
    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self._last_request_time is not None:
            elapsed = asyncio.get_event_loop().time() - self._last_request_time
            if elapsed < self.rate_limit_delay_s:
                delay = self.rate_limit_delay_s - elapsed
                await asyncio.sleep(delay)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Basic email validation.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        email = email.strip().lower()
        if not email:
            return False
        
        # Basic format check
        if "@" not in email:
            return False
        
        parts = email.split("@")
        if len(parts) != 2:
            return False
        
        local, domain = parts
        if not local or not domain:
            return False
        
        if "." not in domain:
            return False
        
        # Basic regex for email format
        if not EMAIL_PATTERN.match(email):
            return False
        
        # Reject very long emails (likely false positives)
        if len(email) > 254:  # RFC 5321 limit
            return False
        
        return True
    
    def _is_example_email(self, email: str) -> bool:
        """
        Check if email looks like an example or placeholder.
        
        Args:
            email: Email address to check
            
        Returns:
            True if likely an example, False otherwise
        """
        email_lower = email.lower()
        
        # Common example patterns
        example_patterns = [
            'example.com',
            'example.org',
            'test.com',
            'placeholder',
            'your-email',
            'email@domain.com',
            'info@example',
            'contact@example',
        ]
        
        for pattern in example_patterns:
            if pattern in email_lower:
                return True
        
        return False


# Global instance
_website_scraper_service: Optional[WebsiteScraperService] = None


def get_website_scraper_service() -> WebsiteScraperService:
    """Get or create the global website scraper service instance."""
    global _website_scraper_service
    if _website_scraper_service is None:
        _website_scraper_service = WebsiteScraperService()
    return _website_scraper_service

