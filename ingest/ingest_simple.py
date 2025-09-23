import os
import feedparser
import httpx
import ssl
import urllib.request
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
from typing import Dict, List
import time

# Fix SSL certificate issue on macOS
ssl._create_default_https_context = ssl._create_unverified_context

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
    text = re.sub(r'\s+', ' ', text)
    return text.strip()[:500]  # Limit length

def extract_summary(content: str) -> str:
    """Extract a summary from content"""
    clean_content = clean_html(content)
    words = clean_content.split()
    if len(words) <= 70:
        return clean_content
    return ' '.join(words[:70]) + '...'

def detect_regions(text: str) -> List[str]:
    """Simple region detection"""
    regions = []
    text_lower = text.lower()
    
    # Check for countries
    if any(word in text_lower for word in ['nederland', 'netherlands', 'holland', 'dutch']):
        regions.append('Nederland')
    if any(word in text_lower for word in ['türkiye', 'turkey', 'turkije', 'turkish']):
        regions.append('Türkiye')
    
    # Check for major cities
    if 'amsterdam' in text_lower:
        regions.append('Amsterdam')
    if 'rotterdam' in text_lower:
        regions.append('Rotterdam')
    if 'istanbul' in text_lower:
        regions.append('Istanbul')
    if 'ankara' in text_lower:
        regions.append('Ankara')
    
    # Default if none found
    if not regions:
        regions.append('General')
    
    return list(set(regions))

def extract_tags(text: str) -> List[str]:
    """Simple tag extraction"""
    tags = []
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['sport', 'spor', 'football', 'voetbal']):
        tags.append('sports')
    if any(word in text_lower for word in ['politi', 'government', 'minister', 'election']):
        tags.append('politics')
    if any(word in text_lower for word in ['economy', 'ekonomi', 'euro', 'inflation']):
        tags.append('economy')
    if any(word in text_lower for word in ['tech', 'digital', 'computer', 'ai']):
        tags.append('technology')
    
    if not tags:
        tags.append('general')
    
    return tags

def fetch_feed_with_httpx(url: str) -> List[Dict]:
    """Fetch RSS feed using httpx (alternative method)"""
    items = []
    try:
        print(f"  Trying httpx for {url}...")
        with httpx.Client(verify=False) as client:
            response = client.get(url, timeout=10)
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                if feed.entries:
                    print(f"    ✓ Found {len(feed.entries)} entries via httpx")
                    return feed.entries
    except Exception as e:
        print(f"    httpx failed: {str(e)[:50]}")
    return []

def process_rss_feeds():
    """Main function to process RSS feeds"""
    print("=" * 60)
    print("RSS FEED INGESTION - SIMPLIFIED VERSION")
    print("=" * 60)
    
    # Clear and add working sources
    print("\n1. Setting up sources...")
    supabase.table('sources').delete().neq('id', 0).execute()
    
    sources_to_add = [
        # Try BBC and Reuters - they usually work well
        {'type': 'news', 'name': 'BBC World', 'country': 'UK', 'lang': 'en-US',
         'url': 'http://feeds.bbci.co.uk/news/world/rss.xml'},
        {'type': 'news', 'name': 'Reuters', 'country': 'INT', 'lang': 'en-US',
         'url': 'https://feeds.reuters.com/reuters/topNews'},
        # Dutch news - alternative URLs
        {'type': 'news', 'name': 'NU.nl', 'country': 'NL', 'lang': 'nl-NL',
         'url': 'https://www.nu.nl/rss/Algemeen'},
        # Turkish news - try daily sabah english
        {'type': 'news', 'name': 'Daily Sabah', 'country': 'TR', 'lang': 'en-US',
         'url': 'https://www.dailysabah.com/rssFeed/home'},
    ]
    
    for source in sources_to_add:
        try:
            result = supabase.table('sources').insert(source).execute()
            print(f"  Added: {source['name']}")
        except Exception as e:
            print(f"  Failed to add {source['name']}: {str(e)[:50]}")
    
    # Fetch sources and process feeds
    print("\n2. Fetching news from RSS feeds...")
    sources = supabase.table('sources').select('*').execute()
    
    all_items = []
    for source in sources.data:
        print(f"\n  Processing {source['name']}...")
        
        # Try regular feedparser first
        feed = feedparser.parse(source['url'])
        
        entries = []
        if hasattr(feed, 'entries') and feed.entries:
            entries = feed.entries
            print(f"    ✓ Found {len(entries)} entries via feedparser")
        else:
            # Try httpx as backup
            entries = fetch_feed_with_httpx(source['url'])
        
        # Process entries
        for entry in entries[:5]:  # Limit to 5 per source for testing
            title = entry.get('title', 'No title')
            link = entry.get('link', '')
            
            if not link:
                continue
            
            # Get content
            content = ''
            if hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description
            
            # Create item
            item = {
                'kind': 'news',
                'source_id': source['id'],
                'title': title[:500],
                'url': link,
                'published_at': datetime.now().isoformat(),
                'lang': source['lang'],
                'summary_nl': extract_summary(content) if 'nl' in source['lang'] else extract_summary(content),
                'summary_tr': None,  # We'll add translation later
                'tags': extract_tags(f"{title} {content}"),
                'regions': detect_regions(f"{title} {content}"),
                'quality_score': 0.7
            }
            all_items.append(item)
    
    # Save to database
    print(f"\n3. Saving {len(all_items)} items to database...")
    saved = 0
    for item in all_items:
        try:
            # Check if exists
            existing = supabase.table('items').select('id').eq('url', item['url']).execute()
            if not existing.data:
                supabase.table('items').insert(item).execute()
                saved += 1
                print(f"  ✓ {item['title'][:50]}...")
        except Exception as e:
            print(f"  ✗ Error: {str(e)[:50]}")
    
    print("\n" + "=" * 60)
    print(f"COMPLETE: {saved} new items saved to database")
    print("=" * 60)

if __name__ == "__main__":
    process_rss_feeds()