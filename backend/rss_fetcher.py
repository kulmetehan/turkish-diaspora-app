"""
RSS Feed Fetcher for Diaspora App
Fetches news from NOS.nl and TRT Haber, normalizes content, and stores in Supabase
"""

import feedparser
from bs4 import BeautifulSoup
from supabase import create_client, Client
from datetime import datetime
from curator import curate_article, translate_content, tag_locations
from dotenv import load_dotenv
import os
import time

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# RSS Feed URLs
RSS_FEEDS = [
    {
        'name': 'NOS Nieuws',
        'url': 'https://feeds.nos.nl/nosnieuwsalgemeen',
        'language': 'nl',
        'country': 'NL'
    },
    {
        'name': 'TRT Haber',
        'url': 'https://www.trthaber.com/sondakika.rss',
        'language': 'tr',
        'country': 'TR'
    }
]


def clean_html(html_text):
    """
    Remove HTML tags and clean text content
    
    Args:
        html_text: String containing HTML
        
    Returns:
        Cleaned plain text string
    """
    if not html_text:
        return ""
    
    soup = BeautifulSoup(html_text, 'html.parser')
    # Get text and clean up whitespace
    text = soup.get_text()
    text = ' '.join(text.split())  # Remove extra whitespace
    return text


def get_or_create_source(source_info):
    """
    Get source ID from database or create if doesn't exist
    
    Args:
        source_info: Dictionary with source details
        
    Returns:
        UUID of the source
    """
    try:
        # Check if source exists
        response = supabase.table('sources').select('id').eq('name', source_info['name']).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
        
        # Create new source if doesn't exist
        response = supabase.table('sources').insert({
            'name': source_info['name'],
            'type': 'rss',
            'url': source_info['url'],
            'language': source_info['language'],
            'country': source_info['country'],
            'is_active': True
        }).execute()
        
        return response.data[0]['id']
        
    except Exception as e:
        print(f"Error getting/creating source {source_info['name']}: {e}")
        return None


def parse_date(date_struct):
    """
    Parse RSS date struct to ISO format
    
    Args:
        date_struct: Time struct from feedparser
        
    Returns:
        ISO formatted datetime string
    """
    try:
        if not date_struct:
            return datetime.now().isoformat()
        
        dt = datetime(*date_struct[:6])
        return dt.isoformat()
    except:
        return datetime.now().isoformat()


def fetch_and_store_feed(feed_info):
    """
    Fetch RSS feed and store articles in database
    
    Args:
        feed_info: Dictionary with feed URL and metadata
        
    Returns:
        Number of articles successfully stored
    """
    print(f"\n{'='*60}")
    print(f"Fetching: {feed_info['name']}")
    print(f"URL: {feed_info['url']}")
    print(f"{'='*60}")
    
    try:
        # Get or create source
        source_id = get_or_create_source(feed_info)
        if not source_id:
            print(f"Failed to get source ID for {feed_info['name']}")
            return 0
        
        # Parse RSS feed with User-Agent
        print("Downloading feed...")
        feed = feedparser.parse(feed_info['url'], agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
        
        # Debug: Print feed status
        print(f"Feed status: {feed.get('status', 'unknown')}")
        print(f"Feed entries found: {len(feed.entries)}")
        
        if hasattr(feed, 'bozo_exception'):
            print(f"Feed parsing warning: {feed.bozo_exception}")
        
        if not feed.entries:
            print(f"No entries found in feed")
            # Try to print raw feed info for debugging
            if hasattr(feed, 'feed'):
                print(f"Feed info: {feed.feed.get('title', 'No title')}")
            return 0
        
        stored_count = 0
        skipped_count = 0
        
        for entry in feed.entries:
            try:
                # Extract and clean data
                title = entry.get('title', 'No title')
                summary = clean_html(entry.get('summary', entry.get('description', '')))
                url = entry.get('link', '')
                published = parse_date(entry.get('published_parsed'))
                
                # Debug: Print first entry details
                if stored_count == 0 and skipped_count == 0:
                    print(f"\nFirst entry details:")
                    print(f"  Title: {title[:80]}...")
                    print(f"  URL: {url}")
                    print(f"  Published: {published}")
                
                # Skip if no URL
                if not url:
                    skipped_count += 1
                    continue
                
                # Check if article already exists
                existing = supabase.table('content_items').select('id').eq('url', url).execute()
                
                if existing.data and len(existing.data) > 0:
                    skipped_count += 1
                    continue
                
                # Prepare content item data
                content_data = {
                    'source_id': source_id,
                    'content_type': 'news',
                    'title': title[:500],
                    'summary': summary[:2000] if summary else None,
                    'original_language': feed_info['language'],
                    'url': url,
                    'published_at': published
                }
                
                # AI curation for each article
                if content_data.get('summary'):
                    print(f"  🤖 Curating article with AI...")
                    curation = curate_article(
                        title=content_data['title'],
                        summary=content_data['summary'],
                        language=content_data['original_language']
                    )
                    
                    # Update item with curated data
                    content_data['summary'] = curation['summary']
                    content_data['relevance_score'] = curation['relevance_score']
                    content_data['category_tags'] = curation['category_tags']
                    
                    # Detect locations
                    print(f"  📍 Detecting locations...")
                    location_tags = tag_locations(
                        title=content_data['title'],
                        summary=content_data['summary']
                    )
                    content_data['location_tags'] = location_tags
                    
                    # AI translation (NL ↔ TR)
                    print(f"  🌍 Translating article...")
                    translation = translate_content(
                        title=content_data['title'],
                        summary=content_data['summary'],
                        from_language=content_data['original_language']
                    )
                    
                    # Add translation to content data
                    content_data['translated_title'] = translation['translated_title']
                    content_data['translated_summary'] = translation['translated_summary']
                    content_data['translated_language'] = translation['translated_language']
                
                # Insert into database
                supabase.table('content_items').insert(content_data).execute()
                stored_count += 1
                print(f"Stored: {title[:60]}...")
                
            except Exception as e:
                print(f"Error processing entry: {e}")
                continue
        
        print(f"\nSummary for {feed_info['name']}:")
        print(f"  - Stored: {stored_count} new articles")
        print(f"  - Skipped: {skipped_count} (duplicates or invalid)")
        
        return stored_count
        
    except Exception as e:
        print(f"Error fetching feed {feed_info['name']}: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """
    Main function to fetch all RSS feeds
    """
    print("\n" + "="*60)
    print("RSS FEED FETCHER - DIASPORA APP")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    total_stored = 0
    
    for feed in RSS_FEEDS:
        stored = fetch_and_store_feed(feed)
        total_stored += stored
    
    print("\n" + "="*60)
    print(f"COMPLETE - Total articles stored: {total_stored}")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()