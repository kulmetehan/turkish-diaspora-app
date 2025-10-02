"""
FastAPI server for Diaspora App
Serves content from Supabase database
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
    version="1.0.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Local development frontend
        "http://localhost:8000",      # Backend itself
        "http://127.0.0.1:3000",      # Alternative localhost
        "http://127.0.0.1:8000",      # Alternative localhost
        "https://kulmetehan.github.io",  # GitHub Pages
        "https://*.onrender.com"      # Render deployment
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_frontend():
    """Serve the web app frontend"""
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_path = os.path.join(base_dir, "index.html")
    return FileResponse(html_path)


@app.get("/api/content/latest")
def get_latest_content(
    limit: int = Query(default=20, ge=1, le=100),
    language: Optional[str] = Query(default=None, pattern="^(nl|tr)$"),
    content_type: Optional[str] = Query(default=None, pattern="^(news|music|event|sports)$"),
    location: Optional[str] = Query(default=None)
):
    """
    Get latest content items from database
    
    Parameters:
    - limit: Number of items to return (1-100, default 20)
    - language: Filter by language ('nl' or 'tr')
    - content_type: Filter by type ('news', 'music', 'event', 'sports')
    - location: Filter by city/location mentioned in the article
    
    Returns:
    - List of content items with title, summary, source, date, url, translations
    """
    try:
        # Start building query - fetch content and source separately
        query = supabase.table('content_items').select('*')
        
        # Apply filters if provided
        if language:
            query = query.eq('original_language', language)
        
        if content_type:
            query = query.eq('content_type', content_type)
        
        if location:
            # Filter for articles that mention this city
            query = query.contains('location_tags', [location])
        
        # Order by published date and apply limit
        query = query.order('published_at', desc=True).limit(limit)
        
        # Execute query
        response = query.execute()
        
        # Get source information separately
        source_ids = list(set([item['source_id'] for item in response.data if item.get('source_id')]))
        sources = {}
        
        if source_ids:
            sources_response = supabase.table('sources').select('*').in_('id', source_ids).execute()
            sources = {s['id']: s for s in sources_response.data}
        
        # Format response
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
    """
    Get a specific content item by ID
    
    Parameters:
    - content_id: UUID of the content item
    
    Returns:
    - Single content item with full details
    """
    try:
        response = supabase.table('content_items').select('*').eq('id', content_id).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=404,
                detail="Content item not found"
            )
        
        item = response.data[0]
        
        # Get source separately
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
                "regions": item.get('region_tags') or [],
                "categories": item.get('category_tags') or [],
                "translated_title": item.get('translated_title'),
                "translated_summary": item.get('translated_summary'),
                "translated_language": item.get('translated_language'),
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
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching content: {str(e)}"
        )


@app.get("/api/stats")
def get_stats():
    """Get database statistics"""
    try:
        # Count total content items
        content_response = supabase.table('content_items').select('id', count='exact').execute()
        
        # Count by language
        nl_response = supabase.table('content_items').select('id', count='exact').eq('original_language', 'nl').execute()
        tr_response = supabase.table('content_items').select('id', count='exact').eq('original_language', 'tr').execute()
        
        # Count sources
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
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}"
        )


# ============================================
# TDA-20: EMOJI REACTIONS ENDPOINTS
# ============================================

@app.post("/api/reactions/add")
async def add_reaction(content_id: str = Query(...), user_id: str = Query(...), emoji: str = Query(...)):
    """
    Add or update a user's reaction to an article.
    
    Parameters:
    - content_id: UUID of the article
    - user_id: Temporary user identifier (from localStorage)
    - emoji: One of: 👍, ❤️, 😂, 🔥, 👏
    
    Returns:
    - success: boolean
    - action: 'added', 'updated', or 'removed'
    - counts: updated reaction counts for this article
    """
    try:
        # Validate emoji
        valid_emojis = ['👍', '❤️', '😂', '🔥', '👏']
        if emoji not in valid_emojis:
            return {"success": False, "error": "Invalid emoji"}, 400
        
        # Check if user already reacted to this article
        existing = supabase.table("reactions")\
            .select("*")\
            .eq("content_item_id", content_id)\
            .eq("user_id", user_id)\
            .execute()
        
        action = ""
        
        if existing.data and len(existing.data) > 0:
            # User already has a reaction
            if existing.data[0]['reaction_type'] == emoji:
                # Same emoji clicked - remove reaction (toggle off)
                supabase.table("reactions")\
                    .delete()\
                    .eq("content_item_id", content_id)\
                    .eq("user_id", user_id)\
                    .execute()
                action = "removed"
            else:
                # Different emoji - update
                supabase.table("reactions")\
                    .update({"reaction_type": emoji})\
                    .eq("content_item_id", content_id)\
                    .eq("user_id", user_id)\
                    .execute()
                action = "updated"
        else:
            # Insert new reaction
            supabase.table("reactions").insert({
                "content_item_id": content_id,
                "user_id": user_id,
                "reaction_type": emoji
            }).execute()
            action = "added"
        
        # Get updated counts
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
    """
    Get reaction counts for a specific article.
    
    Parameters:
    - content_id: UUID of the article
    
    Returns:
    - Object with emoji counts: {'👍': 5, '❤️': 3, ...}
    """
    try:
        counts = get_reaction_counts_sync(content_id)
        return {"success": True, "counts": counts}
        
    except Exception as e:
        print(f"Error getting reactions: {e}")
        return {"success": False, "counts": {'👍': 0, '❤️': 0, '😂': 0, '🔥': 0, '👏': 0}}


@app.get("/api/reactions/user/{content_id}/{user_id}")
async def get_user_reaction(content_id: str, user_id: str):
    """
    Get a specific user's reaction to an article.
    
    Parameters:
    - content_id: UUID of the article
    - user_id: Temporary user identifier
    
    Returns:
    - emoji: The emoji they selected, or null if no reaction
    """
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
    """
    Helper function to get reaction counts (synchronous).
    Used by other endpoints to avoid code duplication.
    """
    try:
        # Get all reactions for this article
        result = supabase.table("reactions")\
            .select("reaction_type")\
            .eq("content_item_id", content_id)\
            .execute()
        
        # Count emojis
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