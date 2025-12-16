from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.models.feed_curated import (
    CuratedEventsResponse,
    CuratedNewsResponse,
    LocationStatsResponse,
    CategoryStat,
)
from app.models.news_public import NewsItem
from app.models.events_public import EventItem
from services.db_service import fetchrow
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(
    prefix="/feed",
    tags=["feed"],
)


@router.get("/curated/news", response_model=CuratedNewsResponse)
async def get_curated_news() -> CuratedNewsResponse:
    """
    Haal laatste AI-gecurateerde news rankings op.
    Returns top 3 news items ranked by relevance to Turkish Dutch people.
    """
    try:
        row = await fetchrow(
            """
            SELECT ranked_items, metadata
            FROM feed_curated_content
            WHERE content_type = 'news'
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        
        if not row:
            logger.warning("no_cached_news_rankings")
            # Return empty response with fallback message
            return CuratedNewsResponse(
                items=[],
                meta={"message": "No cached rankings available yet"}
            )
        
        # #region agent log
        ranked_items_raw = row.get("ranked_items")
        metadata_raw = row.get("metadata")
        with open("/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log", "a") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"feed.py:54","message":"ranked_items_raw type check","data":{"type":str(type(ranked_items_raw)),"is_str":isinstance(ranked_items_raw,str),"value_preview":str(ranked_items_raw)[:100] if ranked_items_raw else None},"timestamp":int(__import__("time").time()*1000)})+"\n")
        # #endregion
        
        # Parse JSONB if it's a string (asyncpg should auto-parse, but handle both cases)
        if isinstance(ranked_items_raw, str):
            ranked_items_data = json.loads(ranked_items_raw)
        else:
            ranked_items_data = ranked_items_raw or []
        
        if isinstance(metadata_raw, str):
            metadata = json.loads(metadata_raw)
        else:
            metadata = metadata_raw or {}
        
        # Convert ranked items to NewsItem format
        news_items: List[NewsItem] = []
        for item_data in ranked_items_data:
            try:
                # Parse published_at if it's a string
                published_at = item_data.get("published_at")
                if isinstance(published_at, str):
                    published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                elif isinstance(published_at, datetime):
                    pass  # Already datetime
                else:
                    # Fallback to now if missing
                    published_at = datetime.now(timezone.utc)
                
                news_item = NewsItem(
                    id=item_data.get("id", 0),
                    title=item_data.get("title", ""),
                    snippet=item_data.get("snippet"),
                    source=item_data.get("source", ""),
                    published_at=published_at,
                    url=item_data.get("url", "#"),
                    image_url=item_data.get("image_url"),
                    tags=item_data.get("tags", []),
                )
                news_items.append(news_item)
            except Exception as e:
                logger.warning("failed_to_parse_news_item", item_id=item_data.get("id"), error=str(e))
                continue
        
        return CuratedNewsResponse(
            items=news_items[:3],  # Ensure max 3 items
            meta=metadata,
        )
    except Exception as e:
        logger.error("get_curated_news_failed", error=str(e))
        # Return empty response instead of crashing
        return CuratedNewsResponse(
            items=[],
            meta={"error": str(e)}
        )


@router.get("/curated/locations", response_model=LocationStatsResponse)
async def get_location_stats() -> LocationStatsResponse:
    """
    Haal laatste location statistics op met random categorie selectie.
    Returns formatted text like "1051 Turkse locaties in Nederland. Waarvan 25 bakkers en 30 supermarkten."
    """
    try:
        row = await fetchrow(
            """
            SELECT ranked_items, metadata
            FROM feed_curated_content
            WHERE content_type = 'location_stats'
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        
        if not row:
            logger.warning("no_cached_location_stats")
            # Return fallback response
            return LocationStatsResponse(
                total=0,
                categories=[],
                formatted_text="Locaties worden geladen...",
            )
        
        # #region agent log
        ranked_items_raw = row.get("ranked_items")
        metadata_raw = row.get("metadata")
        with open("/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log", "a") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"feed.py:126","message":"location_stats ranked_items_raw type check","data":{"type":str(type(ranked_items_raw)),"is_str":isinstance(ranked_items_raw,str),"value_preview":str(ranked_items_raw)[:100] if ranked_items_raw else None},"timestamp":int(__import__("time").time()*1000)})+"\n")
        # #endregion
        
        # Parse JSONB if it's a string (asyncpg should auto-parse, but handle both cases)
        if isinstance(ranked_items_raw, str):
            ranked_items_data = json.loads(ranked_items_raw)
        else:
            ranked_items_data = ranked_items_raw or {}
        
        if isinstance(metadata_raw, str):
            metadata = json.loads(metadata_raw)
        else:
            metadata = metadata_raw or {}
        
        # Extract data
        total = ranked_items_data.get("total", 0)
        categories_data = ranked_items_data.get("categories", [])
        formatted_text = ranked_items_data.get("formatted_text", "")
        
        # Convert categories
        categories: List[CategoryStat] = []
        for cat_data in categories_data:
            try:
                categories.append(CategoryStat(
                    category=cat_data.get("category", ""),
                    label=cat_data.get("label", ""),
                    count=cat_data.get("count", 0),
                ))
            except Exception as e:
                logger.warning("failed_to_parse_category_stat", error=str(e))
                continue
        
        return LocationStatsResponse(
            total=total,
            categories=categories,
            formatted_text=formatted_text,
        )
    except Exception as e:
        logger.error("get_location_stats_failed", error=str(e))
        # Return fallback response
        return LocationStatsResponse(
            total=0,
            categories=[],
            formatted_text="Locaties worden geladen...",
        )


@router.get("/curated/events", response_model=CuratedEventsResponse)
async def get_curated_events() -> CuratedEventsResponse:
    """
    Haal laatste AI-gecurateerde event rankings op.
    Returns top 3 events ranked by relevance to Turkish diaspora.
    """
    try:
        row = await fetchrow(
            """
            SELECT ranked_items, metadata
            FROM feed_curated_content
            WHERE content_type = 'events'
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        
        if not row:
            logger.warning("no_cached_event_rankings")
            # Return empty response
            return CuratedEventsResponse(
                items=[],
                meta={"message": "No cached rankings available yet"}
            )
        
        # #region agent log
        ranked_items_raw = row.get("ranked_items")
        metadata_raw = row.get("metadata")
        with open("/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log", "a") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"feed.py:188","message":"events ranked_items_raw type check","data":{"type":str(type(ranked_items_raw)),"is_str":isinstance(ranked_items_raw,str),"value_preview":str(ranked_items_raw)[:100] if ranked_items_raw else None},"timestamp":int(__import__("time").time()*1000)})+"\n")
        # #endregion
        
        # Parse JSONB if it's a string (asyncpg should auto-parse, but handle both cases)
        if isinstance(ranked_items_raw, str):
            ranked_items_data = json.loads(ranked_items_raw)
        else:
            ranked_items_data = ranked_items_raw or []
        
        if isinstance(metadata_raw, str):
            metadata = json.loads(metadata_raw)
        else:
            metadata = metadata_raw or {}
        
        # Convert ranked items to EventItem format
        event_items: List[EventItem] = []
        for item_data in ranked_items_data:
            try:
                # Parse datetime fields
                start_time_utc = item_data.get("start_time_utc")
                if isinstance(start_time_utc, str):
                    start_time_utc = datetime.fromisoformat(start_time_utc.replace("Z", "+00:00"))
                elif not isinstance(start_time_utc, datetime):
                    continue  # Skip if invalid
                
                end_time_utc = item_data.get("end_time_utc")
                if isinstance(end_time_utc, str):
                    end_time_utc = datetime.fromisoformat(end_time_utc.replace("Z", "+00:00"))
                elif end_time_utc is None:
                    pass  # Optional field
                elif not isinstance(end_time_utc, datetime):
                    end_time_utc = None
                
                updated_at = item_data.get("updated_at")
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                elif not isinstance(updated_at, datetime):
                    updated_at = datetime.now(timezone.utc)
                
                event_item = EventItem(
                    id=item_data.get("id", 0),
                    title=item_data.get("title", ""),
                    description=item_data.get("description"),
                    start_time_utc=start_time_utc,
                    end_time_utc=end_time_utc,
                    city_key=item_data.get("city_key"),
                    category_key=item_data.get("category_key"),
                    location_text=item_data.get("location_text"),
                    url=item_data.get("url"),
                    source_key=item_data.get("source_key", ""),
                    summary_ai=item_data.get("summary_ai"),
                    updated_at=updated_at,
                    lat=item_data.get("lat"),
                    lng=item_data.get("lng"),
                )
                event_items.append(event_item)
            except Exception as e:
                logger.warning("failed_to_parse_event_item", item_id=item_data.get("id"), error=str(e))
                continue
        
        return CuratedEventsResponse(
            items=event_items[:3],  # Ensure max 3 items
            meta=metadata,
        )
    except Exception as e:
        logger.error("get_curated_events_failed", error=str(e))
        # Return empty response instead of crashing
        return CuratedEventsResponse(
            items=[],
            meta={"error": str(e)}
        )
