#!/usr/bin/env python3
"""
Fix missing discovery jobs - Create jobs for all (city, category) combinations.

This script identifies missing discovery jobs and creates them to ensure
all discoverable categories have jobs for all cities.

Usage:
    python -m scripts.fix_missing_discovery_jobs [--dry-run] [--categories cat1,cat2] [--cities city1,city2]
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Set, Optional, Dict, Any

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool, fetch
from services.discovery_jobs_service import enqueue_jobs
from services.cities_db_service import load_cities_config_from_db, get_districts_for_city
from app.models.categories import get_discoverable_categories
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="script")
logger = get_logger()


async def check_job_exists(city_key: str, category: str, district_key: Optional[str] = None) -> bool:
    """Check if a discovery job already exists."""
    await init_db_pool()
    
    if district_key is None:
        sql = """
            SELECT 1 FROM discovery_jobs
            WHERE city_key = $1 AND category = $2 AND district_key IS NULL
            LIMIT 1
        """
        rows = await fetch(sql, city_key, category)
    else:
        sql = """
            SELECT 1 FROM discovery_jobs
            WHERE city_key = $1 AND category = $2 AND district_key = $3
            LIMIT 1
        """
        rows = await fetch(sql, city_key, category, district_key)
    
    return len(rows) > 0


async def find_missing_jobs(
    cities: Dict[str, Any],
    categories: List[str],
    filter_cities: Optional[List[str]] = None,
    filter_categories: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Find missing (city, category) job combinations."""
    missing_city_level: List[Dict[str, str]] = []
    missing_district_level: List[Dict[str, str]] = []
    
    cities_to_process = filter_cities if filter_cities else list(cities.keys())
    categories_to_process = filter_categories if filter_categories else categories
    
    for city_key in cities_to_process:
        city_data = cities.get(city_key)
        if not city_data:
            continue
        
        # Check if city has districts
        districts = city_data.get("districts", {})
        
        if not districts:
            # City-level jobs (no districts)
            for category in categories_to_process:
                exists = await check_job_exists(city_key, category, None)
                if not exists:
                    missing_city_level.append({
                        "city_key": city_key,
                        "category": category,
                        "district_key": None
                    })
        else:
            # District-level jobs
            for district_key in districts.keys():
                for category in categories_to_process:
                    exists = await check_job_exists(city_key, category, district_key)
                    if not exists:
                        missing_district_level.append({
                            "city_key": city_key,
                            "category": category,
                            "district_key": district_key
                        })
    
    return {
        "city_level": missing_city_level,
        "district_level": missing_district_level,
        "total": len(missing_city_level) + len(missing_district_level)
    }


async def create_missing_jobs(missing: Dict[str, Any], dry_run: bool = False) -> Dict[str, int]:
    """Create missing jobs."""
    created = 0
    skipped = 0
    errors = 0
    
    # Group by city and category for efficient enqueueing
    city_level_by_city: Dict[str, Set[str]] = {}
    for item in missing["city_level"]:
        city = item["city_key"]
        category = item["category"]
        if city not in city_level_by_city:
            city_level_by_city[city] = set()
        city_level_by_city[city].add(category)
    
    # Create city-level jobs
    for city_key, categories_set in city_level_by_city.items():
        if dry_run:
            print(f"  [DRY-RUN] Would create city-level jobs for {city_key}: {', '.join(sorted(categories_set))}")
            created += len(categories_set)
        else:
            try:
                job_ids = await enqueue_jobs(
                    city_key=city_key,
                    categories=list(categories_set),
                    districts=None  # City-level
                )
                created += len(job_ids)
                print(f"  ✓ Created {len(job_ids)} city-level jobs for {city_key}")
            except Exception as e:
                errors += len(categories_set)
                print(f"  ✗ Failed to create jobs for {city_key}: {e}")
                logger.error("failed_to_create_city_jobs", city_key=city_key, error=str(e), exc_info=e)
    
    # Group district-level jobs by (city, district)
    district_level_by_city_district: Dict[tuple, Set[str]] = {}
    for item in missing["district_level"]:
        key = (item["city_key"], item["district_key"])
        category = item["category"]
        if key not in district_level_by_city_district:
            district_level_by_city_district[key] = set()
        district_level_by_city_district[key].add(category)
    
    # Create district-level jobs
    for (city_key, district_key), categories_set in district_level_by_city_district.items():
        if dry_run:
            print(f"  [DRY-RUN] Would create district-level jobs for {city_key}/{district_key}: {', '.join(sorted(categories_set))}")
            created += len(categories_set)
        else:
            try:
                job_ids = await enqueue_jobs(
                    city_key=city_key,
                    categories=list(categories_set),
                    districts=[district_key]
                )
                created += len(job_ids)
                print(f"  ✓ Created {len(job_ids)} district-level jobs for {city_key}/{district_key}")
            except Exception as e:
                errors += len(categories_set)
                print(f"  ✗ Failed to create jobs for {city_key}/{district_key}: {e}")
                logger.error("failed_to_create_district_jobs", city_key=city_key, district_key=district_key, error=str(e), exc_info=e)
    
    return {
        "created": created,
        "skipped": skipped,
        "errors": errors
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Fix missing discovery jobs for all cities and categories"
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating jobs"
    )
    ap.add_argument(
        "--categories",
        help="Comma-separated list of category keys to process (default: all discoverable)"
    )
    ap.add_argument(
        "--cities",
        help="Comma-separated list of city keys to process (default: all cities)"
    )
    return ap.parse_args()


async def main_async() -> None:
    args = parse_args()
    dry_run = args.dry_run
    
    print("\n" + "=" * 80)
    print("FIX MISSING DISCOVERY JOBS")
    print("=" * 80)
    if dry_run:
        print("\n[DRY-RUN MODE] No jobs will be created\n")
    
    # Initialize database
    print("1. Initializing database connection...")
    await init_db_pool()
    print("   ✓ Database connected\n")
    
    # Load cities from database
    print("2. Loading cities from database...")
    try:
        cities_config = await load_cities_config_from_db()
        cities = cities_config.get("cities", {})
        
        if not cities:
            print("   ✗ No cities found in database")
            return
        
        print(f"   ✓ Found {len(cities)} cities\n")
    except Exception as e:
        print(f"   ✗ Failed to load cities: {e}")
        logger.exception("failed_to_load_cities", error=str(e))
        return
    
    # Load discoverable categories
    print("3. Loading discoverable categories...")
    try:
        discoverable = get_discoverable_categories()
        all_category_keys = [c.key for c in discoverable]
        
        if not all_category_keys:
            print("   ✗ No discoverable categories found")
            return
        
        print(f"   ✓ Found {len(all_category_keys)} discoverable categories\n")
    except Exception as e:
        print(f"   ✗ Failed to load categories: {e}")
        logger.exception("failed_to_load_categories", error=str(e))
        return
    
    # Filter categories if specified
    categories_to_process = all_category_keys
    if args.categories:
        requested = [c.strip() for c in args.categories.split(",") if c.strip()]
        invalid = [c for c in requested if c not in all_category_keys]
        if invalid:
            print(f"   ✗ Invalid categories: {', '.join(invalid)}")
            print(f"   Available: {', '.join(all_category_keys)}")
            return
        categories_to_process = requested
        print(f"   → Processing {len(categories_to_process)} specified categories\n")
    
    # Filter cities if specified
    cities_to_process = None
    if args.cities:
        requested = [c.strip() for c in args.cities.split(",") if c.strip()]
        invalid = [c for c in requested if c not in cities]
        if invalid:
            print(f"   ✗ Invalid cities: {', '.join(invalid)}")
            print(f"   Available: {', '.join(sorted(cities.keys()))}")
            return
        cities_to_process = requested
        print(f"   → Processing {len(cities_to_process)} specified cities\n")
    
    # Find missing jobs
    print("4. Finding missing jobs...")
    try:
        missing = await find_missing_jobs(
            cities=cities,
            categories=categories_to_process,
            filter_cities=cities_to_process,
            filter_categories=None  # Already filtered above
        )
        
        print(f"   ✓ Analysis complete:")
        print(f"     - Missing city-level jobs: {len(missing['city_level'])}")
        print(f"     - Missing district-level jobs: {len(missing['district_level'])}")
        print(f"     - Total missing: {missing['total']}\n")
        
        if missing['total'] == 0:
            print("   ✓ No missing jobs found! All combinations already exist.\n")
            return
        
    except Exception as e:
        print(f"   ✗ Failed to find missing jobs: {e}")
        logger.exception("failed_to_find_missing_jobs", error=str(e))
        return
    
    # Create missing jobs
    print("5. Creating missing jobs...")
    try:
        results = await create_missing_jobs(missing, dry_run=dry_run)
        
        print(f"\n   Summary:")
        print(f"     - Jobs {'would be ' if dry_run else ''}created: {results['created']}")
        print(f"     - Skipped: {results['skipped']}")
        if results['errors'] > 0:
            print(f"     - Errors: {results['errors']}")
        print()
        
    except Exception as e:
        print(f"   ✗ Failed to create jobs: {e}")
        logger.exception("failed_to_create_jobs", error=str(e))
        return
    
    print("=" * 80)
    if dry_run:
        print("\n[DRY-RUN] Run without --dry-run to actually create the jobs\n")
    else:
        print("\n✓ Fix complete! Run analyze_discovery_categories.py to verify.\n")
    print("=" * 80)


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\nFix interrupted by user.")
    except Exception as e:
        print(f"\n\n✗ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

