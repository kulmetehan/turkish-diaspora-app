from __future__ import annotations

from typing import List

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.main import app
from services.db_service import execute, fetchrow

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def cleanup_locations() -> List[int]:
    created: List[int] = []
    yield created
    if created:
        await execute(
            "DELETE FROM locations WHERE id = ANY($1::bigint[])",
            created,
        )


@pytest_asyncio.fixture
async def admin_client(cleanup_locations: List[int]):
    async def _override() -> AdminUser:
        return AdminUser(email="admin@test.local")

    app.dependency_overrides[verify_admin_user] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(verify_admin_user, None)


async def test_create_admin_location_success(admin_client: AsyncClient, cleanup_locations: List[int]) -> None:
    payload = {
        "name": "Manual Bakery",
        "address": "Straat 1, Rotterdam",
        "lat": 51.92,
        "lng": 4.48,
        "category": "bakery",
        "notes": "Added manually",
        "evidence_urls": ["https://example.com/photo"],
    }

    resp = await admin_client.post("/api/v1/admin/locations", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    cleanup_locations.append(data["id"])

    assert data["name"] == payload["name"]
    assert data["state"] == "VERIFIED"
    assert data["confidence_score"] >= 0.9

    row = await fetchrow(
        """
        SELECT source, place_id, state, confidence_score, lat, lng, category
        FROM locations WHERE id = $1
        """,
        data["id"],
    )
    assert row is not None
    assert row["source"] == "ADMIN_MANUAL"
    assert str(row["place_id"]).startswith("admin_manual/")
    assert row["state"] == "VERIFIED"
    assert float(row["confidence_score"]) >= 0.9
    assert float(row["lat"]) == pytest.approx(payload["lat"])
    assert float(row["lng"]) == pytest.approx(payload["lng"])
    assert row["category"] == payload["category"]


async def test_create_admin_location_invalid_category(admin_client: AsyncClient) -> None:
    payload = {
        "name": "Invalid Category",
        "address": "Straat 1",
        "lat": 51.0,
        "lng": 4.0,
        "category": "not-a-category",
    }
    resp = await admin_client.post("/api/v1/admin/locations", json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid category"


async def test_create_admin_location_invalid_lat(admin_client: AsyncClient) -> None:
    payload = {
        "name": "Bad Lat",
        "address": "Straat 1",
        "lat": 120.0,
        "lng": 4.0,
        "category": "bakery",
    }
    resp = await admin_client.post("/api/v1/admin/locations", json=payload)
    # Pydantic validation should trigger 422 for invalid lat range
    assert resp.status_code == 422

