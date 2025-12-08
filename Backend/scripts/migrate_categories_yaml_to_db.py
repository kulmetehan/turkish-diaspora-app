"""
Migration script: Copy categories configuration from YAML to database.

This script reads the current categories.yml file and migrates all categories
to the database table (categories_config).

Usage:
    python -m scripts.migrate_categories_yaml_to_db

The script is idempotent - it can be run multiple times safely.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.workers.discovery_bot import load_categories_config
from services.db_service import init_db_pool
from services.categories_db_service import (
    save_category_to_db,
    load_categories_config_from_db,
)

async def main():
    """Migrate categories from YAML to database."""
    print("\n=== Categories YAML to Database Migration ===\n")
    
    # Initialize database
    print("1. Initializing database connection...")
    await init_db_pool()
    print("   ✓ Database connected\n")
    
    # Load categories from YAML
    print("2. Loading categories from YAML...")
    try:
        yaml_config = load_categories_config()
        categories = yaml_config.get("categories", {})
        
        if not categories:
            print("   ⚠ No categories found in YAML file")
            return
        
        print(f"   ✓ Found {len(categories)} categories in YAML\n")
    except Exception as e:
        print(f"   ✗ Failed to load categories from YAML: {e}")
        return
    
    # Migrate each category
    print("3. Migrating categories to database...")
    migrated_categories = 0
    errors = []
    
    for category_key, category_data in categories.items():
        try:
            # Save category (this handles INSERT or UPDATE)
            await save_category_to_db(category_key, category_data)
            migrated_categories += 1
            
            label = category_data.get("label", category_key)
            discovery_enabled = category_data.get("discovery", {}).get("enabled", True)
            status = "discoverable" if discovery_enabled else "non-discoverable"
            print(f"   ✓ {category_key:20s} ({label:30s}) - {status}")
        except Exception as e:
            error_msg = f"{category_key}: {e}"
            errors.append(error_msg)
            print(f"   ✗ {error_msg}")
    
    print(f"\n   Migration summary:")
    print(f"   - Categories migrated: {migrated_categories}/{len(categories)}")
    if errors:
        print(f"   - Errors: {len(errors)}")
    
    # Verify migration
    print("\n4. Verifying migration...")
    try:
        db_config = await load_categories_config_from_db()
        db_categories = db_config.get("categories", {})
        
        if len(db_categories) == len(categories):
            print(f"   ✓ Verification passed: {len(db_categories)} categories in database")
            
            # Check discoverable count
            discoverable_yaml = sum(
                1 for cat in categories.values()
                if isinstance(cat, dict) and cat.get("discovery", {}).get("enabled", True)
            )
            discoverable_db = sum(
                1 for cat in db_categories.values()
                if isinstance(cat, dict) and cat.get("discovery", {}).get("enabled", True)
            )
            
            if discoverable_db == discoverable_yaml:
                print(f"   ✓ Discoverable count verified: {discoverable_db} discoverable categories")
            else:
                print(f"   ⚠ Discoverable count mismatch: expected {discoverable_yaml}, got {discoverable_db}")
        else:
            print(f"   ⚠ Category count mismatch: expected {len(categories)}, got {len(db_categories)}")
            
    except Exception as e:
        print(f"   ✗ Verification failed: {e}")
    
    # Print errors if any
    if errors:
        print("\n⚠ Errors occurred during migration:")
        for error in errors:
            print(f"   - {error}")
        print("\nYou may need to fix these manually.")
    
    print("\n=== Migration Complete ===\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user.")
    except Exception as e:
        print(f"\n\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

