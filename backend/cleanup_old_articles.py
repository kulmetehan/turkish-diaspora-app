"""
Cleanup old articles from database
Runs daily to remove articles older than 72 hours
"""

from supabase import create_client
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Missing required environment variables: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def cleanup_old_articles():
    print("\n" + "="*60)
    print("CLEANUP: Removing articles older than 72 hours")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Calculate cutoff date
    cutoff_date = (datetime.now() - timedelta(hours=72)).isoformat()
    
    # Count articles to be deleted
    count_response = supabase.table('content_items')\
        .select('id', count='exact')\
        .lt('published_at', cutoff_date)\
        .execute()
    
    articles_to_delete = count_response.count
    print(f"Articles older than 72 hours: {articles_to_delete}")
    
    if articles_to_delete == 0:
        print("No articles to delete")
        return
    
    # Delete old articles
    delete_response = supabase.table('content_items')\
        .delete()\
        .lt('published_at', cutoff_date)\
        .execute()
    
    print(f"✅ Deleted {articles_to_delete} old articles")
    print("="*60 + "\n")

if __name__ == "__main__":
    cleanup_old_articles()