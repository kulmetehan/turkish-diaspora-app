from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.news_public import NewsListResponse
from services.news_feed_rules import FeedType
from services.news_service import (
    ALLOWED_NEWS_THEMES,
    list_news_by_feed,
    list_trending_news,
    search_news as search_news_service,
)

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
        items, total = await list_trending_news(limit=limit, offset=offset)
        return NewsListResponse(items=items, total=total, limit=limit, offset=offset)

    try:
        feed_enum = FeedType(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feed '{feed}'. Allowed values: {_ALLOWED_FEEDS}.",
        ) from exc

    try:
        items, total = await list_news_by_feed(
            feed_enum,
            limit=limit,
            offset=offset,
            themes=theme_values,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return NewsListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/trending", response_model=NewsListResponse)
async def get_trending_news(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> NewsListResponse:
    items, total = await list_trending_news(limit=limit, offset=offset)
    return NewsListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/search", response_model=NewsListResponse)
async def search_news(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> NewsListResponse:
    items, total = await search_news_service(query=q, limit=limit, offset=offset)
    return NewsListResponse(items=items, total=total, limit=limit, offset=offset)


