from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator

EventFormat = Literal["html", "rss", "json"]


class EventRawBase(BaseModel):
    event_source_id: int = Field(..., gt=0)
    title: Optional[str] = None
    description: Optional[str] = None
    location_text: Optional[str] = None
    venue: Optional[str] = None
    event_url: Optional[str] = None
    image_url: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    detected_format: EventFormat = Field(default="html")
    ingest_hash: str = Field(..., min_length=40, max_length=40)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    processing_state: str = Field(default="pending")
    processing_errors: Optional[Dict[str, Any]] = None
    language_code: Optional[str] = None
    category_key: Optional[str] = None
    summary_ai: Optional[str] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    enriched_at: Optional[datetime] = None
    enriched_by: Optional[str] = None

    @field_validator("ingest_hash")
    @classmethod
    def _normalize_hash(cls, value: str) -> str:
        cleaned = (value or "").strip().lower()
        if len(cleaned) != 40:
            raise ValueError("ingest_hash must be a 40-character sha1 hex string")
        return cleaned


class EventRawCreate(EventRawBase):
    pass


class EventRaw(EventRawBase):
    id: int
    fetched_at: datetime
    created_at: datetime


