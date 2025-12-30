#!/usr/bin/env python3
"""
Quick script to check if bot activity is in activity_stream
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import sys

THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool, fetch

async def main():
    await init_db_pool()
    
    # Check unprocessed bot activity
    sql = """
        SELECT 
            'check_ins' as table_name,
            COUNT(*) as unprocessed_count
        FROM check_ins ci
        INNER JOIN user_profiles up ON ci.user_id = up.id
        WHERE up.is_bot = true
          AND ci.processed_in_activity_stream = false
        UNION ALL
        SELECT 'location_notes', COUNT(*)
        FROM location_notes ln
        INNER JOIN user_profiles up ON ln.user_id = up.id
        WHERE up.is_bot = true
          AND ln.processed_in_activity_stream = false
        UNION ALL
        SELECT 'location_reactions', COUNT(*)
        FROM location_reactions lr
        INNER JOIN user_profiles up ON lr.user_id = up.id
        WHERE up.is_bot = true
          AND lr.processed_in_activity_stream = false
        UNION ALL
        SELECT 'favorites', COUNT(*)
        FROM favorites f
        INNER JOIN user_profiles up ON f.user_id = up.id
        WHERE up.is_bot = true
          AND f.processed_in_activity_stream = false
    """
    
    rows = await fetch(sql)
    print("\n📊 Unprocessed bot activity:")
    for row in rows:
        print(f"   {row['table_name']}: {row['unprocessed_count']} items")
    
    # Check activity_stream entries
    sql2 = """
        SELECT 
            activity_type,
            COUNT(*) as count
        FROM activity_stream ast
        INNER JOIN user_profiles up ON ast.actor_id = up.id
        WHERE up.is_bot = true
        GROUP BY activity_type
        ORDER BY activity_type
    """
    
    rows2 = await fetch(sql2)
    print("\n✅ Bot activity in activity_stream:")
    total = 0
    for row in rows2:
        print(f"   {row['activity_type']}: {row['count']} items")
        total += row['count']
    
    if total == 0:
        print("\n⚠️  No bot activity found in activity_stream!")
        print("   Run the activity_stream_ingest_worker to process bot activity.")
    else:
        print(f"\n   Total: {total} items")

if __name__ == "__main__":
    asyncio.run(main())

