"""
Pydantic models for city and district management in admin interface.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class DistrictCreate(BaseModel):
    """Request model for creating a new district."""
    name: str = Field(..., description="District name (e.g., 'Centrum', 'Zuid')")
    center_lat: float = Field(..., ge=-90.0, le=90.0, description="Center latitude")
    center_lng: float = Field(..., ge=-180.0, le=180.0, description="Center longitude")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("District name cannot be empty")
        return v.strip()


class DistrictUpdate(BaseModel):
    """Request model for updating an existing district."""
    name: Optional[str] = Field(None, description="District name")
    center_lat: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Center latitude")
    center_lng: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Center longitude")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError("District name cannot be empty")
        return v.strip() if v else None


class CityCreate(BaseModel):
    """Request model for creating a new city."""
    city_name: str = Field(..., description="City name (e.g., 'Rotterdam', 'Den Haag')")
    country: str = Field(default="NL", min_length=2, max_length=2, description="2-letter country code")
    center_lat: float = Field(..., ge=-90.0, le=90.0, description="City center latitude")
    center_lng: float = Field(..., ge=-180.0, le=180.0, description="City center longitude")
    districts: Optional[List[DistrictCreate]] = Field(
        default=None,
        description="Optional list of districts to create along with the city"
    )
    
    @field_validator("city_name")
    @classmethod
    def validate_city_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("City name cannot be empty")
        return v.strip()
    
    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        return v.upper().strip()


class CityUpdate(BaseModel):
    """Request model for updating an existing city."""
    city_name: Optional[str] = Field(None, description="City name")
    country: Optional[str] = Field(None, min_length=2, max_length=2, description="2-letter country code")
    center_lat: Optional[float] = Field(None, ge=-90.0, le=90.0, description="City center latitude")
    center_lng: Optional[float] = Field(None, ge=-180.0, le=180.0, description="City center longitude")
    
    @field_validator("city_name")
    @classmethod
    def validate_city_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError("City name cannot be empty")
        return v.strip() if v else None
    
    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.upper().strip()
        return v


class DistrictDetail(BaseModel):
    """Response model for district details."""
    key: str = Field(..., description="District key (normalized name)")
    name: str = Field(..., description="District display name")
    center_lat: float = Field(..., description="Center latitude")
    center_lng: float = Field(..., description="Center longitude")
    bbox: dict[str, float] = Field(..., description="Bounding box with lat_min, lat_max, lng_min, lng_max")


class CityDetailResponse(BaseModel):
    """Response model for full city details including districts."""
    city_key: str
    city_name: str
    country: str
    center_lat: float
    center_lng: float
    districts: List[DistrictDetail] = Field(default_factory=list)

