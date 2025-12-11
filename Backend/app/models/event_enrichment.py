from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

SupportedLanguage = Literal["nl", "tr", "en", "other"]


class EventEnrichmentResult(BaseModel):
    """
    Structured AI response for event enrichment.
    """

    language_code: SupportedLanguage = Field(
        ...,
        description="Detected language code (nl, tr, en, or other).",
    )
    category_key: str = Field(..., min_length=1, description="Canonical event category key.")
    summary: str = Field(..., min_length=1, max_length=1000, description="Short natural-language summary.")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence 0..1.")
    extracted_location_text: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Location extracted from title/description/venue if location_text was missing or empty.",
    )

    @field_validator("language_code", mode="before")
    @classmethod
    def _normalize_language(cls, value: Optional[str]) -> SupportedLanguage:
        normalized = (value or "").strip().lower()
        if normalized in ("nl", "tr", "en"):
            return normalized  # type: ignore[return-value]
        return "other"  # type: ignore[return-value]

    @field_validator("category_key", mode="before")
    @classmethod
    def _normalize_category(cls, value: Optional[str]) -> str:
        if not value:
            return "other"
        return value.strip().lower().replace(" ", "_")

    @field_validator("summary")
    @classmethod
    def _trim_summary(cls, value: str) -> str:
        return value.strip()

    @field_validator("extracted_location_text", mode="before")
    @classmethod
    def _normalize_extracted_location(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        normalized = value.strip()
        return normalized if normalized else None




