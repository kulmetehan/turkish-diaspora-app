"""
Migration script: Copy cities configuration from YAML to database.

This script reads the current cities.yml file and migrates all cities
and districts to the database tables (cities_config and districts_config).

Usage:
    python -m scripts.migrate_cities_yaml_to_db

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

from app.workers.discovery_bot import load_cities_config
from services.db_service import init_db_pool
from services.cities_db_service import (
    save_city_to_db,
    load_cities_config_from_db,
)

async def main():
    """Migrate cities from YAML to database."""
    print("\n=== Cities YAML to Database Migration ===\n")
    
    # Initialize database
    print("1. Initializing database connection...")
    await init_db_pool()
    print("   ✓ Database connected\n")
    
    # Load cities from YAML
    print("2. Loading cities from YAML...")
    try:
        yaml_config = load_cities_config()
        cities = yaml_config.get("cities", {})
        
        if not cities:
            print("   ⚠ No cities found in YAML file")
            return
        
        print(f"   ✓ Found {len(cities)} cities in YAML\n")
    except Exception as e:
        print(f"   ✗ Failed to load cities from YAML: {e}")
        return
    
    # Migrate each city
    print("3. Migrating cities to database...")
    migrated_cities = 0
    migrated_districts = 0
    errors = []
    
    for city_key, city_data in cities.items():
        try:
            # Count districts
            districts = city_data.get("districts", {})
            district_count = len(districts) if isinstance(districts, dict) else 0
            
            # Save city (this will also save districts if provided)
            await save_city_to_db(city_key, city_data)
            migrated_cities += 1
            migrated_districts += district_count
            
            print(f"   ✓ {city_key}: {city_data.get('city_name', city_key)} ({district_count} districts)")
        except Exception as e:
            error_msg = f"{city_key}: {e}"
            errors.append(error_msg)
            print(f"   ✗ {error_msg}")
    
    print(f"\n   Migration summary:")
    print(f"   - Cities migrated: {migrated_cities}/{len(cities)}")
    print(f"   - Total districts migrated: {migrated_districts}")
    if errors:
        print(f"   - Errors: {len(errors)}")
    
    # Verify migration
    print("\n4. Verifying migration...")
    try:
        db_config = await load_cities_config_from_db()
        db_cities = db_config.get("cities", {})
        
        if len(db_cities) == len(cities):
            print(f"   ✓ Verification passed: {len(db_cities)} cities in database")
            
            # Check districts
            total_db_districts = sum(
                len(city.get("districts", {}))
                for city in db_cities.values()
            )
            if total_db_districts == migrated_districts:
                print(f"   ✓ Districts verified: {total_db_districts} districts in database")
            else:
                print(f"   ⚠ District count mismatch: expected {migrated_districts}, got {total_db_districts}")
        else:
            print(f"   ⚠ City count mismatch: expected {len(cities)}, got {len(db_cities)}")
            
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

