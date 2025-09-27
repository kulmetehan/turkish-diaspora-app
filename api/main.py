import os
import ssl
import asyncio
from datetime import datetime
from typing import List, Optional, Literal, Dict, Any

import asyncpg
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from pydantic import BaseModel, AnyHttpUrl
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# ==========
# Config
# ==========
DATABASE_URL = os.getenv("DATABASE_URL")  # Supabase Postgres connect string (met sslmode=require)
INGEST_TOKEN = os.getenv("INGEST_TOKEN")  # secret voor /v1/ingest/run

app = FastAPI(title="Turkish Diaspora App API", version="1.0.0")

# CORS (mag later strikter)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_pool: Optional[asyncpg.Pool] = None


# ==========
# Helper Functions for Language/Region Mapping
# ==========
def _norm_lang(x: str) -> str:
    """Normalize language string for consistent comparison"""
    return x.strip().lower().replace('_', '-')


def _region_to_lang(region: str) -> Optional[str]:
    """Map region names to language codes"""
    r = region.strip().lower()
    nl_aliases = {"nederland", "netherlands", "hollanda", "nl"}
    tr_aliases = {"türkiye", "turkiye", "turkey", "tr"}
    if r in nl_aliases:
        return "nl"
    if r in tr_aliases:
        return "tr"
    return None


# ==========
# Models
# ==========
class Item(BaseModel):
    id: int
    kind: Literal["news", "music", "event", "sport"]
    source_id: Optional[int] = None
    source_name: str
    title: str
    url: AnyHttpUrl
    published_at: datetime
    lang: Optional[str] = None
    summary_tr: Optional[str] = None
    summary_nl: Optional[str] = None
    tags: List[str] = []
    regions: List[str] = []
    quality_score: Optional[float] = None
    reactions: Dict[str, int] = {}


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


class PagedResponse(BaseModel):
    items: List[Item]
    total: int
    limit: int
    offset: Optional[int] = None
    count: Optional[int] = None  # For backward compatibility


class FeedResponse(BaseModel):
    items: List[FeedItem]
    count: int
    region: Optional[str] = None
    limit: int


class NewsResponse(BaseModel):
    items: List[Dict[str, Any]]
    count: int
    filters: Dict[str, Any]


class StatsResponse(BaseModel):
    total_items: int
    total_news: int
    total_sources: int
    by_kind: Dict[str, int] = {}
    last_updated: Optional[str] = None


class ReactionRequest(BaseModel):
    item_id: int
    emoji: str


# ==========
# DB Pool
# ==========
async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set")
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        _pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            ssl=ssl_ctx,
            min_size=1,
            max_size=5,
            command_timeout=30,
        )
    return _pool


@app.on_event("startup")
async def startup_event():
    await get_pool()


@app.on_event("shutdown")
async def shutdown_event():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# ==========
# Helpers
# ==========
def cache_headers(max_age_seconds: int = 300) -> dict:
    return {"Cache-Control": f"public, max-age={max_age_seconds}"}


def safe_format_item(r) -> Dict[str, Any]:
    """Safely format database row to dict, handling type conversions"""
    return {
        'id': int(r["id"]) if r["id"] is not None else 0,
        'title': str(r["title"]) if r["title"] else "",
        'url': str(r["url"]) if r["url"] else "",
        'published_at': r["published_at"].isoformat() if r["published_at"] else None,
        'summary_tr': r["summary_tr"] if r["summary_tr"] else None,
        'summary_nl': r["summary_nl"] if r["summary_nl"] else None,
        'tags': list(r["tags"]) if r["tags"] and isinstance(r["tags"], (list, tuple)) else [],
        'regions': list(r["regions"]) if r["regions"] and isinstance(r["regions"], (list, tuple)) else [],
        'source_name': str(r["source_name"]) if r["source_name"] else "News",
        'lang': str(r["lang"]) if r["lang"] else None
    }


# ==========
# Endpoints
# ==========
@app.get("/")
def read_root():
    return {
        "message": "Turkish Diaspora App API", 
        "version": "1.0.0",
        "status": "connected"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/v1/news")
async def get_news(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    region: Optional[str] = Query(None, description="Filter by region"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    lang: Optional[str] = Query(None, description="Language filter (tr-TR or nl-NL)"),
    q: Optional[str] = Query(None, description="zoek in title (ILIKE)"),
    since: Optional[datetime] = Query(None, description="published_at > since"),
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Get news items with optional filters"""
    try:
        filters = ["i.kind = 'news'"]
        params = []
        
        # Handle language filtering with tolerance for variants
        if lang:
            L = _norm_lang(lang)
            params.append(L + '%')
            filters.append(f"lower(i.lang) like ${len(params)}")
        elif region:
            mapped = _region_to_lang(region)
            if mapped:
                params.append(mapped + '%')
                filters.append(f"lower(i.lang) like ${len(params)}")
        
        # Add other filters
        if q:
            params.append(f"%{q}%")
            filters.append(f"i.title ILIKE ${len(params)}")
        if since:
            params.append(since)
            filters.append(f"i.published_at > ${len(params)}")

        where_sql = " AND ".join(filters) if filters else "TRUE"

        # Simplified query without problematic joins or array operations
        list_sql = f"""
            SELECT
              i.id, i.kind, i.source_id,
              'News' AS source_name,
              i.title, i.url, i.published_at, i.lang,
              i.summary_tr, i.summary_nl,
              COALESCE(i.tags, '{{}}') AS tags,
              COALESCE(i.regions, '{{}}') AS regions,
              i.quality_score
            FROM items i
            WHERE {where_sql}
            ORDER BY i.published_at DESC
            LIMIT ${len(params) + 1}
            OFFSET ${len(params) + 2}
        """

        async with pool.acquire() as conn:
            rows = await conn.fetch(list_sql, *(params + [limit, offset]))

        items = []
        for r in rows:
            try:
                formatted_item = safe_format_item(r)
                items.append(formatted_item)
            except Exception as e:
                # Skip problematic rows instead of failing completely
                print(f"Skipping row {r.get('id', 'unknown')}: {e}")
                continue

        return JSONResponse(
            status_code=200,
            content={
                "items": items,
                "count": len(items),
                "filters": {
                    "region": region,
                    "tags": tags.split(",") if tags else [],
                    "lang": lang
                }
            },
            headers=cache_headers(300),
        )
        
    except Exception as e:
        print(f"News endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")


@app.get("/v1/feed")
async def get_feed(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    region: Optional[str] = Query(None, description="Filter by region"),
    kind: Optional[Literal["news", "music", "event", "sport"]] = None,
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Get mixed feed items (news, events, sports)"""
    try:
        filters = []
        params = []
        
        if kind:
            params.append(kind)
            filters.append(f"i.kind = ${len(params)}")
        else:
            filters.append("i.kind = 'news'")  # MVP: voorlopig alleen news
        
        # Apply region-to-language mapping for feed as well
        if region:
            mapped = _region_to_lang(region)
            if mapped:
                params.append(mapped + '%')
                filters.append(f"lower(i.lang) like ${len(params)}")

        where_sql = " AND ".join(filters) if filters else "TRUE"

        list_sql = f"""
            SELECT
              i.id, i.kind, i.source_id,
              'News' AS source_name,
              i.title, i.url, i.published_at, i.lang,
              i.summary_tr, i.summary_nl,
              COALESCE(i.tags, '{{}}') AS tags,
              COALESCE(i.regions, '{{}}') AS regions,
              i.quality_score
            FROM items i
            WHERE {where_sql}
            ORDER BY i.published_at DESC
            LIMIT ${len(params) + 1}
            OFFSET ${len(params) + 2}
        """

        async with pool.acquire() as conn:
            rows = await conn.fetch(list_sql, *(params + [limit, offset]))

        items = []
        for r in rows:
            try:
                formatted_item = safe_format_item(r)
                formatted_item['kind'] = str(r["kind"]) if r["kind"] else "news"
                formatted_item['reactions'] = {}  # Empty for now
                items.append(formatted_item)
            except Exception as e:
                print(f"Skipping row {r.get('id', 'unknown')}: {e}")
                continue

        return JSONResponse(
            status_code=200,
            content={
                "items": items,
                "count": len(items),
                "region": region,
                "limit": limit
            },
            headers=cache_headers(300),
        )
        
    except Exception as e:
        print(f"Feed endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")


@app.get("/v1/stats")
async def get_stats(pool: asyncpg.Pool = Depends(get_pool)):
    """Get basic statistics about the content"""
    try:
        sql = """
          SELECT
            (SELECT COUNT(*) FROM items)                        AS total_items,
            (SELECT COUNT(*) FROM items WHERE kind='news')      AS total_news,
            (SELECT COUNT(*) FROM sources)                      AS total_sources
        """
        
        # Get kind distribution
        kind_sql = "SELECT kind, COUNT(*) as count FROM items GROUP BY kind"
        
        # Get most recent item
        recent_sql = "SELECT published_at FROM items ORDER BY published_at DESC LIMIT 1"
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql)
            kind_rows = await conn.fetch(kind_sql)
            recent_row = await conn.fetchrow(recent_sql)
        
        by_kind = {str(r["kind"]): int(r["count"]) for r in kind_rows}
        last_updated = recent_row["published_at"].isoformat() if recent_row and recent_row["published_at"] else None
        
        return JSONResponse(
            status_code=200,
            content={
                "total_items": int(row["total_items"]),
                "total_news": int(row["total_news"]),
                "total_sources": int(row["total_sources"]),
                "by_kind": by_kind,
                "last_updated": last_updated
            },
            headers=cache_headers(60),
        )
        
    except Exception as e:
        print(f"Stats endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")


@app.post("/v1/reactions")
async def add_reaction(reaction: ReactionRequest, pool: asyncpg.Pool = Depends(get_pool)):
    """Add or update a reaction to an item"""
    try:
        # For MVP, we'll use a dummy user ID
        # In production, this would come from authentication
        user_id = "00000000-0000-0000-0000-000000000000"
        
        # Upsert reaction using asyncpg
        upsert_sql = """
            INSERT INTO reactions (item_id, user_id, emoji, created_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (item_id, user_id) 
            DO UPDATE SET emoji = $3, created_at = $4
        """
        
        # Get reaction counts
        count_sql = """
            SELECT emoji, COUNT(*) as count 
            FROM reactions 
            WHERE item_id = $1 
            GROUP BY emoji
        """
        
        async with pool.acquire() as conn:
            await conn.execute(upsert_sql, reaction.item_id, user_id, reaction.emoji, datetime.now())
            count_rows = await conn.fetch(count_sql, reaction.item_id)
        
        reaction_counts = {str(r["emoji"]): int(r["count"]) for r in count_rows}
        
        return {
            "success": True,
            "reactions": reaction_counts
        }
        
    except Exception as e:
        print(f"Reactions endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")


@app.post("/v1/ingest/run")
async def run_ingest(authorization: Optional[str] = Header(None)):
    """
    Trigger je ingest (voor Render Cron). Verwacht:
    Authorization: Bearer <INGEST_TOKEN>
    """
    if not INGEST_TOKEN:
        raise HTTPException(status_code=500, detail="INGEST_TOKEN not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != INGEST_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

    # TODO: roep hier jouw ingest-functie aan, bv.:
    # from ingest.runner import run_once
    # await run_once()
    await asyncio.sleep(0.05)
    return {"status": "ok", "ran": True}


# Handig voor lokaal draaien zonder gunicorn
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)