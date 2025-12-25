# -*- coding: utf-8 -*-
"""
Contact Discovery Service — Service voor het ontdekken van contactgegevens voor locaties.

Strategie (in volgorde):
1. OSM tags (email, contact:email) - confidence: 90/85
2. OSM website tag → website scraping → educated guess (info@[domein]) - confidence: 70/45
3. Social bio (Facebook / Instagram, indien beschikbaar) - TODO

Regels:
- Alleen zichtbare e-mails (geen scraping achter logins)
- Educated guess (info@[domein]) als fallback wanneer scraping faalt
- Confidence score berekenen op basis van bron
- Confidence < drempel → skip
"""

from __future__ import annotations

import os
import re
from typing import Optional
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from app.core.logging import get_logger
from app.models.contact import ContactInfo, ContactSource
from services.db_service import fetchrow
from services.osm_service import OsmPlacesService
from services.website_scraper_service import get_website_scraper_service

logger = get_logger()

# Configuration
DEFAULT_CONFIDENCE_THRESHOLD = int(os.getenv("CONTACT_DISCOVERY_CONFIDENCE_THRESHOLD", "50"))
GUESS_CONFIDENCE_THRESHOLD = int(os.getenv("CONTACT_DISCOVERY_GUESS_CONFIDENCE_THRESHOLD", "40"))
GENERIC_EMAIL_PATTERNS = [
    r"^info@",
    r"^contact@",
    r"^hello@",
    r"^noreply@",
    r"^no-reply@",
]


class ContactDiscoveryService:
    """Service voor het ontdekken van contactgegevens voor locaties."""
    
    def __init__(self, confidence_threshold: int = DEFAULT_CONFIDENCE_THRESHOLD):
        """
        Initialize contact discovery service.
        
        Args:
            confidence_threshold: Minimum confidence score (0-100) to accept a contact
        """
        self.confidence_threshold = confidence_threshold
        self.guess_confidence_threshold = GUESS_CONFIDENCE_THRESHOLD
        self.osm_service = OsmPlacesService()
        self.website_scraper = get_website_scraper_service()
    
    async def discover_contact(self, location_id: int) -> Optional[ContactInfo]:
        """
        Discover contact information for a location.
        
        Tries discovery strategies in order until a contact with sufficient confidence is found.
        
        Args:
            location_id: Location ID to discover contact for
            
        Returns:
            ContactInfo with email, source, confidence_score, or None if no contact found
        """
        # First, get location data from database
        location = await self._get_location(location_id)
        if not location:
            logger.warning(
                "location_not_found",
                location_id=location_id,
                action="contact_discovery"
            )
            return None
        
        # Try OSM discovery first (highest confidence, free)
        osm_contact = await self._discover_osm_contact(location)
        if osm_contact and osm_contact.confidence_score >= self.confidence_threshold:
            logger.info(
                "contact_discovered",
                location_id=location_id,
                source="osm",
                confidence=osm_contact.confidence_score,
                email=osm_contact.email[:3] + "***"  # Log partially masked email
            )
            return osm_contact
        
        # Try website scraping (OSM website tag → scrape → info@ fallback)
        website_contact = await self._discover_website_contact(location)
        if website_contact:
            # Contact is already validated in _discover_website_contact (checks both thresholds)
            logger.info(
                "contact_discovered",
                location_id=location_id,
                source="website",
                confidence=website_contact.confidence_score,
                email=website_contact.email[:3] + "***"  # Log partially masked email
            )
            return website_contact
        
        # TODO: Try social media (niet geïmplementeerd)
        
        logger.debug(
            "no_contact_found",
            location_id=location_id,
            confidence_threshold=self.confidence_threshold
        )
        return None
    
    async def _get_location(self, location_id: int) -> Optional[dict]:
        """Get location data from database."""
        row = await fetchrow(
            """
            SELECT id, name, address, lat, lng, place_id, source
            FROM locations
            WHERE id = $1
            LIMIT 1
            """,
            location_id,
        )
        return dict(row) if row else None
    
    async def _discover_osm_contact(self, location: dict) -> Optional[ContactInfo]:
        """
        Discover contact via OSM tags.
        
        Checks:
        - email tag (confidence: 90)
        - contact:email tag (confidence: 85)
        
        Args:
            location: Location dict with id, lat, lng, place_id, etc.
            
        Returns:
            ContactInfo if email found, None otherwise
        """
        lat = location.get("lat")
        lng = location.get("lng")
        place_id = location.get("place_id")
        
        if not lat or not lng:
            logger.debug(
                "osm_contact_skipped_no_coords",
                location_id=location.get("id")
            )
            return None
        
        try:
            # Query OSM Overpass API for the location
            # We need to get the OSM element to check its tags
            # For now, we'll query a small area around the location to find matching elements
            # Note: This is a simplified approach - in production, we might want to
            # store OSM element IDs or query more efficiently
            
            # Try to extract OSM element ID from place_id if it's in format "node/123" or "way/456"
            osm_element = None
            if place_id:
                # Check if place_id contains OSM element reference
                # Format might be "node/123" or "way/456" or just numeric ID
                if "/" in place_id:
                    element_type, element_id = place_id.split("/", 1)
                    # We could query Overpass directly for this element
                    # For now, we'll use a nearby search as fallback
                    osm_element = await self._query_osm_element_by_location(lat, lng)
                else:
                    # Fallback to nearby search
                    osm_element = await self._query_osm_element_by_location(lat, lng)
            else:
                osm_element = await self._query_osm_element_by_location(lat, lng)
            
            if not osm_element:
                return None
            
            tags = osm_element.get("tags", {})
            
            # Check email tag first (higher confidence)
            email = tags.get("email")
            if email and self._is_valid_email(email):
                confidence = 90
                confidence = self._apply_email_penalties(email, confidence)
                
                if confidence >= self.confidence_threshold:
                    return ContactInfo(
                        email=email,
                        source="osm",
                        confidence_score=confidence,
                        discovered_at=datetime.now(timezone.utc)
                    )
            
            # Check contact:email tag (lower confidence)
            contact_email = tags.get("contact:email")
            if contact_email and self._is_valid_email(contact_email):
                confidence = 85
                confidence = self._apply_email_penalties(contact_email, confidence)
                
                if confidence >= self.confidence_threshold:
                    return ContactInfo(
                        email=contact_email,
                        source="osm",
                        confidence_score=confidence,
                        discovered_at=datetime.now(timezone.utc)
                    )
            
            return None
            
        except Exception as e:
            logger.error(
                "osm_contact_discovery_error",
                location_id=location.get("id"),
                error=str(e),
                exc_info=True
            )
            return None
    
    async def _discover_website_contact(self, location: dict) -> Optional[ContactInfo]:
        """
        Discover contact via website scraping.
        
        Requires website URL from OSM tags (website tag).
        
        Args:
            location: Location dict with id, lat, lng, place_id, etc.
            
        Returns:
            ContactInfo if email found, None otherwise
        """
        lat = location.get("lat")
        lng = location.get("lng")
        place_id = location.get("place_id")
        
        if not lat or not lng:
            logger.debug(
                "website_contact_skipped_no_coords",
                location_id=location.get("id")
            )
            return None
        
        try:
            # First, get OSM element to check for website tag
            osm_element = None
            if place_id:
                if "/" in place_id:
                    element_type, element_id = place_id.split("/", 1)
                    osm_element = await self._query_osm_element_by_location(lat, lng)
                else:
                    osm_element = await self._query_osm_element_by_location(lat, lng)
            else:
                osm_element = await self._query_osm_element_by_location(lat, lng)
            
            if not osm_element:
                return None
            
            tags = osm_element.get("tags", {})
            website_url = tags.get("website") or tags.get("contact:website")
            
            if not website_url:
                logger.debug(
                    "website_contact_skipped_no_website",
                    location_id=location.get("id")
                )
                return None
            
            # Scrape website for email
            email = await self.website_scraper.scrape_contact_email(website_url)
            
            if email and self._is_valid_email(email):
                # Base confidence: 70 for website scraping
                confidence = 70
                confidence = self._apply_email_penalties(email, confidence)
                
                if confidence >= self.confidence_threshold:
                    return ContactInfo(
                        email=email,
                        source="website",
                        confidence_score=confidence,
                        discovered_at=datetime.now(timezone.utc)
                    )
            
            # Fallback to educated guess (info@[domein]) if scraping failed
            logger.debug(
                "website_scraping_no_email_fallback_to_guess",
                location_id=location.get("id"),
                website_url=website_url[:50]
            )
            guess_contact = await self._discover_website_guess_contact(location, website_url)
            if guess_contact:
                return guess_contact
            
            return None
            
        except Exception as e:
            logger.error(
                "website_contact_discovery_error",
                location_id=location.get("id"),
                error=str(e),
                exc_info=True
            )
            return None
    
    async def _query_osm_element_by_location(self, lat: float, lng: float) -> Optional[dict]:
        """
        Query OSM element at given location using Overpass API.
        
        Queries a very small radius (10m) to find elements with email tags.
        Uses direct Overpass API query to get raw element data with tags.
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            OSM element dict with tags, or None if not found
        """
        try:
            # Query a very small radius (10m) to find the exact element
            # Query for nodes and ways with email tags
            query = f"""[out:json][timeout:25];
(
  node["email"](around:10,{lat},{lng});
  node["contact:email"](around:10,{lat},{lng});
  node["website"](around:10,{lat},{lng});
  node["contact:website"](around:10,{lat},{lng});
  way["email"](around:10,{lat},{lng});
  way["contact:email"](around:10,{lat},{lng});
  way["website"](around:10,{lat},{lng});
  way["contact:website"](around:10,{lat},{lng});
);
out body;"""
            
            # Use primary Overpass endpoint
            endpoint = self.osm_service.endpoint if hasattr(self.osm_service, 'endpoint') else "https://overpass-api.de/api/interpreter"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    endpoint,
                    content=query,
                    headers={"User-Agent": "TurkishDiasporaApp/1.0 (contact: m.kul@lamarka.nl)"}
                )
                response.raise_for_status()
                data = response.json()
            
            elements = data.get("elements", [])
            if not elements:
                return None
            
            # Return first element with tags (prefer elements with email/website tags)
            # Sort to prefer direct email tag, then website tag
            elements_with_email = [e for e in elements if e.get("tags", {}).get("email")]
            if elements_with_email:
                return elements_with_email[0]
            
            elements_with_contact_email = [e for e in elements if e.get("tags", {}).get("contact:email")]
            if elements_with_contact_email:
                return elements_with_contact_email[0]
            
            # Fallback to website tag (for website scraping)
            elements_with_website = [e for e in elements if e.get("tags", {}).get("website") or e.get("tags", {}).get("contact:website")]
            if elements_with_website:
                return elements_with_website[0]
            
            # Return first element if any found
            return elements[0] if elements else None
            
        except Exception as e:
            logger.debug(
                "osm_element_query_error",
                lat=lat,
                lng=lng,
                error=str(e)
            )
            return None
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        if not email or not isinstance(email, str):
            return False
        
        email = email.strip()
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
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False
        
        return True
    
    def _apply_email_penalties(self, email: str, base_confidence: int) -> int:
        """
        Apply confidence penalties based on email characteristics.
        
        Penalties:
        - Generic email (info@, contact@): -10
        - Onvolledige email: -20 (not applicable for OSM, but kept for future use)
        
        Args:
            email: Email address
            base_confidence: Base confidence score
            
        Returns:
            Adjusted confidence score
        """
        confidence = base_confidence
        
        # Check for generic email patterns
        email_lower = email.lower().strip()
        for pattern in GENERIC_EMAIL_PATTERNS:
            if re.match(pattern, email_lower):
                confidence -= 10
                logger.debug(
                    "email_penalty_generic",
                    email=email_lower[:3] + "***",
                    pattern=pattern,
                    penalty=-10
                )
                break
        
        # Ensure confidence doesn't go below 0
        return max(0, confidence)
    
    def _extract_domain_from_url(self, url: str) -> Optional[str]:
        """
        Extract domain from website URL.
        
        Examples:
            http://www.kapsalonkanat.nl/ -> kapsalonkanat.nl
            https://example.com/contact -> example.com
            www.example.nl -> example.nl
        
        Args:
            url: Website URL
            
        Returns:
            Domain name (without www, protocol, path) or None if invalid
        """
        if not url or not isinstance(url, str):
            return None
        
        url = url.strip()
        if not url:
            return None
        
        # Add protocol if missing (for urlparse to work correctly)
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split('/')[0]
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Basic validation: must contain at least one dot
            if '.' not in domain:
                return None
            
            # Remove port if present
            if ':' in domain:
                domain = domain.split(':')[0]
            
            return domain.lower()
        except Exception as e:
            logger.debug(
                "domain_extraction_error",
                url=url[:50],  # Log first 50 chars only
                error=str(e)
            )
            return None
    
    def _generate_educated_guess_email(self, domain: str) -> str:
        """
        Generate educated guess email (info@[domein]).
        
        Args:
            domain: Domain name (e.g., "kapsalonkanat.nl")
            
        Returns:
            Email address (e.g., "info@kapsalonkanat.nl")
        """
        return f"info@{domain}"
    
    async def _discover_website_guess_contact(
        self, 
        location: dict, 
        website_url: str
    ) -> Optional[ContactInfo]:
        """
        Generate educated guess email (info@[domein]) from website URL.
        
        This is a fallback strategy when website scraping doesn't find an email.
        Confidence is lower (45) because it's an educated guess.
        
        Args:
            location: Location dict with id, etc.
            website_url: Website URL from OSM tags or Google Search
            
        Returns:
            ContactInfo with info@[domein] if domain can be extracted, None otherwise
        """
        try:
            domain = self._extract_domain_from_url(website_url)
            if not domain:
                logger.debug(
                    "website_guess_skipped_no_domain",
                    location_id=location.get("id"),
                    website_url=website_url[:50]
                )
                return None
            
            # Generate info@[domein] email
            guessed_email = self._generate_educated_guess_email(domain)
            
            # Validate the generated email
            if not self._is_valid_email(guessed_email):
                logger.debug(
                    "website_guess_skipped_invalid_email",
                    location_id=location.get("id"),
                    guessed_email=guessed_email
                )
                return None
            
            # Base confidence: 45 for educated guess (lower than scraping)
            # Note: info@ is already generic, so we don't apply generic penalty
            confidence = 45
            
            if confidence >= self.guess_confidence_threshold:
                logger.info(
                    "educated_guess_email_generated",
                    location_id=location.get("id"),
                    website_url=website_url[:50],
                    guessed_email=guessed_email[:3] + "***",
                    confidence=confidence
                )
                return ContactInfo(
                    email=guessed_email,
                    source="website",  # Keep same source, but it's a guess
                    confidence_score=confidence,
                    discovered_at=datetime.now(timezone.utc)
                )
            
            return None
            
        except Exception as e:
            logger.error(
                "website_guess_contact_error",
                location_id=location.get("id"),
                website_url=website_url[:50] if website_url else None,
                error=str(e),
                exc_info=True
            )
            return None


# Global instance
_contact_discovery_service: Optional[ContactDiscoveryService] = None


def get_contact_discovery_service() -> ContactDiscoveryService:
    """Get or create the global contact discovery service instance."""
    global _contact_discovery_service
    if _contact_discovery_service is None:
        confidence_threshold = int(os.getenv("CONTACT_DISCOVERY_CONFIDENCE_THRESHOLD", "50"))
        _contact_discovery_service = ContactDiscoveryService(
            confidence_threshold=confidence_threshold
        )
    return _contact_discovery_service

