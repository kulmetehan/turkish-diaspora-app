from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel

from app.core.client_id import get_client_id
from app.core.feature_flags import require_feature
from app.models.news_city_config import (
    NewsCity,
    get_default_city_keys,
    list_news_cities,
    search_news_cities,
)
from app.models.news_public import (
    NewsCityListResponse,
    NewsCityRecord,
    NewsItem,
    NewsListResponse,
)
from services.db_service import fetch, execute
from services.news_feed_rules import FeedType
from services.news_service import (
    list_news_by_feed,
    list_trending_news,
    search_news as search_news_service,
)
from services.news_trending_x import fetch_trending_topics, TrendingResult
from services.news_google_service import fetch_google_news_for_city

router = APIRouter(
    prefix="/news",
    tags=["news"],
)

_ALLOWED_FEEDS = ", ".join(
    [feed.value for feed in FeedType] + ["trending"]
)




@router.get("", response_model=NewsListResponse)
async def get_news(
    feed: str = Query(
        ...,
        description="Feed to query: diaspora, nl, tr, local, origin, geo, or trending.",
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    categories: list[str] | None = Query(default=None, description="Optional category filters for NL/TR feeds (general, sport, economie, cultuur/magazin)."),
    cities_nl: list[str] | None = Query(default=None, alias="cities_nl"),
    cities_tr: list[str] | None = Query(default=None, alias="cities_tr"),
    trend_country: Literal["nl", "tr"] = Query(
        "nl",
        alias="trend_country",
        description="Country context for the trending feed.",
    ),
) -> NewsListResponse:
    normalized = feed.strip().lower()
    if not normalized:
        raise HTTPException(status_code=400, detail="Feed parameter is required.")

    category_values = list(categories) if isinstance(categories, list) else None

    if normalized == "trending":
        if category_values:
            raise HTTPException(
                status_code=400,
                detail="Category filters are not supported for the trending feed.",
            )
        items, total, meta = await _resolve_trending_payload(
            limit=limit,
            offset=offset,
            trend_country=trend_country,
        )
        return NewsListResponse(items=items, total=total, limit=limit, offset=offset, meta=meta)

    try:
        feed_enum = FeedType(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feed '{feed}'. Allowed values: {_ALLOWED_FEEDS}.",
        ) from exc

    # Handle LOCAL and ORIGIN feeds via Google News service (not DB)
    if feed_enum == FeedType.LOCAL:
        if not cities_nl or len(cities_nl) == 0:
            raise HTTPException(
                status_code=400,
                detail="cities_nl parameter is required for local feed. Please select at least one city.",
            )
        # Use first city (documented behavior: simpler than merging multiple cities)
        city_key = cities_nl[0].strip().lower()
        all_items = await fetch_google_news_for_city(
            country="nl",
            city_key=city_key,
            limit=limit + offset + 50,  # Fetch extra to account for pagination
        )
        # Apply pagination
        total = len(all_items)
        sliced = all_items[offset:offset + limit]
        return NewsListResponse(items=sliced, total=total, limit=limit, offset=offset)

    if feed_enum == FeedType.ORIGIN:
        if not cities_tr or len(cities_tr) == 0:
            raise HTTPException(
                status_code=400,
                detail="cities_tr parameter is required for origin feed. Please select at least one city.",
            )
        # Use first city (documented behavior: simpler than merging multiple cities)
        city_key = cities_tr[0].strip().lower()
        all_items = await fetch_google_news_for_city(
            country="tr",
            city_key=city_key,
            limit=limit + offset + 50,  # Fetch extra to account for pagination
        )
        # Apply pagination
        total = len(all_items)
        sliced = all_items[offset:offset + limit]
        return NewsListResponse(items=sliced, total=total, limit=limit, offset=offset)

    # All other feeds (DIASPORA, NL, TR, GEO) use DB-based list_news_by_feed
    try:
        # Get promoted news first (only for non-LOCAL/ORIGIN feeds)
        promoted_items = []
        if feed_enum not in (FeedType.LOCAL, FeedType.ORIGIN):
            from services.promotion_service import get_promotion_service
            from app.models.news_public import NewsItem
            promotion_service = get_promotion_service()
            promoted_posts = await promotion_service.get_active_news_promotions(limit=5)
            
            for post in promoted_posts:
                # Convert promoted news to NewsItem format
                promoted_items.append(NewsItem(
                    id=-post["id"],  # Negative ID to distinguish from regular news
                    title=post["title"],
                    snippet=post["content"][:200] if len(post["content"]) > 200 else post["content"],
                    source="Promoted",
                    published_at=post["starts_at"],
                    url=post.get("url") or "#",
                    image_url=post.get("image_url"),
                    tags=["promoted"],
                ))
        
        # Get regular news
        regular_items, total = await list_news_by_feed(
            feed_enum,
            limit=limit - len(promoted_items) if len(promoted_items) < limit else limit,
            offset=max(0, offset - len(promoted_items)) if offset > 0 else 0,
            categories=category_values,
            cities_nl=None,  # Not used for these feeds
            cities_tr=None,  # Not used for these feeds
        )
        
        # Combine: promoted first, then regular
        all_items = promoted_items + regular_items
        # Adjust total to include promoted items
        total_with_promoted = total + len(promoted_items)
        
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return NewsListResponse(items=all_items, total=total_with_promoted, limit=limit, offset=offset)


@router.get("/trending", response_model=NewsListResponse)
async def get_trending_news(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    trend_country: Literal["nl", "tr"] = Query(
        "nl",
        alias="trend_country",
        description="Country context for the trending feed.",
    ),
) -> NewsListResponse:
    items, total, meta = await _resolve_trending_payload(limit=limit, offset=offset, trend_country=trend_country)
    return NewsListResponse(items=items, total=total, limit=limit, offset=offset, meta=meta)


@router.get("/search", response_model=NewsListResponse)
async def search_news(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> NewsListResponse:
    items, total = await search_news_service(query=q, limit=limit, offset=offset)
    return NewsListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/cities", response_model=NewsCityListResponse)
async def get_news_cities(
    country: Optional[Literal["nl", "tr"]] = Query(
        default=None,
        description="Optional country filter (nl|tr).",
    ),
) -> NewsCityListResponse:
    cities = [_city_to_payload(city) for city in list_news_cities(country=country)]
    defaults = get_default_city_keys()
    if country:
        normalized = country.strip().lower()
        defaults = {normalized: defaults.get(normalized, [])}
    return NewsCityListResponse(cities=cities, defaults=defaults)


@router.get("/cities/search", response_model=List[NewsCityRecord])
async def search_news_cities_endpoint(
    country: Optional[Literal["nl", "tr"]] = Query(
        default=None,
        description="Optional country filter (nl|tr).",
    ),
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
) -> List[NewsCityRecord]:
    matches = search_news_cities(country=country, query=q, limit=limit)
    return [_city_to_payload(city) for city in matches]


async def _resolve_trending_payload(
    *,
    limit: int,
    offset: int,
    trend_country: Literal["nl", "tr"],
) -> tuple[List[NewsItem], int, Optional[Dict[str, Any]]]:
    """
    Resolve trending payload from X API.
    Returns items, total count, and optional metadata (e.g., unavailable_reason).
    """
    result: TrendingResult = await fetch_trending_topics(limit=limit + offset, country=trend_country)
    
    if result.topics:
        sliced = result.topics[offset:offset + limit]
        items = [_topic_to_news_item(topic) for topic in sliced]
        meta = None
        if result.unavailable_reason:
            meta = {"unavailable_reason": result.unavailable_reason}
        return items, len(result.topics), meta
    
    # No topics available
    meta = None
    if result.unavailable_reason:
        meta = {"unavailable_reason": result.unavailable_reason}
    return [], 0, meta


def _topic_to_news_item(topic) -> NewsItem:
    published_at = topic.published_at or datetime.now(timezone.utc)
    derived_id = abs(hash((topic.title, published_at.timestamp()))) % (2**31 - 1)
    return NewsItem(
        id=derived_id,
        title=topic.title,
        snippet=topic.description,
        source="X Trends",
        published_at=published_at,
        url=topic.url,
        image_url=None,
        tags=["trending"],
    )


def _city_to_payload(city: NewsCity) -> NewsCityRecord:
    metadata = dict(city.metadata) if city.metadata else None
    return NewsCityRecord(
        city_key=city.city_key,
        name=city.name,
        country=city.country.upper(),
        province=city.province,
        parent_key=city.parent_key,
        population=city.population,
        lat=city.lat,
        lng=city.lng,
        metadata=metadata,
    )


class ReactionToggleRequest(BaseModel):
    reaction_type: str  # Emoji string (e.g., "🔥", "❤️", "👍", etc.)


@router.post("/{news_id}/reactions", response_model=dict)
async def toggle_news_reaction(
    news_id: int = Path(..., description="News ID"),
    request: ReactionToggleRequest = ...,
    client_id: Optional[str] = Depends(get_client_id),
):
    """Toggle emoji reaction on news item."""
    require_feature("check_ins_enabled")
    
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id required")
    
    # Basic validation: ensure reaction_type is a non-empty string
    if not request.reaction_type or not isinstance(request.reaction_type, str) or len(request.reaction_type.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="reaction_type must be a non-empty string (emoji)"
        )
    
    # Limit emoji length to prevent abuse (reasonable limit for emoji sequences)
    if len(request.reaction_type) > 10:
        raise HTTPException(
            status_code=400,
            detail="reaction_type too long (max 10 characters)"
        )
    
    user_id = None  # TODO: Extract from auth session
    
    # Check if news exists (only for DB-based news, not trending/promoted)
    check_sql = "SELECT id FROM raw_ingested_news WHERE id = $1"
    check_rows = await fetch(check_sql, news_id)
    if not check_rows:
        raise HTTPException(status_code=404, detail="News item not found")
    
    # Check if already reacted with this type
    if user_id:
        check_reaction_sql = """
            SELECT id FROM news_reactions 
            WHERE news_id = $1 AND user_id = $2 AND reaction_type = $3
        """
        existing = await fetch(check_reaction_sql, news_id, user_id, request.reaction_type)
    else:
        check_reaction_sql = """
            SELECT id FROM news_reactions 
            WHERE news_id = $1 AND client_id = $2 AND reaction_type = $3
        """
        existing = await fetch(check_reaction_sql, news_id, client_id, request.reaction_type)
    
    if existing:
        # Remove reaction
        if user_id:
            delete_sql = """
                DELETE FROM news_reactions 
                WHERE news_id = $1 AND user_id = $2 AND reaction_type = $3
            """
            await execute(delete_sql, news_id, user_id, request.reaction_type)
        else:
            delete_sql = """
                DELETE FROM news_reactions 
                WHERE news_id = $1 AND client_id = $2 AND reaction_type = $3
            """
            await execute(delete_sql, news_id, client_id, request.reaction_type)
        is_active = False
    else:
        # Add reaction
        if user_id:
            insert_sql = """
                INSERT INTO news_reactions (news_id, user_id, reaction_type) 
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """
            await execute(insert_sql, news_id, user_id, request.reaction_type)
        else:
            insert_sql = """
                INSERT INTO news_reactions (news_id, client_id, reaction_type)
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """
            await execute(insert_sql, news_id, client_id, request.reaction_type)
        is_active = True
    
    # Get updated count
    count_sql = """
        SELECT COUNT(*) as count 
        FROM news_reactions 
        WHERE news_id = $1 AND reaction_type = $2
    """
    count_rows = await fetch(count_sql, news_id, request.reaction_type)
    count = count_rows[0]["count"] if count_rows else 0
    
    return {
        "reaction_type": request.reaction_type,
        "is_active": is_active,
        "count": count
    }


@router.get("/{news_id}/reactions", response_model=dict)
async def get_news_reactions(
    news_id: int = Path(..., description="News ID"),
    client_id: Optional[str] = Depends(get_client_id),
):
    """Get reaction counts and user reaction for a news item."""
    require_feature("check_ins_enabled")
    
    # Check if news exists
    check_sql = "SELECT id FROM raw_ingested_news WHERE id = $1"
    check_rows = await fetch(check_sql, news_id)
    if not check_rows:
        raise HTTPException(status_code=404, detail="News item not found")
    
    user_id = None  # TODO: Extract from auth session
    
    # Get reaction counts grouped by type
    counts_sql = """
        SELECT reaction_type, COUNT(*) as count
        FROM news_reactions
        WHERE news_id = $1
        GROUP BY reaction_type
        ORDER BY count DESC, reaction_type ASC
    """
    count_rows = await fetch(counts_sql, news_id)
    
    # Build reactions dict dynamically from database results
    reactions: Dict[str, int] = {}
    for row in count_rows:
        reaction_type = row["reaction_type"]
        reactions[reaction_type] = row["count"]
    
    # Get user's reaction if any
    user_reaction = None
    if user_id:
        user_reaction_sql = """
            SELECT reaction_type FROM news_reactions
            WHERE news_id = $1 AND user_id = $2
            LIMIT 1
        """
        user_reaction_rows = await fetch(user_reaction_sql, news_id, user_id)
        if user_reaction_rows:
            user_reaction = user_reaction_rows[0]["reaction_type"]
    elif client_id:
        user_reaction_sql = """
            SELECT reaction_type FROM news_reactions
            WHERE news_id = $1 AND client_id = $2
            LIMIT 1
        """
        user_reaction_rows = await fetch(user_reaction_sql, news_id, client_id)
        if user_reaction_rows:
            user_reaction = user_reaction_rows[0]["reaction_type"]
    
    return {
        "reactions": reactions,
        "user_reaction": user_reaction
    }


