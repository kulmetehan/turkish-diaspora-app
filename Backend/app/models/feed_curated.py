from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.news_public import NewsItem
from app.models.events_public import EventItem


class CategoryStat(BaseModel):
    """Category statistic for location stats."""
    category: str
    label: str
    count: int


class CuratedNewsResponse(BaseModel):
    """Response for curated news items."""
    items: List[NewsItem] = Field(..., description="Top 3 AI-curated news items")
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata: total_ranked, cached_at, etc."
    )


class LocationStatsResponse(BaseModel):
    """Response for location statistics."""
    total: int = Field(..., description="Total number of Turkish locations in Netherlands")
    categories: List[CategoryStat] = Field(
        default_factory=list,
        description="Randomly selected 2-3 categories with counts"
    )
    formatted_text: str = Field(
        ...,
        description="Formatted text like '1051 Turkse locaties in Nederland. Waarvan 25 bakkers en 30 supermarkten.'"
    )


class CuratedEventsResponse(BaseModel):
    """Response for curated events."""
    items: List[EventItem] = Field(..., description="Top 3 AI-curated events")
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata: total_ranked, cached_at, etc."
    )
