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


class EventStateMetrics(BaseModel):
    """Metrics about event states and visibility."""
    total_candidates: int = Field(description="Total number of events in events_candidate table")
    by_state: Dict[str, int] = Field(description="Count of events per state (candidate, verified, published, rejected)")
    visible_in_frontend: int = Field(description="Count of events visible in frontend (published, future events only, matching frontend API filter)")
    published_not_visible: int = Field(description="Count of published events that are not visible (filtered by country/location)")
    duplicate_count: int = Field(description="Count of events marked as duplicates (have duplicate_of_id)")
    canonical_with_duplicates: int = Field(description="Count of canonical events that have duplicates pointing to them")


class EventSourceDiagnostics(BaseModel):
    """Diagnostic information for an event source showing pipeline status."""
    source_id: int
    source_key: str
    source_name: str
    status: str
    last_run_at: Optional[str] = Field(default=None, description="Last time source was scraped")
    last_success_at: Optional[str] = Field(default=None, description="Last successful scrape")
    last_error: Optional[str] = Field(default=None, description="Last error message if any")
    pages_raw_count: int = Field(description="Total pages scraped")
    pages_pending: int = Field(description="Pages waiting for AI extraction")
    pages_extracted: int = Field(description="Pages successfully extracted")
    pages_error: int = Field(description="Pages with extraction errors")
    events_raw_count: int = Field(description="Total raw events extracted")
    events_raw_pending: int = Field(description="Raw events waiting for normalization")
    events_raw_enriched: int = Field(description="Raw events enriched and ready")
    events_raw_error: int = Field(description="Raw events with errors")
    events_candidate_count: int = Field(description="Total normalized candidate events")
    events_candidate_by_state: Dict[str, int] = Field(description="Candidates by state")
    events_published_count: int = Field(description="Published events from this source")
    events_visible_in_frontend: int = Field(description="Published events visible on frontend (future events)")


