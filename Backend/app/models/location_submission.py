"""
Pydantic models for location submission system.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class LocationSubmissionCreate(BaseModel):
    """Request model for submitting a new location."""
    name: str = Field(..., min_length=1, max_length=200, description="Location name")
    address: Optional[str] = Field(None, max_length=500, description="Optional address")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    category: str = Field(..., min_length=1, max_length=100, description="Category (can be custom)")
    is_owner: bool = Field(default=False, description="Whether user is the owner of this location")


class LocationSubmissionResponse(BaseModel):
    """Response model for location submission."""
    id: int
    name: str
    address: Optional[str]
    lat: float
    lng: float
    category: str
    user_id: UUID
    is_owner: bool
    status: str  # 'pending', 'approved', 'rejected'
    submitted_at: datetime
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_location_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class GeocodeResponse(BaseModel):
    """Response model for geocoding."""
    lat: float
    lng: float
    display_name: str









