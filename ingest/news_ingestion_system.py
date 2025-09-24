#!/usr/bin/env python3
"""
Complete RSS News Ingestion System for Turkish Diaspora App
Handles real news feeds from Dutch and Turkish sources
"""

import os
import feedparser
import ssl
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional
import time
import hashlib
from pathlib import Path
from dotenv import load_dotenv

# Laad .env uit de project-root (1 map omhoog vanaf /ingest)
ROOT_ENV = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ROOT_ENV)

# (optioneel) fallback: als je ooit de .env in ingest/ zet
# load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

# Fix SSL certificate verification on macOS
ssl._create_default_https_context = ssl._create_unverified_context

# Load environment
# Load environment from parent directory
from pathlib import Path
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Verify credentials are loaded
if not os.getenv("SUPABASE_URL"):
    print("ERROR: Supabase credentials not found!")
    print("Make sure .env file exists in the project root with SUPABASE_URL and SUPABASE_KEY")
    exit(1)

# Initialize Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

class NewsIngestionSystem:
    def __init__(self):
        """Initialize the news ingestion system"""
        self.stats = {
            'feeds_processed': 0,
            'items_found': 0,
            'items_saved': 0,
            'items_skipped': 0,
            'errors': []
        }
        
        # Define RSS feeds - ADD YOUR FEEDS HERE
        self.rss_feeds = [
            # Dutch News Sources
            {
                'name': 'NOS Nieuws',
                'url': 'https://feeds.nos.nl/nosnieuwsalgemeen',
                'lang': 'nl-NL',
                'country': 'NL',
                'type': 'news'
            },
            {
                'name': 'NU.nl Algemeen',
                'url': 'https://www.nu.nl/rss/Algemeen',
                'lang': 'nl-NL',
                'country': 'NL',
                'type': 'news'
            },
            {
                'name': 'RTL Nieuws',
                'url': 'https://www.rtlnieuws.nl/rss.xml',
                'lang': 'nl-NL',
                'country': 'NL',
                'type': 'news'
            },
            {
                'name': 'Telegraaf',
                'url': 'https://www.telegraaf.nl/rss',
                'lang': 'nl-NL',
                'country': 'NL',
                'type': 'news'
            },
            # Turkish News Sources (International/English)
            {
                'name': 'Daily Sabah',
                'url': 'https://www.dailysabah.com/rssFeed/home',
                'lang': 'en-US',
                'country': 'TR',
                'type': 'news'
            },
            {
                'name': 'Hürriyet Daily News',
                'url': 'https://www.hurriyetdailynews.com/rss',
                'lang': 'en-US',
                'country': 'TR',
                'type': 'news'
            },
            # ADD MORE FEEDS HERE WHEN YOU PROVIDE THEM
        ]
    
    def clean_text(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        if not text:
            return ""
        # Parse HTML
        soup = BeautifulSoup(text, 'html.parser')
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        # Get text
        text = soup.get_text()
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def extract_summary(self, content: str, title: str = "", max_words: int = 100) -> str:
        """Extract a meaningful summary from content"""
        # Clean the content
        clean_content = self.clean_text(content)
        
        if not clean_content:
            # If no content, use title as summary
            return self.clean_text(title)[:300]
        
        # Split into sentences and take first few
        sentences = re.split(r'[.!?]+', clean_content)
        summary = ""
        word_count = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                sentence_words = sentence.split()
                if word_count + len(sentence_words) <= max_words:
                    summary += sentence + ". "
                    word_count += len(sentence_words)
                else:
                    break
        
        return summary.strip() or clean_content[:300] + "..."
    
    def detect_regions(self, text: str) -> List[str]:
        """Detect regions mentioned in the text"""
        regions = []
        text_lower = text.lower()
        
        # Turkish cities
        turkish_cities = {
            'istanbul': 'Istanbul',
            'ankara': 'Ankara', 
            'izmir': 'Izmir',
            'bursa': 'Bursa',
            'antalya': 'Antalya',
            'kayseri': 'Kayseri',
            'adana': 'Adana',
            'konya': 'Konya',
            'gaziantep': 'Gaziantep',
            'trabzon': 'Trabzon'
        }
        
        # Dutch cities
        dutch_cities = {
            'amsterdam': 'Amsterdam',
            'rotterdam': 'Rotterdam',
            'den haag': 'Den Haag',
            'the hague': 'Den Haag',
            'utrecht': 'Utrecht',
            'eindhoven': 'Eindhoven',
            'groningen': 'Groningen',
            'tilburg': 'Tilburg',
            'almere': 'Almere',
            'breda': 'Breda',
            'nijmegen': 'Nijmegen',
            'haarlem': 'Haarlem',
            'arnhem': 'Arnhem',
            'zaanstad': 'Zaanstad',
            'vlaardingen': 'Vlaardingen'  # Your city!
        }
        
        # Check for cities
        for city_key, city_name in turkish_cities.items():
            if city_key in text_lower:
                regions.append(city_name)
        
        for city_key, city_name in dutch_cities.items():
            if city_key in text_lower:
                regions.append(city_name)
        
        # Check for countries
        if any(word in text_lower for word in ['türkiye', 'turkey', 'turkije', 'turks', 'turkish']):
            regions.append('Türkiye')
        if any(word in text_lower for word in ['nederland', 'netherlands', 'holland', 'dutch', 'nederlandse']):
            regions.append('Nederland')
        
        # If no regions detected, mark as general
        if not regions:
            regions.append('General')
        
        return list(set(regions))[:5]  # Return max 5 unique regions
    
    def extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from content"""
        tags = []
        text_lower = text.lower()
        
        # Category detection
        tag_keywords = {
            'politics': ['politic', 'regering', 'minister', 'election', 'verkiezing', 'parlement', 'government'],
            'economy': ['economy', 'economie', 'business', 'market', 'euro', 'inflation', 'bank'],
            'sports': ['sport', 'spor', 'football', 'voetbal', 'futbol', 'soccer', 'match'],
            'technology': ['tech', 'digital', 'ai', 'artificial intelligence', 'computer', 'internet', 'startup'],
            'culture': ['culture', 'cultuur', 'kültür', 'art', 'kunst', 'music', 'festival'],
            'health': ['health', 'gezondheid', 'sağlık', 'covid', 'vaccine', 'hospital', 'doctor'],
            'education': ['education', 'school', 'university', 'universiteit', 'student', 'onderwijs'],
            'crime': ['crime', 'police', 'polis', 'arrest', 'court', 'rechtbank'],
            'diaspora': ['diaspora', 'turkish-dutch', 'turks-nederlandse', 'expat', 'immigrant']
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                tags.append(tag)
        
        # If no tags detected, add 'general'
        if not tags:
            tags.append('general')
        
        return list(set(tags))[:5]  # Return max 5 unique tags
    
    def get_or_create_source(self, feed_info: Dict) -> Optional[int]:
        """Get existing source ID or create new source"""
        try:
            # Check if source exists
            result = supabase.table('sources').select('id').eq('url', feed_info['url']).execute()
            
            if result.data:
                return result.data[0]['id']
            else:
                # Create new source
                new_source = supabase.table('sources').insert({
                    'name': feed_info['name'],
                    'url': feed_info['url'],
                    'lang': feed_info['lang'],
                    'country': feed_info['country'],
                    'type': feed_info['type'],
                    'enabled': True
                }).execute()
                
                if new_source.data:
                    print(f"  ✅ Created new source: {feed_info['name']}")
                    return new_source.data[0]['id']
        except Exception as e:
            print(f"  ❌ Error with source {feed_info['name']}: {str(e)[:100]}")
            self.stats['errors'].append(f"Source error: {feed_info['name']}")
            return None
    
    def process_feed_entry(self, entry: Dict, source_id: int, lang: str) -> Optional[Dict]:
        """Process a single feed entry into a news item"""
        try:
            # Extract basic fields
            title = entry.get('title', '')
            link = entry.get('link', '')
            
            if not title or not link:
                return None
            
            # Get content
            content = ''
            if hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description
            elif hasattr(entry, 'content') and entry.content:
                content = entry.content[0].value
            
            # Parse publication date
            published_at = datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_at = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published_at = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            
            # Create summary
            summary = self.extract_summary(content, title)
            
            # Detect regions and tags
            full_text = f"{title} {content}"
            regions = self.detect_regions(full_text)
            tags = self.extract_tags(full_text)
            
            # Create item
            item = {
                'kind': 'news',
                'source_id': source_id,
                'title': title[:500],
                'url': link,
                'published_at': published_at.isoformat(),
                'lang': lang,
                'summary_tr': summary if 'tr' in lang.lower() else None,
                'summary_nl': summary if 'nl' in lang.lower() else summary,  # Default to NL or general
                'tags': tags,
                'regions': regions,
                'quality_score': 0.7
            }
            
            return item
            
        except Exception as e:
            print(f"    ⚠️ Error processing entry: {str(e)[:100]}")
            return None
    
    def save_news_item(self, item: Dict) -> bool:
        """Save a news item to the database"""
        try:
            # Check if already exists
            existing = supabase.table('items').select('id').eq('url', item['url']).execute()
            
            if existing.data:
                self.stats['items_skipped'] += 1
                return False
            
            # Save new item
            result = supabase.table('items').insert(item).execute()
            
            if result.data:
                self.stats['items_saved'] += 1
                print(f"    ✅ Saved: {item['title'][:60]}...")
                return True
                
        except Exception as e:
            print(f"    ❌ Error saving: {str(e)[:100]}")
            self.stats['errors'].append(f"Save error: {item['title'][:30]}")
            
        return False
    
    def process_feed(self, feed_info: Dict):
        """Process a single RSS feed"""
        print(f"\n📰 Processing: {feed_info['name']}")
        print(f"   URL: {feed_info['url']}")
        
        try:
            # Get or create source
            source_id = self.get_or_create_source(feed_info)
            if not source_id:
                return
            
            # Parse feed
            feed = feedparser.parse(feed_info['url'])
            
            if not hasattr(feed, 'entries') or not feed.entries:
                print(f"   ⚠️ No entries found")
                if hasattr(feed, 'bozo_exception'):
                    print(f"   Error: {feed.bozo_exception}")
                return
            
            print(f"   Found {len(feed.entries)} entries")
            
            # Process entries (limit to 20 per feed)
            for entry in feed.entries[:20]:
                item = self.process_feed_entry(entry, source_id, feed_info['lang'])
                if item:
                    self.stats['items_found'] += 1
                    self.save_news_item(item)
            
            self.stats['feeds_processed'] += 1
            
        except Exception as e:
            print(f"   ❌ Feed error: {str(e)[:200]}")
            self.stats['errors'].append(f"Feed error: {feed_info['name']}")
    
    def run(self):
        """Run the complete ingestion process"""
        print("=" * 60)
        print("🚀 STARTING REAL NEWS INGESTION")
        print("=" * 60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total feeds to process: {len(self.rss_feeds)}")
        
        # Process each feed
        for feed_info in self.rss_feeds:
            self.process_feed(feed_info)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 INGESTION SUMMARY")
        print("=" * 60)
        print(f"Feeds processed: {self.stats['feeds_processed']}/{len(self.rss_feeds)}")
        print(f"Items found: {self.stats['items_found']}")
        print(f"Items saved: {self.stats['items_saved']}")
        print(f"Items skipped (duplicates): {self.stats['items_skipped']}")
        print(f"Errors: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            print("\n⚠️ Errors encountered:")
            for error in self.stats['errors'][:5]:
                print(f"  - {error}")
        
        print("\n✅ Ingestion complete!")
        print("=" * 60)

def add_custom_feeds(feeds: List[Dict]):
    """Add custom RSS feeds to the system"""
    ingestion = NewsIngestionSystem()
    ingestion.rss_feeds.extend(feeds)
    return ingestion

if __name__ == "__main__":
    # Run the ingestion
    ingestion = NewsIngestionSystem()
    
    # You can add more feeds here programmatically
    # Example:
    # custom_feeds = [
    #     {'name': 'BBC News', 'url': 'http://feeds.bbci.co.uk/news/rss.xml', 
    #      'lang': 'en-US', 'country': 'UK', 'type': 'news'},
    # ]
    # ingestion.rss_feeds.extend(custom_feeds)
    
    ingestion.run()