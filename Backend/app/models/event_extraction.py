from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExtractedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    start_at: datetime
    end_at: Optional[datetime] = None
    location_text: Optional[str] = None
    venue: Optional[str] = None
    event_url: Optional[str] = None
    image_url: Optional[str] = None

    @field_validator("title")
    @classmethod
    def _normalize_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title cannot be empty")
        return cleaned

    @field_validator("description", "location_text", "venue", "event_url", "image_url")
    @classmethod
    def _strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ExtractedEventsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: List[ExtractedEvent] = Field(default_factory=list)


