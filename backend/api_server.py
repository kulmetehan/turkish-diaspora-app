"""
FastAPI server for Diaspora App
Serves content from Supabase database
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import List, Optional
import os
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize FastAPI app
app = FastAPI(
    title="Diaspora App API",
    description="API for serving Turkish diaspora content",
    version="2.0.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "https://kulmetehan.github.io",
        "https://*.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the base directory (parent of backend folder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

# Mount the web directory to serve static files (CSS, JS)
if os.path.exists(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")


@app.get("/")
async def serve_frontend():
    """Serve the web app frontend"""
    html_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(html_path)


# ============================================
# MAIN FEED ENDPOINT - National Headlines
# ============================================

@app.get("/api/content/main")
def get_main_feed(
    limit: int = Query(default=50, ge=1, le=100),
    language: Optional[str] = Query(default=None, pattern="^(nl|tr)$")
):
    """
    Get MAIN feed - national headlines from major cities
    This shows general news from major population centers
    
    Parameters:
    - limit: Number of items to return (1-100, default 50)
    - language: Filter by language ('nl' or 'tr')
    
    Returns:
    - List of content items from major cities
    """
    try:
        # Major cities that represent "national headlines"
        major_dutch_cities = ['Amsterdam', 'Rotterdam', 'Den Haag', 'Utrecht']
        major_turkish_cities = ['İstanbul', 'Ankara', 'İzmir', 'Konya']
        major_cities = major_dutch_cities + major_turkish_cities
        
        # Build query
        query = supabase.table('content_items').select('*')
        
        # Filter by language if specified
        if language:
            query = query.eq('original_language', language)
        
        # Get more articles than needed so we can filter by location
        query = query.order('published_at', desc=True).limit(limit * 3)
        
        response = query.execute()
        
        if not response.data:
            return {"success": True, "items": [], "count": 0}
        
        # Get source information
        source_ids = list(set([item['source_id'] for item in response.data if item.get('source_id')]))
        sources = {}
        
        if source_ids:
            sources_response = supabase.table('sources').select('*').in_('id', source_ids).execute()
            sources = {s['id']: s for s in sources_response.data}
        
        # Filter for main feed: articles from major cities OR no specific location
        main_articles = []
        for item in response.data:
            location_tags = item.get('location_tags', [])
            
            # Include if: no location tags OR from major city
            if not location_tags or any(city in location_tags for city in major_cities):
                source = sources.get(item.get('source_id'), {})
                
                formatted_item = {
                    "id": item['id'],
                    "title": item['title'],
                    "summary": item.get('summary') or "No summary available",
                    "language": item['original_language'],
                    "url": item['url'],
                    "published_at": item['published_at'],
                    "content_type": item['content_type'],
                    "translated_title": item.get('translated_title'),
                    "translated_summary": item.get('translated_summary'),
                    "translated_language": item.get('translated_language'),
                    "category_tags": item.get('category_tags', []),
                    "location_tags": item.get('location_tags', []),
                    "relevance_score": item.get('relevance_score'),
                    "source": {
                        "name": source.get('name', 'Unknown'),
                        "country": source.get('country', 'Unknown')
                    }
                }
                main_articles.append(formatted_item)
                
                if len(main_articles) >= limit:
                    break
        
        return {
            "success": True,
            "count": len(main_articles),
            "items": main_articles
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching main feed: {str(e)}"
        )


# ============================================
# PERSONALIZED FEED ENDPOINT - For You
# ============================================

@app.get("/api/content/personalized")
def get_personalized_feed(
    cities: Optional[str] = Query(default=None),  # Comma-separated city names
    topics: Optional[str] = Query(default=None),  # Comma-separated topics
    limit: int = Query(default=50, ge=1, le=100)
):
    """
    Get PERSONALIZED feed based on user's selected cities and topics
    
    Parameters:
    - cities: Comma-separated city names (e.g., "Vlaardingen,Bayburt,Istanbul")
    - topics: Comma-separated topics (e.g., "Politics,Sports,Economy")
    - limit: Number of items to return (1-100, default 50)
    
    Returns:
    - List of content items matching user preferences
    """
    try:
        # Parse comma-separated strings into lists
        city_list = [c.strip() for c in cities.split(',')] if cities else []
        topic_list = [t.strip() for t in topics.split(',')] if topics else []
        
        if not city_list and not topic_list:
            return {
                "success": True,
                "items": [],
                "count": 0,
                "message": "No preferences specified"
            }
        
        # Build query - get extra articles to filter
        query = supabase.table('content_items').select('*')
        query = query.order('published_at', desc=True).limit(limit * 3)
        
        response = query.execute()
        
        if not response.data:
            return {"success": True, "items": [], "count": 0}
        
        # Get source information
        source_ids = list(set([item['source_id'] for item in response.data if item.get('source_id')]))
        sources = {}
        
        if source_ids:
            sources_response = supabase.table('sources').select('*').in_('id', source_ids).execute()
            sources = {s['id']: s for s in sources_response.data}
        
        # Filter articles based on user preferences
        personalized_articles = []
        
        for item in response.data:
            location_tags = item.get('location_tags', [])
            category_tags = item.get('category_tags', [])
            
            # Check if article matches cities (OR logic - any city match)
            matches_city = False
            if city_list:
                matches_city = any(city in location_tags for city in city_list)
            else:
                matches_city = True  # If no city filter, it matches
            
            # Check if article matches topics (OR logic - any topic match)
            matches_topic = False
            if topic_list:
                matches_topic = any(topic in category_tags for topic in topic_list)
            else:
                matches_topic = True  # If no topic filter, it matches
            
            # Include article if it matches BOTH criteria (city AND topic)
            if matches_city and matches_topic:
                source = sources.get(item.get('source_id'), {})
                
                formatted_item = {
                    "id": item['id'],
                    "title": item['title'],
                    "summary": item.get('summary') or "No summary available",
                    "language": item['original_language'],
                    "url": item['url'],
                    "published_at": item['published_at'],
                    "content_type": item['content_type'],
                    "translated_title": item.get('translated_title'),
                    "translated_summary": item.get('translated_summary'),
                    "translated_language": item.get('translated_language'),
                    "category_tags": item.get('category_tags', []),
                    "location_tags": item.get('location_tags', []),
                    "relevance_score": item.get('relevance_score'),
                    "source": {
                        "name": source.get('name', 'Unknown'),
                        "country": source.get('country', 'Unknown')
                    }
                }
                personalized_articles.append(formatted_item)
                
                if len(personalized_articles) >= limit:
                    break
        
        return {
            "success": True,
            "count": len(personalized_articles),
            "items": personalized_articles,
            "filters_applied": {
                "cities": city_list,
                "topics": topic_list
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching personalized feed: {str(e)}"
        )


# ============================================
# LEGACY ENDPOINT - Backwards Compatibility
# ============================================

@app.get("/api/content/latest")
def get_latest_content(
    limit: int = Query(default=20, ge=1, le=100),
    language: Optional[str] = Query(default=None, pattern="^(nl|tr)$"),
    content_type: Optional[str] = Query(default=None, pattern="^(news|music|event|sports)$"),
    location: Optional[str] = Query(default=None)
):
    """
    Get latest content items from database (legacy endpoint for backwards compatibility)
    
    Parameters:
    - limit: Number of items to return (1-100, default 20)
    - language: Filter by language ('nl' or 'tr')
    - content_type: Filter by type ('news', 'music', 'event', 'sports')
    - location: Filter by city/location mentioned in the article
    
    Returns:
    - List of content items with title, summary, source, date, url, translations
    """
    try:
        query = supabase.table('content_items').select('*')
        
        if language:
            query = query.eq('original_language', language)
        
        if content_type:
            query = query.eq('content_type', content_type)
        
        if location:
            query = query.contains('location_tags', [location])
        
        query = query.order('published_at', desc=True).limit(limit)
        
        response = query.execute()
        
        source_ids = list(set([item['source_id'] for item in response.data if item.get('source_id')]))
        sources = {}
        
        if source_ids:
            sources_response = supabase.table('sources').select('*').in_('id', source_ids).execute()
            sources = {s['id']: s for s in sources_response.data}
        
        items = []
        for item in response.data:
            source = sources.get(item.get('source_id'), {})
            
            formatted_item = {
                "id": item['id'],
                "title": item['title'],
                "summary": item.get('summary') or "No summary available",
                "language": item['original_language'],
                "url": item['url'],
                "published_at": item['published_at'],
                "content_type": item['content_type'],
                "translated_title": item.get('translated_title'),
                "translated_summary": item.get('translated_summary'),
                "translated_language": item.get('translated_language'),
                "category_tags": item.get('category_tags', []),
                "location_tags": item.get('location_tags', []),
                "relevance_score": item.get('relevance_score'),
                "source": {
                    "name": source.get('name', 'Unknown'),
                    "country": source.get('country', 'Unknown')
                }
            }
            items.append(formatted_item)
        
        return {
            "success": True,
            "count": len(items),
            "items": items
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching content: {str(e)}"
        )


@app.get("/api/content/{content_id}")
def get_content_by_id(content_id: str):
    """Get a specific content item by ID"""
    try:
        response = supabase.table('content_items').select('*').eq('id', content_id).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Content item not found")
        
        item = response.data[0]
        
        source = {}
        if item.get('source_id'):
            source_response = supabase.table('sources').select('*').eq('id', item['source_id']).execute()
            if source_response.data:
                source = source_response.data[0]
        
        return {
            "success": True,
            "item": {
                "id": item['id'],
                "title": item['title'],
                "summary": item.get('summary'),
                "language": item['original_language'],
                "url": item['url'],
                "image_url": item.get('image_url'),
                "published_at": item['published_at'],
                "content_type": item['content_type'],
                "categories": item.get('category_tags') or [],
                "locations": item.get('location_tags') or [],
                "translated_title": item.get('translated_title'),
                "translated_summary": item.get('translated_summary'),
                "translated_language": item.get('translated_language'),
                "relevance_score": item.get('relevance_score'),
                "source": {
                    "name": source.get('name', 'Unknown'),
                    "language": source.get('language', 'Unknown'),
                    "country": source.get('country', 'Unknown')
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching content: {str(e)}")


@app.get("/api/stats")
def get_stats():
    """Get database statistics"""
    try:
        content_response = supabase.table('content_items').select('id', count='exact').execute()
        nl_response = supabase.table('content_items').select('id', count='exact').eq('original_language', 'nl').execute()
        tr_response = supabase.table('content_items').select('id', count='exact').eq('original_language', 'tr').execute()
        sources_response = supabase.table('sources').select('id', count='exact').execute()
        
        return {
            "success": True,
            "stats": {
                "total_content": content_response.count,
                "dutch_content": nl_response.count,
                "turkish_content": tr_response.count,
                "active_sources": sources_response.count
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


# ============================================
# EMOJI REACTIONS ENDPOINTS
# ============================================

@app.post("/api/reactions/add")
async def add_reaction(content_id: str = Query(...), user_id: str = Query(...), emoji: str = Query(...)):
    """Add or update a user's reaction to an article"""
    try:
        valid_emojis = ['👍', '❤️', '😂', '🔥', '👏']
        if emoji not in valid_emojis:
            return {"success": False, "error": "Invalid emoji"}, 400
        
        existing = supabase.table("reactions")\
            .select("*")\
            .eq("content_item_id", content_id)\
            .eq("user_id", user_id)\
            .execute()
        
        action = ""
        
        if existing.data and len(existing.data) > 0:
            if existing.data[0]['reaction_type'] == emoji:
                supabase.table("reactions")\
                    .delete()\
                    .eq("content_item_id", content_id)\
                    .eq("user_id", user_id)\
                    .execute()
                action = "removed"
            else:
                supabase.table("reactions")\
                    .update({"reaction_type": emoji})\
                    .eq("content_item_id", content_id)\
                    .eq("user_id", user_id)\
                    .execute()
                action = "updated"
        else:
            supabase.table("reactions").insert({
                "content_item_id": content_id,
                "user_id": user_id,
                "reaction_type": emoji
            }).execute()
            action = "added"
        
        counts = get_reaction_counts_sync(content_id)
        
        return {
            "success": True,
            "action": action,
            "counts": counts
        }
        
    except Exception as e:
        print(f"Error adding reaction: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/reactions/counts/{content_id}")
async def get_reaction_counts(content_id: str):
    """Get reaction counts for a specific article"""
    try:
        counts = get_reaction_counts_sync(content_id)
        return {"success": True, "counts": counts}
        
    except Exception as e:
        print(f"Error getting reactions: {e}")
        return {"success": False, "counts": {'👍': 0, '❤️': 0, '😂': 0, '🔥': 0, '👏': 0}}


@app.get("/api/reactions/user/{content_id}/{user_id}")
async def get_user_reaction(content_id: str, user_id: str):
    """Get a specific user's reaction to an article"""
    try:
        result = supabase.table("reactions")\
            .select("reaction_type")\
            .eq("content_item_id", content_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return {"success": True, "emoji": result.data[0]['reaction_type']}
        else:
            return {"success": True, "emoji": None}
            
    except Exception as e:
        print(f"Error getting user reaction: {e}")
        return {"success": False, "emoji": None}


def get_reaction_counts_sync(content_id: str):
    """Helper function to get reaction counts"""
    try:
        result = supabase.table("reactions")\
            .select("reaction_type")\
            .eq("content_item_id", content_id)\
            .execute()
        
        counts = {'👍': 0, '❤️': 0, '😂': 0, '🔥': 0, '👏': 0}
        for reaction in result.data:
            emoji = reaction['reaction_type']
            if emoji in counts:
                counts[emoji] += 1
        
        return counts
        
    except Exception as e:
        print(f"Error in get_reaction_counts_sync: {e}")
        return {'👍': 0, '❤️': 0, '😂': 0, '🔥': 0, '👏': 0}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)