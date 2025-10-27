from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AdminLocationListItem(BaseModel):
    id: int
    name: str
    category: Optional[str]
    state: str
    confidence_score: Optional[float]
    last_verified_at: Optional[datetime]


class AdminLocationDetail(AdminLocationListItem):
    address: Optional[str]
    notes: Optional[str]
    business_status: Optional[str]
    rating: Optional[float]
    user_ratings_total: Optional[int]
    is_probable_not_open_yet: Optional[bool]


class AdminLocationUpdateRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    state: Optional[str] = None
    notes: Optional[str] = None
    business_status: Optional[str] = None
    is_probable_not_open_yet: Optional[bool] = None
    confidence_score: Optional[float] = None


