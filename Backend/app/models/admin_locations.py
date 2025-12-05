from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Union
from typing import Literal
from pydantic import BaseModel, Field, validator


class AdminLocationListItem(BaseModel):
    id: int
    name: str
    category: Optional[str]
    state: str
    confidence_score: Optional[float]
    last_verified_at: Optional[datetime]
    is_retired: Optional[bool] = None


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
    force: Optional[bool] = None


class AdminVerifyBulkAction(BaseModel):
    """Bulk action payload for verifying locations."""

    type: Literal["verify"] = Field(description="Promote selected locations to VERIFIED.")
    force: bool = Field(
        default=False,
        description="When true, bypass RETIRED guard and allow resurrecting records.",
    )
    clear_retired: bool = Field(
        default=False,
        description="When true, explicitly clear the is_retired flag for selected records.",
    )

    class Config:
        extra = "forbid"


class AdminRetireBulkAction(BaseModel):
    """Bulk action payload for retiring locations."""

    type: Literal["retire"] = Field(description="Retire the selected locations.")

    class Config:
        extra = "forbid"


class AdminAdjustConfidenceBulkAction(BaseModel):
    """Bulk action payload for adjusting a location confidence score."""

    type: Literal["adjust_confidence"] = Field(
        description="Adjust confidence_score for selected locations."
    )
    value: float = Field(description="Desired confidence score between 0 and 1 inclusive.")

    class Config:
        extra = "forbid"

    @validator("value")
    def _clamp_value(cls, v: float) -> float:  # noqa: N805
        if v is None:
            raise ValueError("value is required")
        return max(0.0, min(1.0, float(v)))


AdminLocationsBulkAction = Union[
    AdminVerifyBulkAction,
    AdminRetireBulkAction,
    AdminAdjustConfidenceBulkAction,
]


class AdminLocationsBulkUpdateRequest(BaseModel):
    """Request body for PATCH /admin/locations/bulk-update."""

    ids: List[int] = Field(..., min_items=1, description="Location IDs to mutate.")
    action: AdminLocationsBulkAction

    class Config:
        extra = "forbid"

    @validator("ids")
    def _dedupe_ids(cls, value: List[int]) -> List[int]:  # noqa: N805
        deduped = []
        seen = set()
        for raw in value:
            try:
                item = int(raw)
            except Exception as exc:
                raise ValueError(f"invalid id provided: {raw}") from exc
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped


class AdminLocationsBulkUpdateError(BaseModel):
    """Per-location error details returned for bulk update processing."""

    id: int
    detail: str


class AdminLocationsBulkUpdateResponse(BaseModel):
    """Response shape for bulk update operations."""

    ok: bool
    updated: List[int]
    errors: List[AdminLocationsBulkUpdateError]


class AdminLocationBulkImportError(BaseModel):
    """Per-row error details returned for bulk import processing."""

    row_number: int  # 1-based data row index (excluding header)
    message: str


class AdminLocationBulkImportResult(BaseModel):
    """Response shape for bulk import operations."""

    rows_total: int
    rows_processed: int
    rows_created: int
    rows_failed: int
    errors: List[AdminLocationBulkImportError]


