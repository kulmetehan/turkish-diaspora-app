#!/usr/bin/env python3
"""
Analyze discovery categories usage - compares YAML config with actual discovery_jobs.

This script helps identify:
1. Which categories are actually used in discovery_jobs
2. Which categories from YAML are missing from jobs
3. Which categories in jobs don't exist in YAML
4. Category distribution across cities/districts

Usage:
    python -m scripts.analyze_discovery_categories
"""

import asyncio
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Set, Any

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool, fetch
from app.workers.discovery_bot import load_categories_config
from app.models.categories import get_discoverable_categories, get_all_categories
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="script")
logger = get_logger()


async def analyze_discovery_jobs() -> Dict[str, Any]:
    """Analyze discovery_jobs table to see which categories are actually used."""
    await init_db_pool()
    
    # Get all jobs with their categories
    sql = """
        SELECT 
            category,
            city_key,
            district_key,
            status,
            COUNT(*) as job_count
        FROM discovery_jobs
        GROUP BY category, city_key, district_key, status
        ORDER BY category, city_key, district_key
    """
    rows = await fetch(sql)
    
    # Aggregate data
    category_stats = defaultdict(lambda: {
        "total_jobs": 0,
        "by_status": Counter(),
        "by_city": Counter(),
        "cities": set(),
        "districts": set(),
    })
    
    all_categories_in_jobs: Set[str] = set()
    
    for row in rows:
        row_dict = dict(row)
        category = row_dict["category"]
        city = row_dict["city_key"]
        district = row_dict.get("district_key")
        status = row_dict["status"]
        job_count = int(row_dict["job_count"])
        
        all_categories_in_jobs.add(category)
        
        stats = category_stats[category]
        stats["total_jobs"] += job_count
        stats["by_status"][status] += job_count
        stats["by_city"][city] += job_count
        stats["cities"].add(city)
        if district:
            stats["districts"].add(f"{city}:{district}")
    
    return {
        "categories_in_jobs": all_categories_in_jobs,
        "category_stats": dict(category_stats),
    }


def analyze_yaml_categories() -> Dict[str, Any]:
    """Analyze categories from YAML config."""
    try:
        categories_config = load_categories_config()
        all_categories = categories_config.get("categories", {})
        
        discoverable = []
        non_discoverable = []
        
        for key, cat_def in all_categories.items():
            if not isinstance(cat_def, dict):
                continue
            
            discovery_cfg = cat_def.get("discovery", {})
            is_enabled = discovery_cfg.get("enabled", True)
            has_osm_tags = bool(cat_def.get("osm_tags"))
            
            if is_enabled:
                discoverable.append({
                    "key": key,
                    "label": cat_def.get("label", key),
                    "has_osm_tags": has_osm_tags,
                    "priority": discovery_cfg.get("priority", 0),
                })
            else:
                non_discoverable.append({
                    "key": key,
                    "label": cat_def.get("label", key),
                    "reason": "discovery.enabled=false",
                })
        
        # Also use the model function for comparison
        discoverable_from_model = get_discoverable_categories()
        all_from_model = get_all_categories()
        
        return {
            "all_categories": set(all_categories.keys()),
            "discoverable_categories": {c["key"] for c in discoverable},
            "discoverable_details": discoverable,
            "non_discoverable": non_discoverable,
            "from_model_discoverable": {c.key for c in discoverable_from_model},
            "from_model_all": {c.key for c in all_from_model},
        }
    except Exception as e:
        logger.error("failed_to_load_yaml_categories", error=str(e), exc_info=e)
        return {
            "error": str(e),
        }


def print_analysis(jobs_data: Dict[str, Any], yaml_data: Dict[str, Any]) -> None:
    """Print analysis results."""
    print("\n" + "=" * 80)
    print("DISCOVERY CATEGORIES ANALYSIS")
    print("=" * 80)
    
    if "error" in yaml_data:
        print(f"\n❌ ERROR loading YAML categories: {yaml_data['error']}")
        return
    
    categories_in_jobs = jobs_data["categories_in_jobs"]
    discoverable_yaml = yaml_data["discoverable_categories"]
    all_yaml = yaml_data["all_categories"]
    category_stats = jobs_data["category_stats"]
    
    # 1. Categories in YAML but not in jobs
    missing_in_jobs = discoverable_yaml - categories_in_jobs
    
    # 2. Categories in jobs but not in YAML
    missing_in_yaml = categories_in_jobs - all_yaml
    
    # 3. Categories in jobs but not discoverable in YAML
    non_discoverable_in_jobs = categories_in_jobs - discoverable_yaml
    
    print("\n📊 SUMMARY")
    print("-" * 80)
    print(f"Total categories in YAML: {len(all_yaml)}")
    print(f"Discoverable categories in YAML: {len(discoverable_yaml)}")
    print(f"Categories actually used in jobs: {len(categories_in_jobs)}")
    
    if missing_in_jobs:
        print(f"\n⚠️  DISCOVERABLE CATEGORIES MISSING IN JOBS ({len(missing_in_jobs)}):")
        print("-" * 80)
        for cat_key in sorted(missing_in_jobs):
            details = next((c for c in yaml_data["discoverable_details"] if c["key"] == cat_key), None)
            if details:
                print(f"  • {cat_key:20s} ({details['label']:30s}) priority={details['priority']:2d}, osm_tags={'✓' if details['has_osm_tags'] else '✗'}")
            else:
                print(f"  • {cat_key}")
    
    if missing_in_yaml:
        print(f"\n❌ CATEGORIES IN JOBS BUT NOT IN YAML ({len(missing_in_yaml)}):")
        print("-" * 80)
        for cat_key in sorted(missing_in_yaml):
            stats = category_stats.get(cat_key, {})
            print(f"  • {cat_key:20s} ({stats.get('total_jobs', 0)} jobs)")
    
    if non_discoverable_in_jobs:
        print(f"\n⚠️  NON-DISCOVERABLE CATEGORIES IN JOBS ({len(non_discoverable_in_jobs)}):")
        print("-" * 80)
        for cat_key in sorted(non_discoverable_in_jobs):
            stats = category_stats.get(cat_key, {})
            print(f"  • {cat_key:20s} ({stats.get('total_jobs', 0)} jobs) - discovery.enabled=false in YAML")
    
    # 4. Category usage statistics
    print(f"\n📈 CATEGORY USAGE IN JOBS")
    print("-" * 80)
    print(f"{'Category':<25} {'Total Jobs':<12} {'Status':<40} {'Cities':<10}")
    print("-" * 80)
    
    for cat_key in sorted(categories_in_jobs):
        stats = category_stats.get(cat_key, {})
        status_str = ", ".join([f"{s}:{c}" for s, c in sorted(stats.get("by_status", {}).items())])
        cities_str = f"{len(stats.get('cities', set()))} cities"
        
        print(f"{cat_key:<25} {stats.get('total_jobs', 0):<12} {status_str:<40} {cities_str:<10}")
    
    # 5. Detailed breakdown for missing categories
    if missing_in_jobs:
        print(f"\n🔍 DETAILED BREAKDOWN FOR MISSING CATEGORIES")
        print("-" * 80)
        for cat_key in sorted(missing_in_jobs):
            details = next((c for c in yaml_data["discoverable_details"] if c["key"] == cat_key), None)
            if details:
                print(f"\n{cat_key} ({details['label']}):")
                print(f"  Priority: {details['priority']}")
                print(f"  Has OSM tags: {details['has_osm_tags']}")
                if not details['has_osm_tags']:
                    print(f"  ⚠️  WARNING: Missing osm_tags - discovery will skip this category!")
    
    print("\n" + "=" * 80)


async def main_async() -> None:
    """Main analysis function."""
    print("[AnalyzeCategories] Loading data...")
    
    # Analyze jobs
    jobs_data = await analyze_discovery_jobs()
    
    # Analyze YAML
    yaml_data = analyze_yaml_categories()
    
    # Print results
    print_analysis(jobs_data, yaml_data)
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("-" * 80)
    
    categories_in_jobs = jobs_data["categories_in_jobs"]
    discoverable_yaml = yaml_data.get("discoverable_categories", set())
    missing_in_jobs = discoverable_yaml - categories_in_jobs
    
    if missing_in_jobs:
        print(f"1. {len(missing_in_jobs)} discoverable categories are not in any jobs.")
        print("   → Consider enqueuing jobs for these categories")
        print("   → Check if they were recently added and jobs need to be created")
    
    if missing_in_jobs and len(missing_in_jobs) > 0:
        print(f"\n2. Categories missing from jobs: {', '.join(sorted(missing_in_jobs))}")
        print("   → Run: python -m scripts.enqueue_discovery_jobs --city <city> to create jobs")
    
    print("\n3. Consider migrating categories to database (like cities) for:")
    print("   → Single source of truth")
    print("   → Dynamic category management via admin UI")
    print("   → Better synchronization between Discovery Train and Discovery Bot")


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[AnalyzeCategories] Interrupted by user.")
    except Exception as e:
        print(f"\n[AnalyzeCategories] ERROR: {e}")
        logger.exception("analyze_categories_failed", error=str(e))
        raise


if __name__ == "__main__":
    main()

