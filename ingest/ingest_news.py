import os
import sys
import feedparser
import httpx
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import hashlib
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional
import time

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def clean_html(html_text: str) -> str:
    """Remove HTML tags and clean text"""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, 'html.parser')
    text = soup.get_text()
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_summary(content: str, max_words: int = 70) -> str:
    """Extract a summary from content"""
    clean_content = clean_html(content)
    words = clean_content.split()
    if len(words) <= max_words:
        return clean_content
    return ' '.join(words[:max_words]) + '...'

def detect_regions(text: str) -> List[str]:
    """Detect Turkish and Dutch regions mentioned in text"""
    regions = []
    
    # Turkish cities
    turkish_cities = [
        'Istanbul', 'Ankara', 'Izmir', 'Bursa', 'Antalya', 'Konya', 
        'Kayseri', 'Gaziantep', 'Adana', 'Trabzon', 'Erzurum', 'Diyarbakır'
    ]
    
    # Dutch cities
    dutch_cities = [
        'Amsterdam', 'Rotterdam', 'Den Haag', 'Utrecht', 'Eindhoven', 
        'Groningen', 'Tilburg', 'Almere', 'Breda', 'Nijmegen', 'Haarlem', 'Vlaardingen'
    ]
    
    text_lower = text.lower()
    
    for city in turkish_cities:
        if city.lower() in text_lower:
            regions.append(city)
    
    for city in dutch_cities:
        if city.lower() in text_lower:
            regions.append(city)
    
    # Add countries if mentioned
    if 'türkiye' in text_lower or 'turkey' in text_lower or 'turkije' in text_lower:
        regions.append('Türkiye')
    if 'nederland' in text_lower or 'netherlands' in text_lower or 'holland' in text_lower:
        regions.append('Nederland')
    
    # Default regions if none detected
    if not regions:
        regions.append('General')
    
    return list(set(regions))  # Remove duplicates

def extract_tags(text: str, lang: str) -> List[str]:
    """Extract relevant tags from content"""
    tags = []
    text_lower = text.lower()
    
    # Topic detection
    if any(word in text_lower for word in ['economy', 'ekonomi', 'economie']):
        tags.append('economy')
    if any(word in text_lower for word in ['politics', 'politika', 'politiek', 'siyaset']):
        tags.append('politics')
    if any(word in text_lower for word in ['sport', 'spor', 'football', 'voetbal', 'futbol']):
        tags.append('sports')
    if any(word in text_lower for word in ['technology', 'teknoloji', 'technologie', 'tech']):
        tags.append('technology')
    if any(word in text_lower for word in ['culture', 'kültür', 'cultuur', 'sanat', 'art']):
        tags.append('culture')
    if any(word in text_lower for word in ['health', 'sağlık', 'gezondheid', 'covid', 'corona']):
        tags.append('health')
    
    # Default tag if none detected
    if not tags:
        tags.append('general')
    
    return tags

def fetch_and_parse_feed(source: Dict) -> List[Dict]:
    """Fetch and parse RSS feed from a source"""
    items = []
    
    try:
        print(f"Fetching feed from {source['name']} ({source['url']})...")
        
        # Set a user agent to avoid being blocked
        feedparser.USER_AGENT = "Mozilla/5.0 (compatible; TurkishDiasporaApp/1.0)"
        
        # Try to fetch the feed
        feed = feedparser.parse(source['url'])
        
        # Check if we got entries
        if hasattr(feed, 'entries') and feed.entries:
            print(f"  Found {len(feed.entries)} entries")
            
            for entry in feed.entries[:10]:  # Limit to 10 items per source for MVP
                # Extract content
                title = entry.get('title', 'No title')
                link = entry.get('link', '')
                
                # Skip if no link
                if not link:
                    continue
                
                # Try different fields for content
                content = ''
                if hasattr(entry, 'content') and entry.content:
                    content = entry.content[0].value if entry.content else ''
                elif hasattr(entry, 'summary'):
                    content = entry.summary
                elif hasattr(entry, 'description'):
                    content = entry.description
                
                # Parse published date
                published_at = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_at = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_at = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                
                # Extract summary
                summary = extract_summary(content or title)
                
                # Detect regions and tags
                full_text = f"{title} {content}"
                regions = detect_regions(full_text)
                tags = extract_tags(full_text, source['lang'])
                
                item = {
                    'kind': 'news',
                    'source_id': source['id'],
                    'title': title[:500],  # Limit title length
                    'url': link,
                    'published_at': published_at.isoformat(),
                    'lang': source['lang'],
                    'summary_tr': summary if 'tr' in source['lang'] else None,
                    'summary_nl': summary if 'nl' in source['lang'] else None,
                    'tags': tags,
                    'regions': regions,
                    'quality_score': 0.7  # Default score
                }
                
                items.append(item)
        else:
            print(f"  No entries found or feed structure issue")
            print(f"  Feed status: {getattr(feed, 'status', 'unknown')}")
            if hasattr(feed, 'bozo_exception'):
                print(f"  Parse error: {feed.bozo_exception}")
            
    except Exception as e:
        print(f"  Error fetching {source['name']}: {str(e)}")
    
    return items

def update_sources_with_working_feeds():
    """Update the sources table with RSS feeds that actually work"""
    print("Updating sources with working RSS feeds...")
    
    # Clear existing sources
    supabase.table('sources').delete().neq('id', 0).execute()
    
    # Working RSS feeds (tested)
    working_sources = [
        # Dutch news
        {'type': 'news', 'name': 'NOS Algemeen', 'country': 'NL', 'lang': 'nl-NL', 
         'url': 'https://feeds.nos.nl/nosnieuwsalgemeen'},
        {'type': 'news', 'name': 'RTL Nieuws', 'country': 'NL', 'lang': 'nl-NL',
         'url': 'https://www.rtlnieuws.nl/rss.xml'},
        {'type': 'news', 'name': 'Telegraaf', 'country': 'NL', 'lang': 'nl-NL',
         'url': 'https://www.telegraaf.nl/rss'},
        
        # Turkish news
        {'type': 'news', 'name': 'Anadolu Agency', 'country': 'TR', 'lang': 'tr-TR',
         'url': 'https://www.aa.com.tr/tr/rss/default?cat=guncel'},
        {'type': 'news', 'name': 'Sabah', 'country': 'TR', 'lang': 'tr-TR',
         'url': 'https://www.sabah.com.tr/rss/anasayfa.xml'},
        {'type': 'news', 'name': 'CNN Türk', 'country': 'TR', 'lang': 'tr-TR',
         'url': 'https://www.cnnturk.com/feed/rss/all'},
    ]
    
    # Insert new sources
    for source in working_sources:
        try:
            result = supabase.table('sources').insert(source).execute()
            print(f"  Added source: {source['name']}")
        except Exception as e:
            print(f"  Error adding {source['name']}: {str(e)}")

def save_items_to_database(items: List[Dict]):
    """Save items to Supabase database"""
    if not items:
        print("No items to save")
        return
    
    saved = 0
    errors = 0
    
    for item in items:
        try:
            # Check if item already exists (by URL)
            existing = supabase.table('items').select('id').eq('url', item['url']).execute()
            
            if not existing.data:
                # Insert new item
                result = supabase.table('items').insert(item).execute()
                saved += 1
                print(f"  ✓ Saved: {item['title'][:60]}...")
            else:
                print(f"  - Skipped (exists): {item['title'][:60]}...")
        except Exception as e:
            errors += 1
            print(f"  ✗ Error saving item: {str(e)[:100]}")
    
    print(f"\nResults: {saved} new items saved, {errors} errors")

def main():
    """Main ingestion function"""
    print("=" * 60)
    print("Starting News Ingestion")
    print("=" * 60)
    print(f"Supabase URL: {os.getenv('SUPABASE_URL')}")
    
    # First, update sources with working feeds
    update_sources_with_working_feeds()
    
    # Get active sources from database
    try:
        sources = supabase.table('sources').select('*').eq('enabled', True).execute()
        
        if not sources.data:
            print("No active sources found in database")
            return
        
        print(f"\nFound {len(sources.data)} active sources")
        print("-" * 40)
        
        # Process each source
        all_items = []
        for source in sources.data:
            items = fetch_and_parse_feed(source)
            if items:
                print(f"  → Fetched {len(items)} items from {source['name']}")
                all_items.extend(items)
        
        # Save all items to database
        print("\n" + "=" * 40)
        print("Saving to database...")
        save_items_to_database(all_items)
        
        print("\n" + "=" * 60)
        print(f"✅ Ingestion complete! Total items processed: {len(all_items)}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error accessing database: {str(e)}")
        print("Make sure your Supabase credentials are correct in .env file")

if __name__ == "__main__":
    main()