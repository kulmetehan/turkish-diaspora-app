from __future__ import annotations

from datetime import datetime
from typing import List, Optional

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



