# -*- coding: utf-8 -*-
"""
Provider Factory — OSM Overpass provider only
- Returns OSM service instance for cost-effective discovery
- No Google API dependencies to avoid costs
"""

from __future__ import annotations

from services.osm_service import OsmPlacesService


def get_places_provider() -> OsmPlacesService:
    """
    Get the OSM places provider for free, open-source discovery.
    
    Returns:
        OsmPlacesService - OSM Overpass API service
        
    Note:
        Google Places API support has been removed to avoid costs.
        All discovery now uses the free OSM Overpass API.
    """
    return OsmPlacesService()
