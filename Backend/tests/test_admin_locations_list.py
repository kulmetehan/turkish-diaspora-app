from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest
from httpx import AsyncClient

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.main import app
from services.db_service import execute, fetchrow

pytestmark = pytest.mark.asyncio


async def _insert_location(
    *,
    name: str,
    category: Optional[str] = None,
    state: str = "CANDIDATE",
    confidence: Optional[float] = None,
    first_seen_at: Optional[str] = None,
    last_verified_at: Optional[str] = None,
) -> int:
    row = await fetchrow(
        """
        INSERT INTO locations (
            name,
            address,
            category,
            state,
            confidence_score,
            first_seen_at,
            last_verified_at
        )
        VALUES ($1, 'Adres 1', $2, $3, $4, COALESCE($5, NOW()), $6)
        RETURNING id
        """,
        name,
        category,
        state,
        confidence,
        first_seen_at,
        last_verified_at,
    )
    assert row is not None
    return int(row["id"])


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


def _ids(payload: Dict[str, Any]) -> List[int]:
    return [row["id"] for row in payload["rows"]]


async def test_admin_locations_basic_list_does_not_error(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    resp = await admin_client.get("/api/v1/admin/locations?limit=20&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("rows"), list)
    assert isinstance(data.get("total"), int)


async def test_default_order_is_id_desc(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    first = await _insert_location(name="Alpha")
    second = await _insert_location(name="Beta")
    cleanup_locations.extend([first, second])

    resp = await admin_client.get("/api/v1/admin/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert _ids(data)[:2] == [second, first]


async def test_latest_added_sort_orders_by_first_seen(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    older = await _insert_location(name="Older", first_seen_at="2024-01-01T00:00:00Z")
    newest = await _insert_location(name="Newest", first_seen_at="2024-02-01T00:00:00Z")
    cleanup_locations.extend([older, newest])

    resp = await admin_client.get(
        "/api/v1/admin/locations",
        params={"sort": "latest_added", "sort_direction": "desc"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert _ids(data)[:2] == [newest, older]


async def test_latest_verified_sorts_nulls_last(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    pending = await _insert_location(name="Pending", last_verified_at=None)
    verified = await _insert_location(
        name="Verified",
        last_verified_at="2024-03-05T00:00:00Z",
        confidence=0.95,
    )
    cleanup_locations.extend([pending, verified])

    resp = await admin_client.get(
        "/api/v1/admin/locations",
        params={"sort": "latest_verified", "sort_direction": "desc"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert _ids(data)[:2] == [verified, pending]


async def test_category_filter_limits_rows(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    bakery = await _insert_location(name="Bakery", category="bakery")
    mosque = await _insert_location(name="Mosque", category="mosque")
    cleanup_locations.extend([bakery, mosque])

    resp = await admin_client.get(
        "/api/v1/admin/locations",
        params={"category": "mosque"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert _ids(data) == [mosque]


async def test_confidence_range_filters_and_normalizes(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    low = await _insert_location(name="Low", confidence=0.2)
    mid = await _insert_location(name="Mid", confidence=0.6)
    high = await _insert_location(name="High", confidence=0.95)
    null_conf = await _insert_location(name="Unknown", confidence=None)
    cleanup_locations.extend([low, mid, high, null_conf])

    resp = await admin_client.get(
        "/api/v1/admin/locations",
        params={"confidence_min": 0.9, "confidence_max": 0.5},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Inputs are swapped internally; expect rows between 0.5 and 0.9 inclusive.
    ids = _ids(data)
    assert high not in ids
    assert low not in ids
    assert mid in ids
    assert null_conf not in ids


async def test_location_categories_endpoint_returns_sorted_unique(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    one = await _insert_location(name="Cafe", category="cafe")
    two = await _insert_location(name="Bakery", category="bakery")
    three = await _insert_location(name="Bakery 2", category="bakery")
    cleanup_locations.extend([one, two, three])

    resp = await admin_client.get("/api/v1/admin/location-categories")
    assert resp.status_code == 200
    data = resp.json()
    assert data["categories"] == ["bakery", "cafe"]

