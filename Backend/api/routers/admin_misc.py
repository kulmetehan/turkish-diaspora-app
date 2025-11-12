from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.deps.admin_auth import AdminUser, verify_admin_user
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
