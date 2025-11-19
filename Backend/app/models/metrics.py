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
    latency: Latency
    weekly_candidates: Optional[List[WeeklyCandidatesItem]] = None
    workers: List[WorkerStatus] = Field(default_factory=list)
    current_runs: List[WorkerRunStatus] = Field(default_factory=list)
    stale_candidates: Optional[StaleCandidates] = None


