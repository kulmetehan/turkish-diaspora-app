from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class NormalizedNewsItem(BaseModel):
    """
    Canonical, normalized representation of a single news entry,
    used by the RSS/Atom normalization engine (N1.3).
    This model intentionally contains only the minimal fields required
    by downstream pipelines (AI enrichment, analytics, etc.).
    """

    title: str
    url: str
    snippet: str
    source: str
    published_at: datetime
    # Full original entry (feedparser/Atom dict), kept for debugging
    # and secondary processing steps.
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)

