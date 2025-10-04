"""
Cleanup old articles from database
Smart cleanup that ensures each city always has minimum articles
"""

from supabase import create_client
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Missing required environment variables: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def cleanup_with_safeguards():
    """
    Smart cleanup that ensures each city always has minimum articles
    - Deletes articles older than 7 days
    - BUT always keeps at least 5 most recent articles per city
    """
    print("🧹 Starting cleanup with safeguards...")
    
    # Step 1: Calculate cutoff date (7 days ago, timezone-aware)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    print(f"📅 Cutoff date: {seven_days_ago.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Step 2: Get all unique cities
    cities_result = supabase.table('content_items')\
        .select('location_tags')\
        .execute()
    
    all_cities = set()
    for item in cities_result.data:
        if item['location_tags']:
            all_cities.update(item['location_tags'])
    
    print(f"🏙️  Found {len(all_cities)} unique cities to process")
    
    deleted_total = 0
    kept_total = 0
    
    # Step 3: For each city, keep MINIMUM 5 articles
    for city in sorted(all_cities):
        city_articles = supabase.table('content_items')\
            .select('id, created_at, title')\
            .contains('location_tags', [city])\
            .order('created_at', desc=True)\
            .execute()
        
        total_articles = len(city_articles.data)
        
        # Keep newest 5 articles no matter what
        articles_to_keep = city_articles.data[:5]
        kept_total += len(articles_to_keep)
        
        # For articles beyond the first 5, delete if older than 7 days
        articles_to_delete = []
        for article in city_articles.data[5:]:
            # Parse the created_at timestamp (handle both with and without 'Z')
            created_at_str = article['created_at'].replace('Z', '+00:00')
            created_at = datetime.fromisoformat(created_at_str)
            
            if created_at < seven_days_ago:
                articles_to_delete.append(article)
        
        # Delete old articles
        if articles_to_delete:
            print(f"📍 {city}: Deleting {len(articles_to_delete)} old articles (keeping {min(5, total_articles)} recent)")
            for article in articles_to_delete:
                supabase.table('content_items').delete().eq('id', article['id']).execute()
                deleted_total += 1
        else:
            print(f"📍 {city}: All {total_articles} articles are recent (keeping all)")
    
    print(f"\n{'='*60}")
    print(f"✅ Cleanup complete!")
    print(f"🗑️  Deleted: {deleted_total} old articles")
    print(f"💾 Kept: {kept_total} recent articles")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    cleanup_with_safeguards()