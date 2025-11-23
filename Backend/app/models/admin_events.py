from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.event_candidate import EventCandidateState

class AdminEventRawItem(BaseModel):
    id: int
    event_source_id: int
    source_key: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location_text: Optional[str] = None
    venue: Optional[str] = None
    event_url: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    processing_state: str
    language_code: Optional[str] = None
    category_key: Optional[str] = None
    summary_ai: Optional[str] = Field(default=None, description="AI-generated summary.")
    confidence_score: Optional[float] = None
    enriched_at: Optional[datetime] = None
    enriched_by: Optional[str] = None
    processing_errors: Optional[Dict[str, Any]] = None
    fetched_at: datetime


class AdminEventRawListResponse(BaseModel):
    items: List[AdminEventRawItem]
    total: int
    limit: int
    offset: int


class AdminEventCandidateItem(BaseModel):
    id: int
    event_source_id: int
    source_key: str
    source_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    location_text: Optional[str] = None
    url: Optional[str] = None
    start_time_utc: datetime
    end_time_utc: Optional[datetime] = None
    duplicate_of_id: Optional[int] = None
    duplicate_score: Optional[float] = None
    has_duplicates: bool = False
    state: EventCandidateState
    created_at: datetime
    updated_at: datetime


class AdminEventCandidateListResponse(BaseModel):
    items: List[AdminEventCandidateItem]
    total: int
    limit: int
    offset: int


class AdminEventDuplicateCluster(BaseModel):
    canonical: AdminEventCandidateItem
    duplicates: List[AdminEventCandidateItem] = Field(default_factory=list)


