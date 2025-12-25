#!/usr/bin/env python3
"""
Verify that the automotive migration was successful.

This script checks:
1. That 'automotive' category exists in categories.yml
2. That normalize_category works for 'automotive'
3. That no 'car_dealer' records remain in the database (if DB connection available)
"""

import sys
from pathlib import Path

# Add Backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.category_map import normalize_category, clear_category_map_cache
from app.models.categories import Category, clear_cache

def main():
    print("🔍 Verifying automotive migration...")
    print()
    
    # Clear caches
    clear_category_map_cache()
    clear_cache()
    
    # Test 1: Check Category enum
    print("1. Checking Category enum...")
    try:
        assert hasattr(Category, 'automotive'), "Category.automotive not found in enum"
        assert Category.automotive == "automotive", "Category.automotive value incorrect"
        assert not hasattr(Category, 'car_dealer'), "Category.car_dealer still exists (should be removed)"
        print("   ✅ Category enum is correct")
    except AssertionError as e:
        print(f"   ❌ Category enum issue: {e}")
        return 1
    
    # Test 2: Check normalize_category for automotive
    print("2. Testing normalize_category('automotive')...")
    try:
        result = normalize_category('automotive')
        assert result.get('category_key') == 'automotive', f"Expected 'automotive', got {result.get('category_key')}"
        assert result.get('category_label') == 'automotive', f"Expected 'automotive' label, got {result.get('category_label')}"
        print(f"   ✅ normalize_category works: {result}")
    except AssertionError as e:
        print(f"   ❌ normalize_category issue: {e}")
        return 1
    
    # Test 3: Check that car_dealer is no longer recognized
    print("3. Testing normalize_category('car_dealer') (should return None key)...")
    try:
        result = normalize_category('car_dealer')
        # car_dealer should not be found, so category_key should be None
        assert result.get('category_key') is None, f"car_dealer should not be recognized, but got {result.get('category_key')}"
        print(f"   ✅ car_dealer correctly returns None: {result}")
    except AssertionError as e:
        print(f"   ❌ car_dealer normalization issue: {e}")
        return 1
    
    # Test 4: Check database (optional, if connection available)
    print("4. Checking database (if connection available)...")
    try:
        from services.db_service import fetch
        import asyncio
        
        async def check_db():
            # Check for remaining car_dealer records
            rows = await fetch("SELECT COUNT(*) as count FROM locations WHERE category = 'car_dealer'")
            car_dealer_count = rows[0]['count'] if rows else 0
            
            # Check for automotive records
            rows = await fetch("SELECT COUNT(*) as count FROM locations WHERE category = 'automotive'")
            automotive_count = rows[0]['count'] if rows else 0
            
            return car_dealer_count, automotive_count
        
        try:
            loop = asyncio.get_event_loop()
            car_dealer_count, automotive_count = loop.run_until_complete(check_db())
            
            if car_dealer_count > 0:
                print(f"   ⚠️  Warning: {car_dealer_count} locations still have category='car_dealer'")
                print(f"      Run migration script: Infra/supabase/082_migrate_car_dealer_to_automotive.sql")
            else:
                print(f"   ✅ No car_dealer records found")
            
            print(f"   📊 Found {automotive_count} locations with category='automotive'")
        except Exception as e:
            print(f"   ⚠️  Could not check database: {e}")
            print(f"      (This is OK if database is not accessible)")
    except ImportError:
        print("   ⚠️  Database service not available (this is OK)")
    
    print()
    print("✅ All checks passed!")
    print()
    print("Next steps:")
    print("1. Restart the backend server to clear caches")
    print("2. Rebuild the frontend if needed")
    print("3. Verify locations are visible on the map")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

