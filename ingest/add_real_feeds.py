import os
import ssl
from supabase import create_client, Client
from dotenv import load_dotenv

# Fix SSL
ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv()

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Real working RSS feeds for Turkish diaspora
feeds_to_add = [
    # International news with Turkey/NL coverage
    {'type': 'news', 'name': 'BBC News', 'country': 'UK', 'lang': 'en-US',
     'url': 'http://feeds.bbci.co.uk/news/rss.xml'},
    {'type': 'news', 'name': 'Al Jazeera', 'country': 'INT', 'lang': 'en-US',
     'url': 'https://www.aljazeera.com/xml/rss/all.xml'},
    
    # Dutch local news
    {'type': 'news', 'name': 'AD.nl', 'country': 'NL', 'lang': 'nl-NL',
     'url': 'https://www.ad.nl/home/rss.xml'},
    {'type': 'news', 'name': 'Volkskrant', 'country': 'NL', 'lang': 'nl-NL',
     'url': 'https://www.volkskrant.nl/nieuws/rss.xml'},
    
    # Turkish news in English
    {'type': 'news', 'name': 'Daily Sabah', 'country': 'TR', 'lang': 'en-US',
     'url': 'https://www.dailysabah.com/rssFeed/home'},
    {'type': 'news', 'name': 'TRT World', 'country': 'TR', 'lang': 'en-US',
     'url': 'https://www.trtworld.com/feed'},
    
    # Sports - Football
    {'type': 'sports', 'name': 'UEFA', 'country': 'INT', 'lang': 'en-US',
     'url': 'https://www.uefa.com/rssfeed/news/rss.xml'},
]

print("Adding real RSS feeds...")
for feed in feeds_to_add:
    try:
        # Check if already exists
        existing = supabase.table('sources').select('id').eq('url', feed['url']).execute()
        if not existing.data:
            result = supabase.table('sources').insert(feed).execute()
            print(f"✅ Added: {feed['name']}")
        else:
            print(f"⏭️  Skipped (exists): {feed['name']}")
    except Exception as e:
        print(f"❌ Error adding {feed['name']}: {str(e)[:50]}")

print("\nDone! Now run ingest_simple.py to fetch news from these feeds.")