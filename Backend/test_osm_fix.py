#!/usr/bin/env python3
"""
Quick test script to validate OSM service fixes.
Run this to test the defensive JSON parsing and error handling.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add Backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from services.osm_service import OsmPlacesService

async def test_osm_service():
    """Test OSM service with defensive parsing."""
    print("Testing OSM service with defensive JSON parsing...")
    
    # Set up environment for testing
    os.environ.setdefault("OVERPASS_USER_AGENT", "TurkishDiasporaApp/1.0 (contact: m.kul@lamarka.nl)")
    os.environ.setdefault("DISCOVERY_RATE_LIMIT_QPS", "0.5")  # Faster for testing
    os.environ.setdefault("DISCOVERY_SLEEP_BASE_S", "1.0")    # Shorter sleep for testing
    os.environ.setdefault("OVERPASS_TIMEOUT_S", "30")
    os.environ.setdefault("DISCOVERY_MAX_RESULTS", "10")
    os.environ.setdefault("OSM_TRACE", "1")  # Enable tracing
    
    # Initialize OSM service
    osm_service = OsmPlacesService(
        max_results=10,
        turkish_hints=True
    )
    
    try:
        # Test with a small area in Rotterdam
        print("Testing search_nearby...")
        results, needs_subdivision = await osm_service.search_nearby(
            lat=51.9244,
            lng=4.4777,
            radius=500,
            included_types=["restaurant"],
            max_results=10
        )
        
        print(f"Found {len(results)} results, needs_subdivision: {needs_subdivision}")
        
        # Test subdivision if needed
        if needs_subdivision:
            print("Testing search_nearby_with_subdivision...")
            subdivision_results = await osm_service.search_nearby_with_subdivision(
                lat=51.9244,
                lng=4.4777,
                radius=500,
                included_types=["restaurant"],
                max_results=10
            )
            print(f"Subdivision found {len(subdivision_results)} results")
        
        print("✅ OSM service test completed successfully!")
        
    except Exception as e:
        print(f"❌ OSM service test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await osm_service.aclose()

if __name__ == "__main__":
    asyncio.run(test_osm_service())
