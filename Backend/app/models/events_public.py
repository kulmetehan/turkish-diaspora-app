from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class EventItem(BaseModel):
    """Public-facing event payload."""

    id: int
    title: str
    description: Optional[str] = None
    start_time_utc: datetime
    end_time_utc: Optional[datetime] = None
    city_key: Optional[str] = None
    category_key: Optional[str] = None
    location_text: Optional[str] = None
    url: Optional[str] = None
    source_key: str
    summary_ai: Optional[str] = None
    updated_at: datetime


class EventsListResponse(BaseModel):
    """Paginated response for /api/v1/events."""

    items: List[EventItem]
    total: int
    limit: int
    offset: int

