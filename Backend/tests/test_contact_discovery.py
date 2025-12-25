# Backend/tests/test_contact_discovery.py
"""
Integration tests for Contact Discovery Service.

Tests the contact discovery service end-to-end, including:
- OSM email tag discovery
- OSM contact:email tag discovery
- Website scraping contact discovery
- Confidence scoring and penalties
- Error handling scenarios
- Service integration
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional

import pytest
import httpx

from services.contact_discovery_service import ContactDiscoveryService, get_contact_discovery_service
from services.db_service import fetchrow, execute
from services.website_scraper_service import WebsiteScraperService
from app.models.contact import ContactInfo


pytestmark = pytest.mark.asyncio


# Helper functions for mock OSM responses
def create_mock_osm_response_with_email(email: str, name: str = "Test Location") -> dict:
    """Create mock OSM Overpass API response with email tag."""
    return {
        "elements": [{
            "type": "node",
            "id": 123456,
            "lat": 51.9244,
            "lon": 4.4777,
            "tags": {
                "email": email,
                "name": name
            }
        }]
    }


def create_mock_osm_response_with_contact_email(email: str, name: str = "Test Location") -> dict:
    """Create mock OSM Overpass API response with contact:email tag."""
    return {
        "elements": [{
            "type": "node",
            "id": 123456,
            "lat": 51.9244,
            "lon": 4.4777,
            "tags": {
                "contact:email": email,
                "name": name
            }
        }]
    }


def create_mock_osm_response_no_email(name: str = "Test Location") -> dict:
    """Create mock OSM Overpass API response without email tags."""
    return {
        "elements": [{
            "type": "node",
            "id": 123456,
            "lat": 51.9244,
            "lon": 4.4777,
            "tags": {
                "name": name
            }
        }]
    }


def create_mock_osm_response_empty() -> dict:
    """Create mock OSM Overpass API response with no elements."""
    return {"elements": []}


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


# Test scenarios
async def test_osm_email_tag_discovery():
    """Test that OSM email tag is correctly detected with confidence score 90."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test Restaurant",
        "Test Address 123",
        "restaurant",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/123456",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Mock OSM Overpass API response with email tag
        mock_response = create_mock_osm_response_with_email("owner@testrestaurant.nl", "Test Restaurant")
        
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client:
            # Setup mock client response
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_response_obj.status_code = 200
            
            # Setup async context manager pattern for httpx.AsyncClient
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            # Create service with low threshold to accept the email
            service = ContactDiscoveryService(confidence_threshold=50)
            
            # Discover contact
            contact = await service.discover_contact(location_id)
            
            # Verify results
            assert contact is not None
            assert isinstance(contact, ContactInfo)
            assert contact.email == "owner@testrestaurant.nl"
            assert contact.source == "osm"
            assert contact.confidence_score == 90  # Direct email tag = 90
            assert contact.discovered_at is not None
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_osm_contact_email_tag_discovery():
    """Test that OSM contact:email tag is correctly detected with confidence score 85."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test Bakery",
        "Test Address 456",
        "bakery",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/789012",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Mock OSM Overpass API response with contact:email tag (no direct email tag)
        mock_response = create_mock_osm_response_with_contact_email("contact@testbakery.nl", "Test Bakery")
        
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client:
            # Setup mock client response
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_response_obj.status_code = 200
            
            # Setup async context manager pattern for httpx.AsyncClient
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            # Create service with low threshold to accept the email
            service = ContactDiscoveryService(confidence_threshold=50)
            
            # Discover contact
            contact = await service.discover_contact(location_id)
            
            # Verify results
            assert contact is not None
            assert isinstance(contact, ContactInfo)
            assert contact.email == "contact@testbakery.nl"
            assert contact.source == "osm"
            assert contact.confidence_score == 85  # contact:email tag = 85
            assert contact.discovered_at is not None
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_osm_email_tag_takes_precedence_over_contact_email():
    """Test that direct email tag is preferred over contact:email tag."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test Shop",
        "Test Address 789",
        "supermarket",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/345678",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Mock OSM response with both email and contact:email tags (email should be preferred)
        mock_response = {
            "elements": [{
                "type": "node",
                "id": 345678,
                "lat": 51.9244,
                "lon": 4.4777,
                "tags": {
                    "email": "owner@testshop.nl",
                    "contact:email": "contact@testshop.nl",
                    "name": "Test Shop"
                }
            }]
        }
        
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client:
            # Setup mock client response
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_response_obj.status_code = 200
            
            # Setup async context manager pattern for httpx.AsyncClient
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            service = ContactDiscoveryService(confidence_threshold=50)
            
            # Discover contact
            contact = await service.discover_contact(location_id)
            
            # Verify that direct email tag was used (higher confidence)
            assert contact is not None
            assert contact.email == "owner@testshop.nl"  # Direct email tag, not contact:email
            assert contact.confidence_score == 90  # Direct email = 90, not 85
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_confidence_scoring_generic_email_penalty():
    """Test that generic email addresses (info@, contact@) receive -10 penalty."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test Cafe",
        "Test Address Generic",
        "restaurant",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/111222",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Mock OSM response with generic email (info@)
        mock_response = create_mock_osm_response_with_email("info@testcafe.nl", "Test Cafe")
        
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client:
            # Setup mock client response
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_response_obj.status_code = 200
            
            # Setup async context manager pattern for httpx.AsyncClient
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            service = ContactDiscoveryService(confidence_threshold=50)
            
            # Discover contact
            contact = await service.discover_contact(location_id)
            
            # Verify penalty was applied
            assert contact is not None
            assert contact.email == "info@testcafe.nl"
            assert contact.confidence_score == 80  # 90 (base) - 10 (penalty) = 80
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_confidence_threshold_filtering():
    """Test that emails below confidence threshold are filtered out."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test Low Confidence",
        "Test Address Threshold",
        "restaurant",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/333444",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Mock OSM response with generic email (which gets penalty, resulting in score below threshold)
        mock_response = create_mock_osm_response_with_contact_email("contact@testlow.nl", "Test Low Confidence")
        
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client:
            # Setup mock client response
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_response_obj.status_code = 200
            
            # Setup async context manager pattern for httpx.AsyncClient
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            # Create service with high threshold (above the penalized score)
            # contact:email = 85, with contact@ penalty = 75, so threshold 80 should filter it out
            service = ContactDiscoveryService(confidence_threshold=80)
            
            # Discover contact
            contact = await service.discover_contact(location_id)
            
            # Verify that contact was filtered out (below threshold)
            assert contact is None  # 85 - 10 = 75 < 80 threshold
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_confidence_threshold_configuration_via_env():
    """Test that confidence threshold can be configured via environment variable."""
    # Test default threshold
    service_default = ContactDiscoveryService()
    assert service_default.confidence_threshold == 50  # Default from env or code
    
    # Test custom threshold
    service_custom = ContactDiscoveryService(confidence_threshold=75)
    assert service_custom.confidence_threshold == 75


async def test_no_contact_found_scenario():
    """Test scenario where no email tags are found in OSM."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test No Email",
        "Test Address No Email",
        "restaurant",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/555666",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Mock OSM response without email tags
        mock_response = create_mock_osm_response_no_email("Test No Email")
        
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client:
            # Setup mock client response
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_response_obj.status_code = 200
            
            # Setup async context manager pattern for httpx.AsyncClient
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            service = ContactDiscoveryService(confidence_threshold=50)
            
            # Discover contact
            contact = await service.discover_contact(location_id)
            
            # Verify no contact found
            assert contact is None
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_osm_empty_response():
    """Test scenario where OSM API returns empty elements list."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test Empty OSM",
        "Test Address Empty",
        "restaurant",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/777888",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Mock OSM response with empty elements
        mock_response = create_mock_osm_response_empty()
        
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client:
            # Setup mock client response
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_response_obj.status_code = 200
            
            # Setup async context manager pattern for httpx.AsyncClient
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            service = ContactDiscoveryService(confidence_threshold=50)
            
            # Discover contact
            contact = await service.discover_contact(location_id)
            
            # Verify no contact found
            assert contact is None
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_location_not_found():
    """Test error handling when location_id doesn't exist in database."""
    service = ContactDiscoveryService(confidence_threshold=50)
    
    # Try to discover contact for non-existent location
    contact = await service.discover_contact(99999999)
    
    # Verify no contact found (location doesn't exist)
    assert contact is None


async def test_location_without_coordinates():
    """Test error handling when location has no lat/lng coordinates."""
    # Create test location without coordinates
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        "Test No Coords",
        "Test Address No Coords",
        "restaurant",
        "VERIFIED",
        0.95,
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        service = ContactDiscoveryService(confidence_threshold=50)
        
        # Discover contact (should skip OSM query due to missing coordinates)
        contact = await service.discover_contact(location_id)
        
        # Verify no contact found (no coordinates, can't query OSM)
        assert contact is None
        
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_osm_api_error_handling():
    """Test error handling when OSM API returns an error."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test API Error",
        "Test Address Error",
        "restaurant",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/999000",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client:
            # Setup mock client to raise an exception
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=httpx.HTTPError("Network error"))
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            service = ContactDiscoveryService(confidence_threshold=50)
            
            # Discover contact (should handle error gracefully)
            contact = await service.discover_contact(location_id)
            
            # Verify no contact found (error was handled, returns None)
            assert contact is None
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_invalid_email_format_handling():
    """Test that invalid email formats are rejected."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test Invalid Email",
        "Test Address Invalid",
        "restaurant",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/111000",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Mock OSM response with invalid email format
        mock_response = {
            "elements": [{
                "type": "node",
                "id": 111000,
                "lat": 51.9244,
                "lon": 4.4777,
                "tags": {
                    "email": "not-an-email-address",  # Invalid format
                    "name": "Test Invalid Email"
                }
            }]
        }
        
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client:
            # Setup mock client response
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_response_obj.status_code = 200
            
            # Setup async context manager pattern for httpx.AsyncClient
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            service = ContactDiscoveryService(confidence_threshold=50)
            
            # Discover contact
            contact = await service.discover_contact(location_id)
            
            # Verify no contact found (invalid email format was rejected)
            assert contact is None
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_service_instantiation_with_custom_threshold():
    """Test that service can be instantiated with custom confidence threshold."""
    service = ContactDiscoveryService(confidence_threshold=75)
    assert service.confidence_threshold == 75
    assert service.osm_service is not None


async def test_get_contact_discovery_service_global_getter():
    """Test that global getter function returns service instance."""
    service = get_contact_discovery_service()
    assert service is not None
    assert isinstance(service, ContactDiscoveryService)
    
    # Should return same instance on subsequent calls (singleton pattern)
    service2 = get_contact_discovery_service()
    assert service is service2


async def test_service_integration_with_worker_pattern():
    """Test that service can be used by worker (mock integration test)."""
    # Create test location in database
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, lat, lng, place_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        "Test Worker Integration",
        "Test Address Worker",
        "restaurant",
        "VERIFIED",
        0.95,
        51.9244,
        4.4777,
        "node/222333",
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Mock OSM response
        mock_response = create_mock_osm_response_with_email("worker@testintegration.nl", "Test Worker Integration")
        
        with patch("services.contact_discovery_service.httpx.AsyncClient") as mock_client:
            # Setup mock client response
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_response_obj.status_code = 200
            
            # Setup async context manager pattern for httpx.AsyncClient
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()
            
            # Simulate worker usage pattern
            service = get_contact_discovery_service()
            contact = await service.discover_contact(location_id)
            
            # Verify worker can use the service successfully
            assert contact is not None
            assert contact.email == "worker@testintegration.nl"
            
            # Verify ContactInfo can be used to insert into outreach_contacts table
            # (This simulates what a worker would do)
            assert contact.email is not None
            assert contact.source is not None
            assert contact.confidence_score >= 0
            assert contact.confidence_score <= 100
            assert contact.discovered_at is not None
            
    finally:
        # Cleanup
        await execute("DELETE FROM locations WHERE id = $1", location_id)

