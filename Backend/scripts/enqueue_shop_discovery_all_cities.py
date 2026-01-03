#!/usr/bin/env python3
"""
Enqueue discovery jobs for the "shop" category across all cities and districts.

Reads cities.yml and enqueues discovery jobs for the "shop" category for all
cities and their districts (or city-level if no districts are defined).

Usage:
    python -m scripts.enqueue_shop_discovery_all_cities
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

from services.db_service import init_db_pool
from services.discovery_jobs_service import enqueue_jobs
from app.workers.discovery_bot import load_cities_config
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="script")
logger = get_logger()


async def main_async() -> None:
    """Enqueue shop discovery jobs for all cities and districts."""
    await init_db_pool()
    
    # Load cities config
    try:
        cities_config = load_cities_config()
        cities = cities_config.get("cities", {})
        
        if not cities:
            print("ERROR: No cities found in cities.yml")
            sys.exit(1)
        
        print(f"\n[EnqueueShopJobs] Found {len(cities)} cities in cities.yml")
        print(f"[EnqueueShopJobs] Category: shop")
        print(f"[EnqueueShopJobs] Starting job enqueueing...\n")
        
    except Exception as e:
        print(f"ERROR: Failed to load cities.yml: {e}")
        logger.exception("load_cities_config_failed", error=str(e))
        sys.exit(1)
    
    total_jobs_created = 0
    cities_processed = 0
    cities_failed = 0
    
    # Process each city
    for city_key, city_def in cities.items():
        city_name = city_def.get("city_name", city_key)
        print(f"[EnqueueShopJobs] Processing: {city_name} ({city_key})")
        
        try:
            # Determine districts
            districts_dict = city_def.get("districts", {})
            if districts_dict:
                districts = list(districts_dict.keys())
                print(f"  Districts: {len(districts)} ({', '.join(districts[:5])}{'...' if len(districts) > 5 else ''})")
            else:
                districts = None
                print(f"  No districts - creating city-level jobs")
            
            # Enqueue jobs for shop category only
            job_ids = await enqueue_jobs(
                city_key=city_key,
                categories=["shop"],
                districts=districts,
            )
            
            # Calculate expected job count
            if districts is None:
                expected_count = 1  # One job for city-level
            else:
                expected_count = len(districts)  # One job per district
            
            if len(job_ids) != expected_count:
                print(f"  WARNING: Expected {expected_count} jobs but created {len(job_ids)}")
            else:
                print(f"  ✓ Created {len(job_ids)} job(s) successfully")
            
            total_jobs_created += len(job_ids)
            cities_processed += 1
            
        except Exception as e:
            print(f"  ✗ ERROR: Failed to enqueue jobs for {city_name}: {e}")
            logger.exception(
                "enqueue_jobs_failed",
                city_key=city_key,
                city_name=city_name,
                error=str(e)
            )
            cities_failed += 1
            continue
    
    # Print summary
    print(f"\n[EnqueueShopJobs] ===== SUMMARY =====")
    print(f"[EnqueueShopJobs] Cities processed: {cities_processed}")
    print(f"[EnqueueShopJobs] Cities failed: {cities_failed}")
    print(f"[EnqueueShopJobs] Total jobs created: {total_jobs_created}")
    print(f"[EnqueueShopJobs] Category: shop")
    
    if cities_failed > 0:
        print(f"\n[EnqueueShopJobs] WARNING: {cities_failed} city/cities failed. Check logs for details.")
        sys.exit(1)
    else:
        print(f"\n[EnqueueShopJobs] All jobs enqueued successfully!")


def main():
    """Main entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[EnqueueShopJobs] Interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n[EnqueueShopJobs] ERROR: {e}")
        logger.exception("enqueue_shop_discovery_all_cities_failed", error=str(e))
        raise


if __name__ == "__main__":
    main()







