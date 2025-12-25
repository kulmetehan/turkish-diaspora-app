from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ContactSource = Literal["osm", "website", "google", "social"]


class ContactInfo(BaseModel):
    """
    Contact information discovered for a location.
    
    Used by the contact discovery service to represent discovered contact data
    with confidence scoring for outreach purposes.
    """
    
    email: str = Field(..., description="Discovered email address")
    source: ContactSource = Field(..., description="Source of contact discovery")
    confidence_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score (0-100) for the discovered contact"
    )
    discovered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when contact was discovered"
    )
    
    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        """Basic email format validation."""
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("email cannot be empty")
        if "@" not in cleaned or "." not in cleaned.split("@")[1]:
            raise ValueError("email must have valid format")
        return cleaned

