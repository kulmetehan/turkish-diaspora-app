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


def create_csv_content(headers: List[str], rows: List[List[str]]) -> bytes:
    """Helper to create CSV content as bytes."""
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(str(cell) for cell in row))
    return "\n".join(lines).encode("utf-8")


async def test_bulk_import_happy_path(admin_client: AsyncClient, cleanup_locations: List[int]) -> None:
    """Test successful bulk import with all valid rows."""
    csv_content = create_csv_content(
        ["name", "address", "lat", "lng", "category", "notes"],
        [
            ["Bakery A", "Street 1, Rotterdam", "51.92", "4.48", "bakery", "First bakery"],
            ["Bakery B", "Street 2, Amsterdam", "52.37", "4.90", "bakery", "Second bakery"],
            ["Restaurant C", "Street 3, Utrecht", "52.09", "5.11", "restaurant", ""],
        ],
    )

    files = {"file": ("test.csv", csv_content, "text/csv")}
    resp = await admin_client.post("/api/v1/admin/locations/bulk_import", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["rows_total"] == 3
    assert data["rows_processed"] == 3
    assert data["rows_created"] == 3
    assert data["rows_failed"] == 0
    assert len(data["errors"]) == 0

    # Verify locations were created
    for i in range(3):
        row = await fetchrow(
            "SELECT id, name, source FROM locations WHERE name LIKE $1 ORDER BY id DESC LIMIT 1",
            f"%{['Bakery A', 'Bakery B', 'Restaurant C'][i]}%",
        )
        assert row is not None
        cleanup_locations.append(row["id"])
        assert row["source"] == "ADMIN_MANUAL"


async def test_bulk_import_missing_required_columns(admin_client: AsyncClient) -> None:
    """Test that missing required columns returns 400."""
    csv_content = create_csv_content(
        ["name", "address", "lat"],  # Missing lng and category
        [["Test", "Street 1", "51.0"]],
    )

    files = {"file": ("test.csv", csv_content, "text/csv")}
    resp = await admin_client.post("/api/v1/admin/locations/bulk_import", files=files)
    assert resp.status_code == 400
    assert "Missing required columns" in resp.json()["detail"]


async def test_bulk_import_invalid_category(admin_client: AsyncClient) -> None:
    """Test that invalid category in a row causes that row to fail."""
    csv_content = create_csv_content(
        ["name", "address", "lat", "lng", "category"],
        [
            ["Valid Bakery", "Street 1", "51.0", "4.0", "bakery"],
            ["Invalid Category", "Street 2", "52.0", "5.0", "not-a-category"],
            ["Another Valid", "Street 3", "53.0", "6.0", "restaurant"],
        ],
    )

    files = {"file": ("test.csv", csv_content, "text/csv")}
    resp = await admin_client.post("/api/v1/admin/locations/bulk_import", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["rows_total"] == 3
    assert data["rows_processed"] == 3
    assert data["rows_created"] == 2
    assert data["rows_failed"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["row_number"] == 2
    assert "invalid category" in data["errors"][0]["message"].lower()


async def test_bulk_import_invalid_lat_range(admin_client: AsyncClient) -> None:
    """Test that invalid lat range causes row to fail."""
    csv_content = create_csv_content(
        ["name", "address", "lat", "lng", "category"],
        [
            ["Valid", "Street 1", "51.0", "4.0", "bakery"],
            ["Invalid Lat", "Street 2", "120.0", "5.0", "bakery"],  # lat > 90
        ],
    )

    files = {"file": ("test.csv", csv_content, "text/csv")}
    resp = await admin_client.post("/api/v1/admin/locations/bulk_import", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["rows_created"] == 1
    assert data["rows_failed"] == 1
    assert len(data["errors"]) == 1
    assert "lat must be between" in data["errors"][0]["message"].lower()


async def test_bulk_import_invalid_lng_range(admin_client: AsyncClient) -> None:
    """Test that invalid lng range causes row to fail."""
    csv_content = create_csv_content(
        ["name", "address", "lat", "lng", "category"],
        [
            ["Invalid Lng", "Street 1", "51.0", "200.0", "bakery"],  # lng > 180
        ],
    )

    files = {"file": ("test.csv", csv_content, "text/csv")}
    resp = await admin_client.post("/api/v1/admin/locations/bulk_import", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["rows_created"] == 0
    assert data["rows_failed"] == 1
    assert "lng must be between" in data["errors"][0]["message"].lower()


async def test_bulk_import_empty_csv(admin_client: AsyncClient) -> None:
    """Test that empty CSV returns 400."""
    csv_content = b""
    files = {"file": ("test.csv", csv_content, "text/csv")}
    resp = await admin_client.post("/api/v1/admin/locations/bulk_import", files=files)
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()


async def test_bulk_import_missing_field_in_row(admin_client: AsyncClient) -> None:
    """Test that missing required field in a row causes that row to fail."""
    csv_content = create_csv_content(
        ["name", "address", "lat", "lng", "category"],
        [
            ["Valid", "Street 1", "51.0", "4.0", "bakery"],
            ["Missing Address", "", "52.0", "5.0", "bakery"],  # Empty address
            ["Another Valid", "Street 3", "53.0", "6.0", "restaurant"],
        ],
    )

    files = {"file": ("test.csv", csv_content, "text/csv")}
    resp = await admin_client.post("/api/v1/admin/locations/bulk_import", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["rows_created"] == 2
    assert data["rows_failed"] == 1
    assert len(data["errors"]) == 1
    assert "missing required field" in data["errors"][0]["message"].lower() or "address" in data["errors"][0]["message"].lower()


async def test_bulk_import_with_evidence_urls(admin_client: AsyncClient, cleanup_locations: List[int]) -> None:
    """Test that evidence_urls are properly parsed from comma-separated string."""
    csv_content = create_csv_content(
        ["name", "address", "lat", "lng", "category", "evidence_urls"],
        [
            ["Test Bakery", "Street 1", "51.0", "4.0", "bakery", "https://example.com/1,https://example.com/2"],
        ],
    )

    files = {"file": ("test.csv", csv_content, "text/csv")}
    resp = await admin_client.post("/api/v1/admin/locations/bulk_import", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["rows_created"] == 1
    assert data["rows_failed"] == 0

    # Verify location was created (evidence_urls stored as array in DB)
    row = await fetchrow(
        "SELECT id, evidence_urls FROM locations WHERE name = $1",
        "Test Bakery",
    )
    assert row is not None
    cleanup_locations.append(row["id"])
    # evidence_urls should be stored as array
    assert row["evidence_urls"] is not None


async def test_bulk_import_normalized_headers(admin_client: AsyncClient, cleanup_locations: List[int]) -> None:
    """Test that headers are normalized (lowercase, whitespace trimmed)."""
    # Headers with mixed case and whitespace
    csv_content = "Name,  Address  ,Lat,LNG,Category\n"
    csv_content += "Test Bakery,Street 1,51.0,4.0,bakery"
    csv_content = csv_content.encode("utf-8")

    files = {"file": ("test.csv", csv_content, "text/csv")}
    resp = await admin_client.post("/api/v1/admin/locations/bulk_import", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["rows_created"] == 1
    assert data["rows_failed"] == 0

    row = await fetchrow(
        "SELECT id FROM locations WHERE name = $1",
        "Test Bakery",
    )
    assert row is not None
    cleanup_locations.append(row["id"])













