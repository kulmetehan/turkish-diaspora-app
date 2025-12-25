# Backend/services/mapview_link_service.py
"""
Service for generating mapview links with location focus.

Generates URLs that automatically focus on a location in the mapview
and open the tooltip when clicked from email links.
"""

from __future__ import annotations

import os


def generate_mapview_link(location_id: int | str, location_lat: float | None = None, location_lng: float | None = None) -> str:
    """
    Generate a mapview link that focuses on a specific location.
    
    The generated link will automatically center the map on the location
    and open the tooltip when accessed from an email link.
    
    Args:
        location_id: ID of the location to focus on
        location_lat: Latitude of the location (optional, not used in current implementation)
        location_lng: Longitude of the location (optional, not used in current implementation)
        
    Returns:
        URL string in format: {frontend_url}/#/map?focus={location_id}
        
    Example:
        >>> link = generate_mapview_link(123)
        >>> link
        'https://turkspot.nl/#/map?focus=123'
    """
    frontend_url = os.getenv("FRONTEND_URL", "https://turkspot.nl")
    
    # The frontend supports focus parameter via viewMode.ts
    # Format: /#/map?focus={location_id}
    return f"{frontend_url}/#/map?focus={location_id}"


def get_mapview_link_service():
    """
    Get the mapview link service instance.
    
    Returns:
        Module-level functions for mapview link generation
    """
    return {
        "generate_mapview_link": generate_mapview_link,
    }

