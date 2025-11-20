#!/usr/bin/env python3
"""
Helper script to enqueue discovery jobs for a city.

Reads cities.yml and categories.yml to create jobs for all (city, district, category) combinations.

Usage:
    python -m scripts.enqueue_discovery_jobs --city rotterdam
    python -m scripts.enqueue_discovery_jobs --city vlaardingen
    python -m scripts.enqueue_discovery_jobs --city schiedam
    python -m scripts.enqueue_discovery_jobs --city rotterdam --categories restaurant,bakery
    python -m scripts.enqueue_discovery_jobs --city rotterdam --districts centrum,noord
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool
from services.discovery_jobs_service import enqueue_jobs
from app.workers.discovery_bot import load_cities_config, load_categories_config
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="script")
logger = get_logger()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Enqueue discovery jobs for a city from cities.yml and categories.yml"
    )
    ap.add_argument(
        "--city",
        required=True,
        help="City key from cities.yml (e.g., rotterdam, vlaardingen, schiedam)"
    )
    ap.add_argument(
        "--categories",
        help="Comma-separated category keys (default: all discoverable categories from categories.yml)"
    )
    ap.add_argument(
        "--districts",
        help="Comma-separated district keys (default: all districts for the city, or city-level if no districts)"
    )
    return ap.parse_args()


async def main_async() -> None:
    args = parse_args()
    city_key = args.city.strip().lower()
    
    await init_db_pool()
    
    # Load cities config
    try:
        cities_config = load_cities_config()
        cities = cities_config.get("cities", {})
        city_def = cities.get(city_key)
        
        if not city_def:
            print(f"ERROR: City '{city_key}' not found in cities.yml")
            print(f"Available cities: {', '.join(cities.keys())}")
            sys.exit(1)
        
        city_name = city_def.get("city_name", city_key)
        print(f"\n[EnqueueJobs] City: {city_name} ({city_key})")
    except Exception as e:
        print(f"ERROR: Failed to load cities.yml: {e}")
        sys.exit(1)
    
    # Determine districts
    districts: list[str] | None = None
    if args.districts:
        districts = [d.strip() for d in args.districts.split(",") if d.strip()]
        print(f"[EnqueueJobs] Districts: {', '.join(districts)}")
    else:
        # Auto-detect districts from cities.yml
        districts_dict = city_def.get("districts", {})
        if districts_dict:
            districts = list(districts_dict.keys())
            print(f"[EnqueueJobs] Auto-detected districts: {', '.join(districts)}")
        else:
            districts = None
            print(f"[EnqueueJobs] No districts defined - will create city-level jobs")
    
    # Load categories config
    try:
        categories_config = load_categories_config()
        all_categories = categories_config.get("categories", {})
        
        # Filter to discoverable categories
        discoverable_categories = [
            key
            for key, cat_def in all_categories.items()
            if isinstance(cat_def, dict) and cat_def.get("discovery", {}).get("enabled", True)
        ]
        
        if args.categories:
            # Use specified categories
            requested_categories = [c.strip() for c in args.categories.split(",") if c.strip()]
            # Validate
            invalid = [c for c in requested_categories if c not in all_categories]
            if invalid:
                print(f"ERROR: Invalid categories: {', '.join(invalid)}")
                print(f"Available categories: {', '.join(all_categories.keys())}")
                sys.exit(1)
            categories = requested_categories
        else:
            # Use all discoverable categories
            categories = discoverable_categories
        
        print(f"[EnqueueJobs] Categories: {', '.join(categories)}")
    except Exception as e:
        print(f"ERROR: Failed to load categories.yml: {e}")
        sys.exit(1)
    
    # Enqueue jobs
    try:
        job_ids = await enqueue_jobs(
            city_key=city_key,
            categories=categories,
            districts=districts,
        )
        
        print(f"\n[EnqueueJobs] Successfully enqueued {len(job_ids)} job(s)")
        print(f"[EnqueueJobs] Job IDs: {', '.join(str(jid) for jid in job_ids[:10])}" + ("..." if len(job_ids) > 10 else ""))
        
        # Calculate expected job count
        if districts is None:
            expected_count = len(categories)
        else:
            expected_count = len(districts) * len(categories)
        
        if len(job_ids) != expected_count:
            print(f"WARNING: Expected {expected_count} jobs but created {len(job_ids)}")
        else:
            print(f"[EnqueueJobs] All {expected_count} expected jobs created successfully")
    
    except Exception as e:
        print(f"ERROR: Failed to enqueue jobs: {e}")
        logger.exception("enqueue_jobs_failed", city_key=city_key, error=str(e))
        sys.exit(1)


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[EnqueueJobs] Interrupted by user.")
    except Exception as e:
        print(f"\n[EnqueueJobs] ERROR: {e}")
        raise


if __name__ == "__main__":
    main()


