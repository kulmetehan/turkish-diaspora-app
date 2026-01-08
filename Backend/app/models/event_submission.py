"""
Pydantic models for event submission system.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from uuid import UUID
from datetime import datetime


class EventSubmissionCreate(BaseModel):
    """Request model for submitting a new event."""
    title: str = Field(..., min_length=1, max_length=200, description="Event title")
    description: Optional[str] = Field(None, max_length=2000, description="Optional event description")
    start_time_utc: datetime = Field(..., description="Event start time in UTC")
    end_time_utc: Optional[datetime] = Field(None, description="Optional event end time in UTC")
    location_text: Optional[str] = Field(None, max_length=500, description="Optional location text")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Optional latitude")
    lng: Optional[float] = Field(None, ge=-180, le=180, description="Optional longitude")
    url: Optional[str] = Field(None, max_length=500, description="Optional event URL")
    category_key: Optional[str] = Field(None, max_length=100, description="Optional event category")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Basic URL validation."""
        if v is None or not v.strip():
            return None
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @model_validator(mode="after")
    def validate_end_time_after_start(self):
        """Ensure end_time is after start_time if both are provided."""
        if self.end_time_utc is not None and self.end_time_utc <= self.start_time_utc:
            raise ValueError("end_time_utc must be after start_time_utc")
        return self


class EventSubmissionResponse(BaseModel):
    """Response model for event submission."""
    id: int
    title: str
    description: Optional[str]
    start_time_utc: datetime
    end_time_utc: Optional[datetime]
    location_text: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    url: Optional[str]
    category_key: Optional[str]
    user_id: UUID
    status: str  # 'pending', 'approved', 'rejected'
    submitted_at: datetime
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_event_id: Optional[int]
    created_at: datetime
    updated_at: datetime

