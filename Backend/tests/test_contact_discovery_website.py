# Backend/tests/test_contact_discovery_website.py
"""
Tests for website scraping contact discovery functionality.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.contact_discovery_service import ContactDiscoveryService
from services.db_service import fetchrow, execute
from app.models.contact import ContactInfo


pytestmark = pytest.mark.asyncio


def create_mock_osm_response_with_website(website: str, name: str = "Test Location") -> dict:
    """Create mock OSM Overpass API response with website tag."""
    return {
        "elements": [{
            "type": "node",
            "id": 123456,
            "lat": 51.9244,
            "lon": 4.4777,
            "tags": {
                "website": website,
                "name": name
            }
        }]
    }


async def test_website_scraping_contact_discovery():
    """Test that website scraping correctly discovers email from website."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test Website Location",
        "Test Address Website",
        "restaurant",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/999888",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Mock OSM response with website tag (no email tag)
        mock_osm_response = create_mock_osm_response_with_website("https://example.com", "Test Website Location")
        
        # Mock website HTML with email in mailto link
        mock_html = """
        <html>
        <body>
            <a href="mailto:contact@example.com">Contact Us</a>
            <p>Visit us at contact@example.com</p>
        </body>
        </html>
        """
        
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client, \
             patch("services.website_scraper_service.httpx.AsyncClient") as mock_website_client:
            
            # Setup OSM mock
            mock_osm_response_obj = MagicMock()
            mock_osm_response_obj.json.return_value = mock_osm_response
            mock_osm_response_obj.raise_for_status = MagicMock()
            mock_osm_response_obj.status_code = 200
            
            # Setup website mock
            mock_website_response_obj = MagicMock()
            mock_website_response_obj.text = mock_html
            mock_website_response_obj.status_code = 200
            mock_website_response_obj.raise_for_status = MagicMock()
            
            # Setup async context manager pattern
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_osm_response_obj)
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            mock_website_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_website_response_obj)
            mock_website_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            service = ContactDiscoveryService(confidence_threshold=50)
            
            # Discover contact (should try OSM first, then website)
            contact = await service.discover_contact(location_id)
            
            # Verify website scraping found email
            assert contact is not None
            assert contact.email == "contact@example.com"
            assert contact.source == "website"
            assert contact.confidence_score == 70  # Base confidence for website scraping
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_website_scraping_robots_txt_respect():
    """Test that website scraping respects robots.txt disallow."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test Robots Disallow",
        "Test Address Robots",
        "restaurant",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/777666",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Mock OSM response with website tag
        mock_osm_response = create_mock_osm_response_with_website("https://blocked-site.com", "Test Robots Disallow")
        
        # Mock robots.txt that disallows all
        mock_robots_txt = """
        User-agent: *
        Disallow: /
        """
        
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client, \
             patch("services.website_scraper_service.httpx.AsyncClient") as mock_website_client:
            
            # Setup OSM mock
            mock_osm_response_obj = MagicMock()
            mock_osm_response_obj.json.return_value = mock_osm_response
            mock_osm_response_obj.raise_for_status = MagicMock()
            mock_osm_response_obj.status_code = 200
            
            # Setup robots.txt mock
            mock_robots_response_obj = MagicMock()
            mock_robots_response_obj.text = mock_robots_txt
            mock_robots_response_obj.status_code = 200
            mock_robots_response_obj.raise_for_status = MagicMock()
            
            # Setup async context manager pattern
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_osm_response_obj)
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            # Mock robots.txt fetch
            mock_website_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=lambda url, **kwargs: mock_robots_response_obj if "robots.txt" in str(url) else MagicMock()
            )
            mock_website_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            service = ContactDiscoveryService(confidence_threshold=50)
            
            # Discover contact (should respect robots.txt and skip scraping)
            contact = await service.discover_contact(location_id)
            
            # Verify no contact found (robots.txt blocked scraping)
            assert contact is None
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)

