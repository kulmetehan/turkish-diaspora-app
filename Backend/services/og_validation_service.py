# Backend/services/og_validation_service.py
"""
Open Graph validation service for Prikbord link sharing.

Validates that links have proper Open Graph metadata before allowing sharing.
Blocks social media links (Facebook, Instagram, Twitter) that don't provide good previews.
"""

from __future__ import annotations

from typing import Optional
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from app.core.logging import get_logger

logger = get_logger()


class OGValidationService:
    """Service for validating Open Graph metadata in URLs."""
    
    def __init__(self):
        self.timeout = httpx.Timeout(10.0)
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    
    def is_blocked_domain(self, url: str) -> bool:
        """Check if URL is from a blocked domain (social media that don't provide good previews)."""
        parsed = urlparse(url.lower())
        domain = parsed.netloc.lower()
        
        blocked_domains = [
            "facebook.com",
            "www.facebook.com",
            "m.facebook.com",
            "instagram.com",
            "www.instagram.com",
            "twitter.com",
            "www.twitter.com",
            "x.com",
            "www.x.com",
        ]
        
        return any(domain == blocked or domain.endswith(f".{blocked}") for blocked in blocked_domains)
    
    async def validate_og_metadata(self, url: str) -> tuple[bool, Optional[str]]:
        """
        Validate that URL has proper Open Graph metadata.
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if URL has valid OG metadata
            - error_message: Error message if validation failed, None if valid
        """
        # Check if domain is blocked
        if self.is_blocked_domain(url):
            return False, "Social media links (Facebook, Instagram, Twitter) kunnen niet worden gedeeld omdat er geen preview beschikbaar is. Probeer een link van YouTube, Marktplaats of een nieuwssite."
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                )
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Check for Open Graph metadata
                og_title = soup.find("meta", property="og:title")
                og_description = soup.find("meta", property="og:description")
                
                # At minimum, we need title OR description
                if not og_title and not og_description:
                    return False, "Deze link kan niet worden gedeeld omdat er geen preview beschikbaar is. Probeer een link van YouTube, Marktplaats of een nieuwssite."
                
                # If we have at least one, it's valid
                return True, None
                
        except httpx.TimeoutException:
            logger.warning("og_validation_timeout", url=url[:100])
            return False, "Kon de link niet valideren (timeout). Probeer het later opnieuw."
        except httpx.HTTPStatusError as e:
            logger.warning("og_validation_http_error", url=url[:100], status_code=e.response.status_code)
            return False, "Kon de link niet valideren. De website reageert niet correct."
        except Exception as e:
            logger.error("og_validation_error", url=url[:100], error=str(e), exc_info=True)
            return False, "Kon de link niet valideren. Probeer het later opnieuw."


# Global instance
_og_validation_service: Optional[OGValidationService] = None


def get_og_validation_service() -> OGValidationService:
    """Get or create the global OG validation service instance."""
    global _og_validation_service
    if _og_validation_service is None:
        _og_validation_service = OGValidationService()
    return _og_validation_service


