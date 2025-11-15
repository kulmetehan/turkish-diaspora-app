from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AIConfig(BaseModel):
    """Full AI policy configuration model."""
    id: int = Field(default=1, description="Config row ID (always 1 for single-row table)")
    classify_min_conf: float = Field(ge=0.0, le=1.0, description="Minimum confidence for classify_bot (0.0-1.0)")
    verify_min_conf: float = Field(ge=0.0, le=1.0, description="Minimum confidence for verify_locations bot (0.0-1.0)")
    task_verifier_min_conf: float = Field(ge=0.0, le=1.0, description="Minimum confidence for task_verifier bot (0.0-1.0)")
    auto_promote_conf: float = Field(ge=0.0, le=1.0, description="Auto-promotion threshold for task_verifier (0.0-1.0)")
    monitor_low_conf_days: int = Field(ge=1, description="Freshness interval (days) for low confidence locations")
    monitor_medium_conf_days: int = Field(ge=1, description="Freshness interval (days) for medium confidence locations")
    monitor_high_conf_days: int = Field(ge=1, description="Freshness interval (days) for high confidence locations")
    monitor_verified_few_reviews_days: int = Field(ge=1, description="Freshness interval (days) for VERIFIED with < 10 reviews")
    monitor_verified_medium_reviews_days: int = Field(ge=1, description="Freshness interval (days) for VERIFIED with 10-99 reviews")
    monitor_verified_many_reviews_days: int = Field(ge=1, description="Freshness interval (days) for VERIFIED with >= 100 reviews")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    updated_by: Optional[str] = Field(default=None, description="Admin email who made the change")

    @field_validator("classify_min_conf", "verify_min_conf", "task_verifier_min_conf", "auto_promote_conf", mode="before")
    @classmethod
    def validate_threshold(cls, v: any) -> float:
        """Ensure threshold is in valid range [0.0, 1.0]."""
        try:
            f = float(v)
            if f < 0.0 or f > 1.0:
                raise ValueError(f"Threshold must be between 0.0 and 1.0, got {f}")
            return f
        except (TypeError, ValueError) as e:
            if isinstance(e, ValueError) and "must be between" in str(e):
                raise
            raise ValueError(f"Invalid threshold value: {v}") from e

    @field_validator("monitor_low_conf_days", "monitor_medium_conf_days", "monitor_high_conf_days",
                     "monitor_verified_few_reviews_days", "monitor_verified_medium_reviews_days",
                     "monitor_verified_many_reviews_days", mode="before")
    @classmethod
    def validate_days(cls, v: any) -> int:
        """Ensure days is a positive integer >= 1."""
        try:
            i = int(v)
            if i < 1:
                raise ValueError(f"Days must be >= 1, got {i}")
            return i
        except (TypeError, ValueError) as e:
            if isinstance(e, ValueError) and "must be >=" in str(e):
                raise
            raise ValueError(f"Invalid days value: {v}") from e


class AIConfigUpdate(BaseModel):
    """Update payload for AI config (all fields optional)."""
    classify_min_conf: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum confidence for classify_bot")
    verify_min_conf: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum confidence for verify_locations bot")
    task_verifier_min_conf: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum confidence for task_verifier bot")
    auto_promote_conf: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Auto-promotion threshold for task_verifier")
    monitor_low_conf_days: Optional[int] = Field(default=None, ge=1, description="Freshness interval (days) for low confidence")
    monitor_medium_conf_days: Optional[int] = Field(default=None, ge=1, description="Freshness interval (days) for medium confidence")
    monitor_high_conf_days: Optional[int] = Field(default=None, ge=1, description="Freshness interval (days) for high confidence")
    monitor_verified_few_reviews_days: Optional[int] = Field(default=None, ge=1, description="Freshness interval (days) for VERIFIED with < 10 reviews")
    monitor_verified_medium_reviews_days: Optional[int] = Field(default=None, ge=1, description="Freshness interval (days) for VERIFIED with 10-99 reviews")
    monitor_verified_many_reviews_days: Optional[int] = Field(default=None, ge=1, description="Freshness interval (days) for VERIFIED with >= 100 reviews")

    @field_validator("classify_min_conf", "verify_min_conf", "task_verifier_min_conf", "auto_promote_conf", mode="before")
    @classmethod
    def validate_threshold(cls, v: any) -> Optional[float]:
        """Ensure threshold is in valid range [0.0, 1.0]."""
        if v is None:
            return None
        try:
            f = float(v)
            if f < 0.0 or f > 1.0:
                raise ValueError(f"Threshold must be between 0.0 and 1.0, got {f}")
            return f
        except (TypeError, ValueError) as e:
            if isinstance(e, ValueError) and "must be between" in str(e):
                raise
            raise ValueError(f"Invalid threshold value: {v}") from e

    @field_validator("monitor_low_conf_days", "monitor_medium_conf_days", "monitor_high_conf_days",
                     "monitor_verified_few_reviews_days", "monitor_verified_medium_reviews_days",
                     "monitor_verified_many_reviews_days", mode="before")
    @classmethod
    def validate_days(cls, v: any) -> Optional[int]:
        """Ensure days is a positive integer >= 1."""
        if v is None:
            return None
        try:
            i = int(v)
            if i < 1:
                raise ValueError(f"Days must be >= 1, got {i}")
            return i
        except (TypeError, ValueError) as e:
            if isinstance(e, ValueError) and "must be >=" in str(e):
                raise
            raise ValueError(f"Invalid days value: {v}") from e

