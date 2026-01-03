#!/usr/bin/env python3
"""
Backfill category_key for existing activity_stream records.

This script updates all existing activity_stream records that have a location_id
but no category_key, by copying the category from the locations table.
This ensures that all existing check-ins and other activities show category images.
"""

import asyncio
import sys
from pathlib import Path

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
REPO_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool, execute, fetch
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="script")
logger = get_logger()


async def backfill_category_key():
    """Backfill category_key for existing activity_stream records."""
    print("\n=== Backfilling Activity Stream Category Key ===\n")
    
    # Initialize database
    print("1. Initializing database connection...")
    await init_db_pool()
    print("   ✓ Database connected\n")
    
    # Check how many records need updating
    print("2. Checking records that need updating...")
    check_sql = """
        SELECT COUNT(*) as count
        FROM activity_stream ast
        JOIN locations l ON ast.location_id = l.id
        WHERE ast.category_key IS NULL
          AND ast.location_id IS NOT NULL
          AND l.category IS NOT NULL
    """
    try:
        rows = await fetch(check_sql)
        count = rows[0]["count"] if rows else 0
        print(f"   ✓ Found {count} records that need updating\n")
        
        if count == 0:
            print("   ℹ No records need updating. All done!\n")
            return
    except Exception as e:
        print(f"   ✗ Failed to check records: {e}")
        logger.exception("check_failed", error=str(e))
        return
    
    # Read SQL file
    sql_file = REPO_ROOT / "Infra" / "supabase" / "098_backfill_activity_stream_category_key.sql"
    if not sql_file.exists():
        print(f"   ✗ SQL file not found: {sql_file}")
        return
    
    print("3. Reading SQL migration file...")
    sql_content = sql_file.read_text(encoding="utf-8")
    print(f"   ✓ Read {len(sql_content)} bytes from {sql_file.name}\n")
    
    # Execute SQL
    print("4. Applying backfill update...")
    try:
        result = await execute(sql_content)
        print("   ✓ Backfill completed successfully\n")
    except Exception as e:
        print(f"   ✗ Backfill failed: {e}")
        logger.exception("backfill_failed", error=str(e))
        return
    
    # Verify update
    print("5. Verifying update...")
    try:
        verify_sql = """
            SELECT COUNT(*) as count
            FROM activity_stream ast
            JOIN locations l ON ast.location_id = l.id
            WHERE ast.category_key IS NULL
              AND ast.location_id IS NOT NULL
              AND l.category IS NOT NULL
        """
        rows = await fetch(verify_sql)
        remaining = rows[0]["count"] if rows else 0
        
        if remaining == 0:
            print("   ✓ All records updated successfully\n")
        else:
            print(f"   ⚠ {remaining} records still need updating (may have NULL categories in locations table)\n")
    except Exception as e:
        print(f"   ⚠ Verification failed: {e}")
        logger.exception("verification_failed", error=str(e))
    
    print("=== Backfill Complete ===\n")


if __name__ == "__main__":
    asyncio.run(backfill_category_key())



