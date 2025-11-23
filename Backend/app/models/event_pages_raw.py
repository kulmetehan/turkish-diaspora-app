from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

EVENT_PAGE_PROCESSING_STATES = (
    "pending",
    "extracted",
    "error_fetch",
    "error_extract",
)


class EventPageRawBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_source_id: int = Field(..., gt=0)
    page_url: str = Field(..., min_length=1)
    http_status: Optional[int] = Field(default=None, ge=100, le=599)
    response_headers: Dict[str, Any] = Field(default_factory=dict)
    response_body: str = Field(..., min_length=1)
    content_hash: str = Field(..., min_length=40, max_length=40)
    processing_state: str = Field(default="pending")
    processing_errors: Optional[Dict[str, Any]] = None

    @field_validator("page_url")
    @classmethod
    def _validate_page_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("page_url cannot be empty")
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("page_url must start with http:// or https://")
        return cleaned

    @field_validator("response_body")
    @classmethod
    def _validate_body(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("response_body cannot be empty")
        return value

    @field_validator("content_hash")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        cleaned = (value or "").strip().lower()
        if len(cleaned) != 40:
            raise ValueError("content_hash must be a 40-character sha1 hex string")
        return cleaned

    @field_validator("processing_state")
    @classmethod
    def _validate_state(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in EVENT_PAGE_PROCESSING_STATES:
            allowed = ", ".join(EVENT_PAGE_PROCESSING_STATES)
            raise ValueError(f"processing_state must be one of: {allowed}")
        return normalized


class EventPageRawCreate(EventPageRawBase):
    pass


class EventPageRaw(EventPageRawBase):
    id: int
    fetched_at: datetime
    created_at: datetime


