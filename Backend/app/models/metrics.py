from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, Literal

from pydantic import BaseModel, Field


class CityProgressRotterdam(BaseModel):
    verified_count: int
    candidate_count: int
    coverage_ratio: float
    growth_weekly: float


class CityProgress(BaseModel):
    rotterdam: CityProgressRotterdam


class Quality(BaseModel):
    conversion_rate_verified_14d: float
    task_error_rate_60m: float
    google429_last60m: int


class Discovery(BaseModel):
    new_candidates_per_week: int


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


class MetricsSnapshot(BaseModel):
    city_progress: CityProgress
    quality: Quality
    discovery: Discovery
    latency: Latency
    weekly_candidates: Optional[List[WeeklyCandidatesItem]] = None
    workers: List[WorkerStatus] = Field(default_factory=list)


