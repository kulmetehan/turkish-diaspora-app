from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel


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


class MetricsSnapshot(BaseModel):
    city_progress: CityProgress
    quality: Quality
    discovery: Discovery
    latency: Latency
    weekly_candidates: Optional[List[WeeklyCandidatesItem]] = None


