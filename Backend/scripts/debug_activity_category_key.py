#!/usr/bin/env python3
"""
Debug script to check category_key values in activity_stream for check-ins.
"""

import asyncio
import sys
from pathlib import Path

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool, fetch
from app.core.logging import configure_logging

configure_logging(service_name="script")


async def debug_category_key():
    """Check category_key values in activity_stream."""
    print("\n=== Debugging Activity Stream Category Key ===\n")
    
    await init_db_pool()
    
    # Check check-ins with category_key
    sql = """
        SELECT 
            ast.id,
            ast.activity_type,
            ast.location_id,
            ast.category_key,
            l.name as location_name,
            l.category as location_category,
            ast.created_at
        FROM activity_stream ast
        LEFT JOIN locations l ON ast.location_id = l.id
        WHERE ast.activity_type = 'check_in'
        ORDER BY ast.created_at DESC
        LIMIT 20
    """
    
    rows = await fetch(sql)
    
    print(f"Found {len(rows)} recent check-ins:\n")
    
    for row in rows:
        print(f"ID: {row['id']}")
        print(f"  Location: {row.get('location_name', 'N/A')}")
        print(f"  Location Category: {row.get('location_category', 'NULL')}")
        print(f"  Activity Stream category_key: {row.get('category_key', 'NULL')}")
        print(f"  Created: {row.get('created_at')}")
        print()
    
    # Count check-ins with and without category_key
    count_sql = """
        SELECT 
            COUNT(*) FILTER (WHERE category_key IS NOT NULL) as with_category,
            COUNT(*) FILTER (WHERE category_key IS NULL) as without_category,
            COUNT(*) FILTER (WHERE category_key IS NULL AND location_id IS NOT NULL) as without_category_with_location
        FROM activity_stream
        WHERE activity_type = 'check_in'
    """
    
    count_rows = await fetch(count_sql)
    if count_rows:
        row = count_rows[0]
        print("\nSummary:")
        print(f"  Check-ins with category_key: {row.get('with_category', 0)}")
        print(f"  Check-ins without category_key: {row.get('without_category', 0)}")
        print(f"  Check-ins without category_key but with location: {row.get('without_category_with_location', 0)}")
    
    print("\n=== Debug Complete ===\n")


if __name__ == "__main__":
    asyncio.run(debug_category_key())



