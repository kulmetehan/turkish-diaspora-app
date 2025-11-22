from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CityProgressRotterdam(BaseModel):
    verified_count: int
    candidate_count: int
    coverage_ratio: float
    growth_weekly: float


class CityProgressData(BaseModel):
    """Generic city progress data (same structure as CityProgressRotterdam)."""
    verified_count: int
    candidate_count: int
    coverage_ratio: float
    growth_weekly: float


class CityReadiness(BaseModel):
    """City configuration and readiness status."""
    city_key: str
    city_name: str
    has_districts: bool
    districts_count: int
    verified_count: int
    candidate_count: int
    coverage_ratio: float
    growth_weekly: Optional[float]
    readiness_status: Literal["active", "configured_inactive", "config_incomplete"]
    readiness_notes: Optional[str] = None


class CitiesOverview(BaseModel):
    """Overview of all cities with their readiness status."""
    cities: List[CityReadiness] = Field(default_factory=list)


class CityProgress(BaseModel):
    """Multi-city progress metrics. Keys are city keys from cities.yml."""
    # Store as a dict to support dynamic city keys
    cities: Dict[str, CityProgressData] = Field(default_factory=dict)
    
    def __getitem__(self, key: str) -> CityProgressData:
        """Get progress data for a specific city."""
        return self.cities[key]
    
    def __setitem__(self, key: str, value: CityProgressData) -> None:
        """Set progress data for a specific city."""
        self.cities[key] = value
    
    def get(self, key: str, default: Optional[CityProgressData] = None) -> Optional[CityProgressData]:
        """Get progress data with optional default."""
        return self.cities.get(key, default)
    
    @property
    def rotterdam(self) -> Optional[CityProgressRotterdam]:
        """Backward compatibility: access rotterdam as CityProgressRotterdam."""
        rot_data = self.cities.get("rotterdam")
        if rot_data:
            return CityProgressRotterdam(
                verified_count=rot_data.verified_count,
                candidate_count=rot_data.candidate_count,
                coverage_ratio=rot_data.coverage_ratio,
                growth_weekly=rot_data.growth_weekly,
            )
        return None


class Quality(BaseModel):
    conversion_rate_verified_14d: float
    task_error_rate_60m: float
    google429_last60m: int


class Discovery(BaseModel):
    new_candidates_per_week: int


class NewsTrendingMetrics(BaseModel):
    window_hours: int
    eligible_count: int
    sample_titles: List[str] = Field(default_factory=list)


class NewsPerDayItem(BaseModel):
    date: date
    count: int


class NewsLabelCount(BaseModel):
    label: str
    count: int


class NewsErrorMetrics(BaseModel):
    ingest_errors_last_24h: int
    classify_errors_last_24h: int
    pending_items_last_24h: int


class NewsMetricsSnapshot(BaseModel):
    items_per_day_last_7d: List[NewsPerDayItem] = Field(default_factory=list)
    items_by_source_last_24h: List[NewsLabelCount] = Field(default_factory=list)
    items_by_feed_last_24h: List[NewsLabelCount] = Field(default_factory=list)
    errors: NewsErrorMetrics


class StaleCandidates(BaseModel):
    """Metrics for stale CANDIDATE records (older than threshold days)."""
    total_stale: int
    by_source: Dict[str, int] = Field(default_factory=dict)
    by_city: Dict[str, int] = Field(default_factory=dict)
    days_threshold: int


class Latency(BaseModel):
    p50_ms: int
    avg_ms: int
    max_ms: int


class WeeklyCandidatesItem(BaseModel):
    week_start: date
    count: int


class WorkerStatus(BaseModel):
    id: str
    label: str
    last_run: Optional[datetime]
    duration_seconds: Optional[float]
    processed_count: Optional[int]
    error_count: Optional[int]
    status: Literal["ok", "warning", "error", "unknown"]
    window_label: Optional[str] = None
    quota_info: Optional[Dict[str, Optional[int]]] = None
    notes: Optional[str] = None
    diagnosis_code: Optional[str] = None
    worker_type: Optional[Literal["queue_based", "direct", "legacy"]] = None


class WorkerRunStatus(BaseModel):
    id: UUID
    bot: str
    city: Optional[str]
    category: Optional[str]
    status: str
    progress: int
    started_at: Optional[datetime]


class MetricsSnapshot(BaseModel):
    city_progress: CityProgress
    quality: Quality
    discovery: Discovery
    news_trending: Optional[NewsTrendingMetrics] = None
    latency: Latency
    weekly_candidates: Optional[List[WeeklyCandidatesItem]] = None
    workers: List[WorkerStatus] = Field(default_factory=list)
    current_runs: List[WorkerRunStatus] = Field(default_factory=list)
    stale_candidates: Optional[StaleCandidates] = None


class CategoryHealth(BaseModel):
    """Health metrics for a single category."""
    overpass_calls: int
    overpass_successful_calls: int
    overpass_zero_results: int
    overpass_zero_result_ratio_pct: float
    inserted_locations_last_7d: int
    state_counts: Dict[str, int] = Field(default_factory=dict)
    avg_confidence_last_7d: Optional[float] = None
    ai_classifications_last_7d: int
    ai_action_keep: int
    ai_action_ignore: int
    ai_avg_confidence: Optional[float] = None
    promoted_verified_last_7d: int
    # New fields for Turkish-first strategy metrics
    overpass_found: int = 0
    turkish_coverage_ratio_pct: float = 0.0
    ai_precision_pct: float = 0.0
    status: Literal["healthy", "warning", "degraded", "critical", "no_data"] = "no_data"


class CategoryHealthResponse(BaseModel):
    """Response model for category health metrics endpoint."""
    categories: Dict[str, CategoryHealth] = Field(default_factory=dict)
    time_windows: Dict[str, int] = Field(
        default_factory=lambda: {
            "overpass_window_hours": 72,
            "inserts_window_days": 7,
            "classifications_window_days": 7,
            "promotions_window_days": 7,
        }
    )


class LocationStateBucket(BaseModel):
    """Count of locations in a specific state."""
    state: str
    count: int


class LocationStateMetrics(BaseModel):
    """Location state breakdown metrics."""
    total: int
    by_state: List[LocationStateBucket] = Field(default_factory=list)


