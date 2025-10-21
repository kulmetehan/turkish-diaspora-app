# -*- coding: utf-8 -*-
"""
Provider Factory — Switch between Google Places and OSM Overpass providers
- Environment-driven provider selection
- Returns appropriate service instance based on DATA_PROVIDER env var
"""

from __future__ import annotations

import os
from typing import Any, Union

from services.google_service import GooglePlacesService
from services.osm_service import OsmPlacesService


def get_places_provider() -> Union[GooglePlacesService, OsmPlacesService]:
    """
    Get the appropriate places provider based on environment configuration.
    
    Returns:
        GooglePlacesService if DATA_PROVIDER=google (default)
        OsmPlacesService if DATA_PROVIDER=osm
        
    Raises:
        ValueError: If DATA_PROVIDER is set to an unsupported value
    """
    provider = os.getenv("DATA_PROVIDER", "google").lower().strip()
    
    if provider == "google":
        from app.config import settings
        return GooglePlacesService(api_key=settings.GOOGLE_API_KEY)
    elif provider == "osm":
        return OsmPlacesService()
    else:
        raise ValueError(
            f"Unsupported DATA_PROVIDER: {provider}. "
            f"Supported values: 'google', 'osm'"
        )
