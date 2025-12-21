from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

EVENT_CANDIDATE_STATES = ("candidate", "verified", "published", "rejected")
EventCandidateState = Literal["candidate", "verified", "published", "rejected"]


class EventCandidateBase(BaseModel):
    event_source_id: int = Field(..., gt=0)
    event_raw_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    duplicate_of_id: Optional[int] = Field(default=None, ge=1)
    duplicate_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    start_time_utc: datetime
    end_time_utc: Optional[datetime] = None
    location_text: Optional[str] = None
    url: Optional[str] = None
    source_key: str = Field(..., min_length=1)
    ingest_hash: str = Field(..., min_length=8)
    state: EventCandidateState = Field(default="candidate")
    event_category: Optional[str] = None

    @field_validator("title")
    @classmethod
    def _normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title cannot be empty")
        return normalized

    @field_validator("source_key")
    @classmethod
    def _normalize_source_key(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("source_key cannot be empty")
        return normalized

    @field_validator("state")
    @classmethod
    def _normalize_state(cls, value: str) -> EventCandidateState:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("state cannot be empty")
        if normalized not in EVENT_CANDIDATE_STATES:
            raise ValueError(f"state must be one of: {', '.join(EVENT_CANDIDATE_STATES)}")
        return normalized  # type: ignore[return-value]


class EventCandidateCreate(EventCandidateBase):
    pass


class EventCandidate(EventCandidateBase):
    id: int
    created_at: datetime
    updated_at: datetime


