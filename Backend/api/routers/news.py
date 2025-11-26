from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query

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
from services.news_feed_rules import FeedType
from services.news_service import (
    ALLOWED_NEWS_THEMES,
    list_news_by_feed,
    list_trending_news,
    search_news as search_news_service,
)
from services.news_trending_x import fetch_trending_topics

router = APIRouter(
    prefix="/news",
    tags=["news"],
)

_ALLOWED_FEEDS = ", ".join(
    [feed.value for feed in FeedType] + ["trending"]
)


THEME_DESCRIPTION = (
    "Optional comma separated themes "
    f"({', '.join(ALLOWED_NEWS_THEMES)})."
)


@router.get("", response_model=NewsListResponse)
async def get_news(
    feed: str = Query(
        ...,
        description="Feed to query: diaspora, nl, tr, local, origin, geo, or trending.",
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    themes: list[str] | None = Query(default=None, description=THEME_DESCRIPTION),
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

    theme_values = list(themes) if isinstance(themes, list) else None

    if normalized == "trending":
        if theme_values:
            raise HTTPException(
                status_code=400,
                detail="Theme filters are not supported for the trending feed.",
            )
        items, total = await _resolve_trending_payload(
            limit=limit,
            offset=offset,
            trend_country=trend_country,
        )
        return NewsListResponse(items=items, total=total, limit=limit, offset=offset)

    try:
        feed_enum = FeedType(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feed '{feed}'. Allowed values: {_ALLOWED_FEEDS}.",
        ) from exc

    try:
        city_filter_nl = None
        city_filter_tr = None
        if feed_enum == FeedType.LOCAL:
            city_filter_nl = cities_nl
        elif feed_enum == FeedType.ORIGIN:
            city_filter_tr = cities_tr

        items, total = await list_news_by_feed(
            feed_enum,
            limit=limit,
            offset=offset,
            themes=theme_values,
            cities_nl=city_filter_nl,
            cities_tr=city_filter_tr,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return NewsListResponse(items=items, total=total, limit=limit, offset=offset)


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
    items, total = await _resolve_trending_payload(limit=limit, offset=offset, trend_country=trend_country)
    return NewsListResponse(items=items, total=total, limit=limit, offset=offset)


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
) -> tuple[List[NewsItem], int]:
    """
    Resolve trending payload from X API or stub topics.
    Falls back to stub topics if X API is unavailable (instead of database items).
    """
    raw_topics = await fetch_trending_topics(limit=limit + offset, country=trend_country)
    if raw_topics:
        sliced = raw_topics[offset:offset + limit]
        items = [_topic_to_news_item(topic) for topic in sliced]
        return items, len(raw_topics)
    # If no topics (X API failed and stubs not available), return empty list
    # instead of falling back to database items which may contain legacy sources
    return [], 0


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


