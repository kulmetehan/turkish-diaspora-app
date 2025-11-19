from __future__ import annotations

from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

from app.models.categories import get_all_categories, get_discoverable_categories, CategoryMetadata

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)


class CategoryResponse(BaseModel):
    """Category information for API responses."""
    key: str
    label: str
    description: str
    aliases: List[str]
    google_types: List[str]
    osm_tags: dict | None
    is_discoverable: bool
    discovery_priority: int

    @classmethod
    def from_metadata(cls, metadata: CategoryMetadata) -> "CategoryResponse":
        """Create response from CategoryMetadata."""
        return cls(
            key=metadata.key,
            label=metadata.label,
            description=metadata.description,
            aliases=metadata.aliases,
            google_types=metadata.google_types,
            osm_tags=metadata.osm_tags,
            is_discoverable=metadata.discovery_enabled,
            discovery_priority=metadata.discovery_priority,
        )


@router.get("", response_model=List[CategoryResponse])
async def get_categories(discoverable_only: bool = False) -> List[CategoryResponse]:
    """
    Get all categories or only discoverable ones.
    
    Args:
        discoverable_only: If True, return only categories with discovery.enabled=true
        
    Returns:
        List of category information including key, label, description, aliases, etc.
    """
    if discoverable_only:
        categories = get_discoverable_categories()
    else:
        categories = get_all_categories()
    
    return [CategoryResponse.from_metadata(cat) for cat in categories]

