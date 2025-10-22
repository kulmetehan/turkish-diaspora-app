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
        GooglePlacesService if DATA_PROVIDER=google
        OsmPlacesService if DATA_PROVIDER=osm (default)
        
    Raises:
        ValueError: If DATA_PROVIDER is set to an unsupported value
    """
    # Default to OSM to avoid accidental paid Google usage
    provider = os.getenv("DATA_PROVIDER", "osm").lower().strip()
    
    if provider == "google":
        # Guard against missing key to prevent unintended paid calls
        from app.config import settings
        api_key = settings.GOOGLE_API_KEY
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not set but DATA_PROVIDER=google. "
                "Set DATA_PROVIDER=osm to use the free Overpass API or provide a key."
            )
        return GooglePlacesService(api_key=api_key)
    elif provider == "osm":
        return OsmPlacesService()
    else:
        raise ValueError(
            f"Unsupported DATA_PROVIDER: {provider}. "
            f"Supported values: 'google', 'osm'"
        )
