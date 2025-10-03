"""
Google News RSS Feed Fetcher for Diaspora App
Fetches news from Google News for specific cities using RSS feeds
"""

import feedparser
from bs4 import BeautifulSoup
from supabase import create_client, Client
from datetime import datetime
from urllib.parse import quote_plus
from curator import curate_and_translate_batch, tag_locations
from cities import get_all_cities
from dotenv import load_dotenv
import os
import time
import ssl
import hashlib

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# SSL context for macOS (if needed)
ssl._create_default_https_context = ssl._create_unverified_context


def get_content_hash(title, summary):
    """
    Create unique hash from title + first 100 chars of summary
    
    Args:
        title: Article title
        summary: Article summary
        
    Returns:
        MD5 hash string
    """
    # Handle None summary
    clean_summary = summary if summary else ""
    
    # Create content string from title + first 100 chars of summary
    content = f"{title[:200]}{clean_summary[:100]}".lower()
    
    # Generate MD5 hash
    return hashlib.md5(content.encode()).hexdigest()


def generate_google_news_url(city_name, country_code, language):
    """
    Generate Google News RSS feed URL for a specific city
    
    Args:
        city_name: Name of the city (e.g., "Vlaardingen")
        country_code: Country code (e.g., "NL" or "TR")
        language: Language code (e.g., "nl" or "tr")
    
    Returns:
        Full RSS URL string
    """
    # Create search query: "City Country" to be more specific
    country_name = "Netherlands" if country_code == "NL" else "Turkey"
    query = f"{city_name} {country_name}"
    
    # URL encode the query
    encoded_query = quote_plus(query)
    
    # Build Google News RSS URL
    base_url = "https://news.google.com/rss/search"
    url = f"{base_url}?q={encoded_query}&hl={language}&gl={country_code}&ceid={country_code}:{language}"
    
    return url


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
    text = soup.get_text()
    text = ' '.join(text.split())  # Remove extra whitespace
    return text


def get_or_create_source(source_name, source_url, language, country):
    """
    Get source ID from database or create if doesn't exist
    
    Args:
        source_name: Name of the source
        source_url: URL of the source
        language: Language code
        country: Country code
        
    Returns:
        UUID of the source
    """
    try:
        # Check if source exists
        response = supabase.table('sources').select('id').eq('name', source_name).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
        
        # Create new source if doesn't exist
        response = supabase.table('sources').insert({
            'name': source_name,
            'type': 'google_news',
            'url': source_url,
            'language': language,
            'country': country,
            'is_active': True
        }).execute()
        
        return response.data[0]['id']
        
    except Exception as e:
        print(f"Error getting/creating source {source_name}: {e}")
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


def fetch_priority_cities():
    """
    Get only high-priority cities (top 15 Dutch + top 15 Turkish)
    to reduce processing time from 50 to 30 cities
    """
    all_cities = get_all_cities()
    
    # Separate Dutch and Turkish cities
    dutch_cities = [city for city in all_cities if city['country'] == 'Netherlands']
    turkish_cities = [city for city in all_cities if city['country'] == 'Turkey']
    
    # Take top 15 from each (cities are already sorted by population)
    priority_cities = dutch_cities[:15] + turkish_cities[:15]
    
    print(f"🎯 Using {len(priority_cities)} priority cities: {len(dutch_cities[:15])} Dutch + {len(turkish_cities[:15])} Turkish")
    return priority_cities


def fetch_google_news_for_city(city):
    """
    Fetch news from Google News for a specific city
    
    Args:
        city: Dictionary with city info (name, country_code, language)
    
    Returns:
        Number of articles successfully stored
    """
    print(f"\n{'='*60}")
    print(f"📍 Fetching: {city['name']}, {city['country']}")
    print(f"{'='*60}")
    
    # Generate Google News URL
    url = generate_google_news_url(
        city['name'], 
        city['country_code'], 
        city['language']
    )
    
    print(f"🔗 URL: {url}")
    
    try:
        # Parse RSS feed
        print("📥 Downloading feed...")
        feed = feedparser.parse(url, agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
        
        print(f"📊 Feed status: {feed.get('status', 'unknown')}")
        print(f"📄 Feed entries found: {len(feed.entries)}")
        
        if hasattr(feed, 'bozo_exception'):
            print(f"⚠️ Feed parsing warning: {feed.bozo_exception}")
        
        if not feed.entries:
            print(f"❌ No entries found in feed for {city['name']}")
            return 0
        
        stored_count = 0
        skipped_count = 0
        
        # Process up to 10 articles per city, but stop after 5 new ones
        for entry in feed.entries[:10]:
            try:
                # Early exit if we already have 5 new articles for this city
                if stored_count >= 5:
                    print(f"✅ Reached 5 new articles for {city['name']}, moving to next city")
                    break
                
                # Extract and clean data
                title = entry.get('title', 'No title')
                summary = clean_html(entry.get('summary', entry.get('description', '')))
                url = entry.get('link', '')
                published = parse_date(entry.get('published_parsed'))
                
                # Extract source name from title (Google News includes source in title)
                # Format is usually: "Article Title - Source Name"
                source_name = "Google News"
                if ' - ' in title:
                    parts = title.split(' - ')
                    source_name = parts[-1]  # Last part is usually the source
                    title = ' - '.join(parts[:-1])  # Rejoin the rest as title
                
                # Skip if no URL
                if not url:
                    skipped_count += 1
                    continue
                
                # Generate content hash for deduplication
                content_hash = get_content_hash(title, summary)
                
                # Check if article already exists by URL OR content hash
                existing = supabase.table('content_items').select('id').or_(f"url.eq.{url},content_hash.eq.{content_hash}").execute()
                
                if existing.data and len(existing.data) > 0:
                    skipped_count += 1
                    print(f"⏭️  Skipped duplicate: {title[:50]}...")
                    continue
                
                # Get or create source
                source_id = get_or_create_source(
                    source_name=source_name,
                    source_url=url,
                    language=city['language'],
                    country=city['country_code']
                )
                
                if not source_id:
                    print(f"❌ Failed to get source ID for {source_name}")
                    skipped_count += 1
                    continue
                
                # Prepare content item data
                content_data = {
                    'source_id': source_id,
                    'content_type': 'news',
                    'title': title[:500],
                    'summary': summary[:2000] if summary else title[:200],
                    'original_language': city['language'],
                    'url': url,
                    'published_at': published,
                    'location_tags': [city['name']],  # Tag with city name
                    'content_hash': content_hash  # Add content hash for future deduplication
                }
                
                # AI curation and translation in ONE batch call
                if content_data.get('summary'):
                    print(f"  🤖 Processing article with AI...")
                    batch_result = curate_and_translate_batch(
                        title=content_data['title'],
                        summary=content_data['summary'],
                        language=content_data['original_language']
                    )
                    
                    # Update item with batch processed data
                    content_data['summary'] = batch_result['summary']
                    content_data['relevance_score'] = batch_result['relevance_score']
                    content_data['category_tags'] = batch_result['category_tags']
                    content_data['translated_title'] = batch_result['translated_title']
                    content_data['translated_summary'] = batch_result['translated_summary']
                    content_data['translated_language'] = batch_result['translated_language']
                    
                    # Detect additional locations (beyond the city we searched for)
                    location_tags = tag_locations(
                        title=content_data['title'],
                        summary=content_data['summary']
                    )
                    
                    # Merge with existing city tag (avoid duplicates)
                    all_locations = list(set([city['name']] + location_tags))
                    content_data['location_tags'] = all_locations
                
                # Insert into database
                supabase.table('content_items').insert(content_data).execute()
                stored_count += 1
                print(f"✅ Stored: {title[:60]}...")
                
            except Exception as e:
                print(f"❌ Error processing entry: {e}")
                continue
        
        print(f"\n📊 Summary for {city['name']}:")
        print(f"  - ✅ Stored: {stored_count} new articles")
        print(f"  - ⏭️  Skipped: {skipped_count} (duplicates or invalid)")
        
        return stored_count
        
    except Exception as e:
        print(f"❌ Error fetching feed for {city['name']}: {e}")
        return 0


def fetch_all_cities():
    """
    Main function: Fetch news for priority cities and store in database
    """
    print("\n" + "="*60)
    print("🚀 GOOGLE NEWS FETCHER - DIASPORA APP (OPTIMIZED)")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Use priority cities instead of all 50
    cities = fetch_priority_cities()
    total_stored = 0
    start_time = time.time()
    
    for i, city in enumerate(cities, 1):
        print(f"\n[{i}/{len(cities)}] 🏙️ Processing {city['name']}, {city['country']}")
        
        # Fetch articles
        stored = fetch_google_news_for_city(city)
        total_stored += stored
        
        # Be nice to Google - wait 2 seconds between requests
        if i < len(cities):
            print("⏳ Waiting 2 seconds before next city...")
            time.sleep(2)
    
    end_time = time.time()
    total_minutes = (end_time - start_time) / 60
    
    print("\n" + "="*60)
    print(f"✅ COMPLETED!")
    print(f"💾 Total articles stored: {total_stored}")
    print(f"⏱️  Total time: {total_minutes:.1f} minutes")
    print(f"🏁 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")


if __name__ == "__main__":
    fetch_all_cities()