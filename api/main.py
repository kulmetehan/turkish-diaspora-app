from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import uvicorn
from supabase import create_client, Client
from datetime import datetime

load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

app = FastAPI(title="Turkish Diaspora App API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class FeedItem(BaseModel):
    id: int
    kind: str
    title: str
    url: str
    published_at: str
    summary_tr: Optional[str] = None
    summary_nl: Optional[str] = None
    tags: List[str] = []
    regions: List[str] = []
    reactions: Dict[str, int] = {}
    source_name: Optional[str] = None

class ReactionRequest(BaseModel):
    item_id: int
    emoji: str

@app.get("/")
def read_root():
    return {
        "message": "Turkish Diaspora App API", 
        "version": "1.0.0",
        "status": "connected"
    }

@app.get("/v1/feed", response_model=Dict[str, Any])
async def get_feed(
    region: Optional[str] = Query(None, description="Filter by region"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return")
):
    """Get mixed feed items (news, events, sports)"""
    try:
        # Build query without join
        query = supabase.table('items').select('*')
        
        # Apply region filter if provided
        if region:
            query = query.contains('regions', [region])
        
        # Order by published date and limit
        query = query.order('published_at', desc=True).limit(limit)
        
        # Execute query
        response = query.execute()
        
        # Format items
        items = []
        for item in response.data:
            formatted_item = {
                'id': item['id'],
                'kind': item['kind'],
                'title': item['title'],
                'url': item['url'],
                'published_at': item['published_at'],
                'summary_tr': item.get('summary_tr'),
                'summary_nl': item.get('summary_nl'),
                'tags': item.get('tags', []),
                'regions': item.get('regions', []),
                'reactions': {},  # Empty for now
                'source_name': 'News'  # Generic name since we can't join
            }
            items.append(formatted_item)
        
        return {
            "items": items,
            "count": len(items),
            "region": region,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/news", response_model=Dict[str, Any])
async def get_news(
    region: Optional[str] = Query(None, description="Filter by region"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    lang: Optional[str] = Query(None, description="Language filter (tr-TR or nl-NL)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return")
):
    """Get news items with optional filters"""
    try:
        # Build query WITHOUT the problematic join
        query = supabase.table('items').select('*').eq('kind', 'news')
        
        # Apply filters
        if region:
            query = query.contains('regions', [region])
        
        if tags:
            tag_list = tags.split(',')
            for tag in tag_list:
                query = query.contains('tags', [tag.strip()])
        
        if lang:
            query = query.eq('lang', lang)
        
        # Order and limit
        query = query.order('published_at', desc=True).limit(limit)
        
        # Execute query
        response = query.execute()
        
        # Format response
        items = []
        for item in response.data:
            formatted_item = {
                'id': item['id'],
                'title': item['title'],
                'url': item['url'],
                'published_at': item['published_at'],
                'summary_tr': item.get('summary_tr'),
                'summary_nl': item.get('summary_nl'),
                'tags': item.get('tags', []),
                'regions': item.get('regions', []),
                'source_name': 'News',  # Generic name since we can't join
                'lang': item.get('lang')
            }
            items.append(formatted_item)
        
        return {
            "items": items,
            "count": len(items),
            "filters": {
                "region": region,
                "tags": tags.split(",") if tags else [],
                "lang": lang
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/reactions")
async def add_reaction(reaction: ReactionRequest):
    """Add or update a reaction to an item"""
    try:
        # For MVP, we'll use a dummy user ID
        # In production, this would come from authentication
        user_id = "00000000-0000-0000-0000-000000000000"
        
        # Upsert reaction
        response = supabase.table('reactions').upsert({
            'item_id': reaction.item_id,
            'user_id': user_id,
            'emoji': reaction.emoji,
            'created_at': datetime.now().isoformat()
        }).execute()
        
        # Get updated reaction counts
        reactions_response = supabase.table('reactions').select('emoji').eq('item_id', reaction.item_id).execute()
        
        reaction_counts = {}
        for r in reactions_response.data:
            emoji = r['emoji']
            reaction_counts[emoji] = reaction_counts.get(emoji, 0) + 1
        
        return {
            "success": True,
            "reactions": reaction_counts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/stats")
async def get_stats():
    """Get basic statistics about the content"""
    try:
        # Count items by kind
        items = supabase.table('items').select('kind').execute()
        
        stats = {
            'total_items': len(items.data),
            'by_kind': {},
            'last_updated': None
        }
        
        for item in items.data:
            kind = item['kind']
            stats['by_kind'][kind] = stats['by_kind'].get(kind, 0) + 1
        
        # Get most recent item
        recent = supabase.table('items').select('published_at').order('published_at', desc=True).limit(1).execute()
        if recent.data:
            stats['last_updated'] = recent.data[0]['published_at']
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)