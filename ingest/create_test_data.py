import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def create_test_news():
    """Create test news items directly in the database"""
    print("Creating test news items...")
    
    # Sample news items - mix of Dutch and Turkish topics
    test_items = [
        {
            'title': 'Rotterdam Haven bereikt recordomzet in 2024',
            'summary': 'De Rotterdamse haven heeft een recordomzet behaald met een groei van 12% ten opzichte van vorig jaar.',
            'lang': 'nl-NL',
            'regions': ['Rotterdam', 'Nederland'],
            'tags': ['economy', 'business'],
        },
        {
            'title': 'Turkse gemeenschap viert Republiekdag in Amsterdam',
            'summary': 'Duizenden Turks-Nederlandse burgers kwamen samen in Amsterdam om de 101e verjaardag van de Turkse Republiek te vieren.',
            'lang': 'nl-NL',
            'regions': ['Amsterdam', 'Nederland'],
            'tags': ['culture', 'community'],
        },
        {
            'title': 'Galatasaray wint belangrijke wedstrijd in Champions League',
            'summary': 'Galatasaray heeft een belangrijke overwinning behaald in de Champions League met 3-1 tegen Bayern München.',
            'lang': 'nl-NL',
            'regions': ['Istanbul', 'Türkiye'],
            'tags': ['sports', 'football'],
        },
        {
            'title': 'Nieuwe Turkse supermarkt opent in Den Haag',
            'summary': 'Een nieuwe grote Turkse supermarkt opent haar deuren in Den Haag met producten rechtstreeks uit Turkije.',
            'lang': 'nl-NL',
            'regions': ['Den Haag', 'Nederland'],
            'tags': ['business', 'community'],
        },
        {
            'title': 'Nederlands-Turkse startup wint innovatieprijs',
            'summary': 'Een startup opgericht door Nederlands-Turkse ondernemers heeft de nationale innovatieprijs gewonnen voor hun AI-platform.',
            'lang': 'nl-NL',
            'regions': ['Nederland', 'Amsterdam'],
            'tags': ['technology', 'business'],
        },
        {
            'title': 'Kayseri Erciyes Kayak Merkezi sezon açılışı yaptı',
            'summary': 'Erciyes Kayak Merkezi yeni sezonu rekor sayıda kayakseverle açtı. Sezon boyunca 2 milyon ziyaretçi bekleniyor.',
            'lang': 'tr-TR',
            'regions': ['Kayseri', 'Türkiye'],
            'tags': ['sports', 'tourism'],
        },
        {
            'title': 'Türk-Hollanda ticaret hacmi rekor seviyede',
            'summary': 'Türkiye ve Hollanda arasındaki ticaret hacmi 2024 yılında 10 milyar Euro seviyesini aştı.',
            'lang': 'tr-TR',
            'regions': ['Türkiye', 'Nederland'],
            'tags': ['economy', 'business'],
        },
        {
            'title': 'Utrecht Üniversitesi Türk öğrencilere burs programı',
            'summary': 'Utrecht Üniversitesi, Türk öğrenciler için özel burs programı başlattığını duyurdu.',
            'lang': 'tr-TR',
            'regions': ['Utrecht', 'Nederland'],
            'tags': ['education', 'community'],
        },
    ]
    
    # Get or create a default source
    sources = supabase.table('sources').select('*').limit(1).execute()
    if sources.data:
        source_id = sources.data[0]['id']
    else:
        # Create a default source
        new_source = supabase.table('sources').insert({
            'type': 'news',
            'name': 'Test Source',
            'country': 'NL',
            'lang': 'nl-NL',
            'url': 'http://example.com/rss'
        }).execute()
        source_id = new_source.data[0]['id']
    
    # Insert test items
    saved = 0
    for i, item_data in enumerate(test_items):
        # Create published date (spread across last 7 days)
        published_at = datetime.now() - timedelta(days=random.randint(0, 7), hours=random.randint(0, 23))
        
        item = {
            'kind': 'news',
            'source_id': source_id,
            'title': item_data['title'],
            'url': f"http://example.com/news/{i+1}",
            'published_at': published_at.isoformat(),
            'lang': item_data['lang'],
            'summary_tr': item_data['summary'] if item_data['lang'] == 'tr-TR' else None,
            'summary_nl': item_data['summary'] if item_data['lang'] == 'nl-NL' else None,
            'tags': item_data['tags'],
            'regions': item_data['regions'],
            'quality_score': round(random.uniform(0.6, 0.9), 2)
        }
        
        try:
            # Check if already exists
            existing = supabase.table('items').select('id').eq('url', item['url']).execute()
            if not existing.data:
                result = supabase.table('items').insert(item).execute()
                saved += 1
                print(f"  ✓ Created: {item['title']}")
            else:
                print(f"  - Skipped (exists): {item['title']}")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
    
    print(f"\n✅ Created {saved} test news items")
    
    # Display some stats
    total = supabase.table('items').select('id', count='exact').execute()
    print(f"📊 Total items in database: {total.count}")

if __name__ == "__main__":
    create_test_news()