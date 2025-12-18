from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
    lat: Optional[float] = None
    lng: Optional[float] = None
    reactions: Optional[Dict[str, int]] = Field(
        default=None,
        description="Reaction counts: {'fire': 5, 'heart': 3, ...}",
    )
    user_reaction: Optional[str] = Field(
        default=None,
        description="Current user's reaction type, if any",
    )


class EventsListResponse(BaseModel):
    """Paginated response for /api/v1/events."""

    items: List[EventItem]
    total: int
    limit: int
    offset: int



