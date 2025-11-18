from __future__ import annotations

from typing import Any, Dict, List

import pytest
from httpx import AsyncClient

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.main import app
from services.db_service import execute, fetchrow

pytestmark = pytest.mark.asyncio


async def _insert_location(
    *,
    name: str,
    state: str,
    confidence: float | None,
    category: str | None = None,
    is_retired: bool = False,
) -> int:
    row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, last_verified_at, is_retired)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
        """,
        name,
        "Forcepad 1",
        category,
        state,
        confidence,
        None,
        is_retired,
    )
    assert row is not None
    return int(row["id"])


async def _fetch_location(location_id: int) -> Dict[str, Any] | None:
    row = await fetchrow(
        """
        SELECT id, state, confidence_score, last_verified_at, category, is_retired
        FROM locations
        WHERE id = $1
        """,
        int(location_id),
    )
    return dict(row) if row else None


@pytest.fixture(autouse=True)
async def cleanup_locations() -> List[int]:
    created: List[int] = []
    yield created
    if created:
        await execute(
            "DELETE FROM locations WHERE id = ANY($1::bigint[])",
            created,
        )


@pytest.fixture
async def admin_client(cleanup_locations: List[int]):  # noqa: D401
    """HTTP client with admin auth override applied."""

    async def _override() -> AdminUser:
        return AdminUser(email="admin@test.local")

    app.dependency_overrides[verify_admin_user] = _override
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(verify_admin_user, None)


async def test_put_verify_retired_without_force_fails(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    location_id = await _insert_location(
        name="Retired Bakery",
        state="RETIRED",
        confidence=0.91,
        category="bakery",
        is_retired=True,
    )
    cleanup_locations.append(location_id)

    resp = await admin_client.put(
        f"/api/v1/admin/locations/{location_id}",
        json={"state": "VERIFIED"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["detail"] == "Cannot verify a retired location without force flag."

    refreshed = await _fetch_location(location_id)
    assert refreshed is not None
    assert refreshed["state"] == "RETIRED"
    assert refreshed["is_retired"] is True


async def test_put_verify_retired_with_force_promotes(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    location_id = await _insert_location(
        name="Retired With Force",
        state="RETIRED",
        confidence=0.5,
        category="restaurant",
        is_retired=True,
    )
    cleanup_locations.append(location_id)

    resp = await admin_client.put(
        f"/api/v1/admin/locations/{location_id}",
        json={"state": "VERIFIED", "force": True},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["state"] == "VERIFIED"

    refreshed = await _fetch_location(location_id)
    assert refreshed is not None
    assert refreshed["state"] == "VERIFIED"
    assert refreshed["is_retired"] is False
    assert refreshed["last_verified_at"] is not None
    assert float(refreshed["confidence_score"]) >= 0.9





