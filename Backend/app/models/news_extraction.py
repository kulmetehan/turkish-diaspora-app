from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExtractedNewsItem(BaseModel):
    """Single extracted news article from HTML."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, description="Article title")
    snippet: Optional[str] = Field(
        default=None,
        description="Short summary or excerpt (first 200 words recommended)",
    )
    published_at: datetime = Field(..., description="Publication date/time (ISO 8601)")
    url: str = Field(..., min_length=1, description="Full article URL")
    image_url: Optional[str] = Field(
        default=None,
        description="Article featured image URL (if available)",
    )
    source: str = Field(..., min_length=1, description="Source name (e.g., 'Turkse Media')")

    @field_validator("title")
    @classmethod
    def _normalize_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title cannot be empty")
        return cleaned

    @field_validator("snippet", "url", "image_url", "source")
    @classmethod
    def _strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("url", "image_url")
    @classmethod
    def _validate_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return cleaned


class ExtractedNewsPayload(BaseModel):
    """Payload containing multiple extracted news articles."""

    model_config = ConfigDict(extra="forbid")

    articles: List[ExtractedNewsItem] = Field(
        default_factory=list,
        description="List of extracted news articles",
    )










