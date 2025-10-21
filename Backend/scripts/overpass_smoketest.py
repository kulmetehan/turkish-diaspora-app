#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Overpass Smoketest — Test OSM provider with a single bakery query in Rotterdam
- Tests OsmPlacesService with real Overpass API
- Validates query syntax and response parsing
- Returns appropriate exit codes for different failure modes
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add Backend to path for imports
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from services.osm_service import OsmPlacesService


async def main():
    """Run the smoketest."""
    print("SMOKETEST START (bakery @ Rotterdam, r=1000)")
    
    try:
        # Initialize OSM service
        osm_service = OsmPlacesService()
        
        # Test query for bakeries in Rotterdam
        results = await osm_service.search_nearby(
            lat=51.9244,
            lng=4.4777,
            radius=1000,
            included_types=["bakery"],
            max_results=20,
            language="nl"
        )
        
        print(f"results: {len(results)}")
        
        # Print first 3 items
        for i, item in enumerate(results[:3]):
            print(f"{i+1}. {item.get('id', 'N/A')} | {item.get('displayName', {}).get('text', 'N/A')} | {item.get('formattedAddress', 'N/A')}")
        
        # Cleanup
        await osm_service.aclose()
        
        # Exit code based on results
        if len(results) >= 1:
            print("✅ Smoketest PASSED")
            return 0
        else:
            print("❌ Smoketest FAILED: No results returned")
            return 1
            
    except RuntimeError as e:
        if "Overpass 400" in str(e):
            print("❌ Overpass 400 – likely syntax. Full query logged.")
            return 2
        else:
            print(f"❌ Runtime error: {e}")
            return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
