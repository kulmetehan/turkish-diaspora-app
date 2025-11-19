from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.categories import get_all_categories
from services.db_service import fetch

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/location-states", response_model=Dict[str, Any])
async def list_location_states_alias(
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, Any]:
    """
    Alias for listing all values of the location_state enum for admin dropdowns.
    Mirrors the handler in admin_locations but exposed at /api/v1/admin/location-states.
    """
    rows = await fetch("SELECT unnest(enum_range(NULL::location_state))::text AS value")

    def to_label(value: str) -> str:
        return value.replace("_", " ").title()

    states = [{"value": rec["value"], "label": to_label(rec["value"])} for rec in rows]
    return {"states": states}


@router.get("/location-categories", response_model=Dict[str, Any])
async def list_location_categories_alias(
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, Any]:
    """
    Return all categories from the central registry for admin dropdowns.
    
    Uses the dynamic category registry (categories.yml) instead of querying
    the database, ensuring new categories appear immediately even if no
    locations exist yet.
    
    Returns format: {"categories": [{"key": "...", "label": "..."}, ...]}
    """
    try:
        all_categories = get_all_categories()
        # Filter out "other" category as it's a fallback, not a discovery target
        categories = [
            {"key": cat.key, "label": cat.label}
            for cat in all_categories
            if cat.key != "other"
        ]
        return {"categories": categories}
    except Exception as e:
        # Fallback to empty list if registry fails to load
        return {"categories": []}

