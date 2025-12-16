from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

NEWS_PAGE_PROCESSING_STATES = (
    "pending",
    "extracted",
    "error_fetch",
    "error_extract",
)


class NewsPageRawBase(BaseModel):
    """Base model for raw news page storage."""

    model_config = ConfigDict(extra="forbid")

    news_source_key: str = Field(..., min_length=1, description="Source key identifier")
    page_url: str = Field(..., min_length=1, description="URL of the scraped page")
    http_status: Optional[int] = Field(default=None, ge=100, le=599, description="HTTP status code")
    response_headers: Dict[str, Any] = Field(
        default_factory=dict,
        description="HTTP response headers as dictionary",
    )
    response_body: str = Field(..., min_length=1, description="Raw HTML response body")
    content_hash: str = Field(..., min_length=40, max_length=40, description="SHA1 hash for deduplication")
    processing_state: str = Field(default="pending", description="Current processing state")
    processing_errors: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Error details if processing failed",
    )

    @field_validator("news_source_key")
    @classmethod
    def _validate_source_key(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("news_source_key cannot be empty")
        return cleaned

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
        if normalized not in NEWS_PAGE_PROCESSING_STATES:
            allowed = ", ".join(NEWS_PAGE_PROCESSING_STATES)
            raise ValueError(f"processing_state must be one of: {allowed}")
        return normalized


class NewsPageRawCreate(NewsPageRawBase):
    """Model for creating a new news page raw record."""

    pass


class NewsPageRaw(NewsPageRawBase):
    """Model for an existing news page raw record."""

    id: int
    fetched_at: datetime
    created_at: datetime










