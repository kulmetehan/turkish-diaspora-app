#!/usr/bin/env python3
"""Quick script to check which cities have jobs for specific categories."""

import asyncio
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool, fetch


async def check():
    await init_db_pool()
    
    # Get cities that have jobs for clinic and events_venue
    sql = """
        SELECT 
            category,
            city_key,
            COUNT(*) as job_count
        FROM discovery_jobs
        WHERE category IN ('clinic', 'events_venue')
        GROUP BY category, city_key
        ORDER BY category, city_key
    """
    rows = await fetch(sql)
    
    print('\n📋 Clinic and Events Venue Jobs by City:')
    print('=' * 60)
    clinic_cities = set()
    events_venue_cities = set()
    
    for row in rows:
        d = dict(row)
        cat = d['category']
        city = d['city_key']
        count = d['job_count']
        print(f"  {cat:15s} {city:20s} {count} jobs")
        if cat == 'clinic':
            clinic_cities.add(city)
        elif cat == 'events_venue':
            events_venue_cities.add(city)
    
    # Get all cities that have ANY jobs
    sql_all = """
        SELECT DISTINCT city_key
        FROM discovery_jobs
        ORDER BY city_key
    """
    all_cities_rows = await fetch(sql_all)
    all_cities = {dict(r)['city_key'] for r in all_cities_rows}
    
    print(f'\n📊 Summary:')
    print(f'  Total cities with jobs: {len(all_cities)}')
    print(f'  Cities with clinic jobs: {len(clinic_cities)}')
    print(f'  Cities with events_venue jobs: {len(events_venue_cities)}')
    
    missing_clinic = all_cities - clinic_cities
    missing_events = all_cities - events_venue_cities
    
    if missing_clinic:
        print(f'\n⚠️  Cities missing clinic jobs ({len(missing_clinic)}):')
        for city in sorted(missing_clinic):
            print(f'    • {city}')
    
    if missing_events:
        print(f'\n⚠️  Cities missing events_venue jobs ({len(missing_events)}):')
        for city in sorted(missing_events):
            print(f'    • {city}')
    
    # Compare with other categories
    sql_other = """
        SELECT 
            category,
            COUNT(DISTINCT city_key) as city_count
        FROM discovery_jobs
        GROUP BY category
        ORDER BY category
    """
    other_rows = await fetch(sql_other)
    
    print(f'\n📈 Category Coverage (number of cities):')
    print('-' * 60)
    for row in other_rows:
        d = dict(row)
        cat = d['category']
        count = d['city_count']
        marker = '⚠️' if cat in ('clinic', 'events_venue') and count < 10 else '  '
        print(f"{marker} {cat:20s} {count:2d} cities")


if __name__ == "__main__":
    asyncio.run(check())

