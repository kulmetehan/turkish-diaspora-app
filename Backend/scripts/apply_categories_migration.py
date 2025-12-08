#!/usr/bin/env python3
"""
Apply categories_config table migration.

This script runs the SQL migration to create the categories_config table.
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

from services.db_service import init_db_pool, execute
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="script")
logger = get_logger()


async def apply_migration():
    """Apply the categories_config migration."""
    print("\n=== Applying Categories Config Migration ===\n")
    
    # Initialize database
    print("1. Initializing database connection...")
    await init_db_pool()
    print("   ✓ Database connected\n")
    
    # Read SQL file
    sql_file = REPO_ROOT / "Infra" / "supabase" / "044_categories_config.sql"
    if not sql_file.exists():
        print(f"   ✗ SQL file not found: {sql_file}")
        return
    
    print("2. Reading SQL migration file...")
    sql_content = sql_file.read_text(encoding="utf-8")
    print(f"   ✓ Read {len(sql_content)} bytes from {sql_file.name}\n")
    
    # Execute SQL
    print("3. Applying migration...")
    try:
        result = await execute(sql_content)
        print("   ✓ Migration applied successfully\n")
    except Exception as e:
        # Check if table already exists (that's okay)
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("   ⚠ Table or indexes already exist (migration may have been run before)")
            print("   ✓ Migration check complete\n")
        else:
            print(f"   ✗ Migration failed: {e}")
            logger.exception("migration_failed", error=str(e))
            return
    
    # Verify table exists
    print("4. Verifying table creation...")
    try:
        check_sql = """
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'categories_config'
        """
        from services.db_service import fetchrow
        row = await fetchrow(check_sql)
        if row and row.get("count", 0) > 0:
            print("   ✓ Table 'categories_config' exists\n")
        else:
            print("   ⚠ Table 'categories_config' not found\n")
    except Exception as e:
        print(f"   ⚠ Could not verify table: {e}\n")
    
    print("=== Migration Complete ===\n")


if __name__ == "__main__":
    try:
        asyncio.run(apply_migration())
    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user.")
    except Exception as e:
        print(f"\n\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

