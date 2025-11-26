from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """Public-facing news article payload."""

    id: int
    title: str
    snippet: Optional[str] = Field(
        default=None,
        description="Short summary derived from article metadata.",
    )
    source: str
    published_at: datetime
    url: str
    image_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class NewsListResponse(BaseModel):
    """Paginated response for /api/v1/news."""

    items: List[NewsItem]
    total: int
    limit: int
    offset: int


class NewsCityRecord(BaseModel):
    city_key: str
    name: str
    country: str
    province: Optional[str] = None
    parent_key: Optional[str] = None
    population: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class NewsCityListResponse(BaseModel):
    cities: List[NewsCityRecord]
    defaults: Dict[str, List[str]] = Field(default_factory=dict)





