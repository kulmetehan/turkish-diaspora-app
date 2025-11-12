from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest
from httpx import AsyncClient

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.main import app
from services import db_service
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
        "Teststraat 1",
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
    if not created:
        return
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


async def test_bulk_verify_promotes_to_verified(admin_client: AsyncClient, cleanup_locations: List[int]) -> None:
    location_id = await _insert_location(
        name="Verify Me",
        state="CANDIDATE",
        confidence=0.42,
        category="bakery",
    )
    cleanup_locations.append(location_id)

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={"ids": [location_id], "action": {"type": "verify"}},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["updated"] == [location_id]
    assert payload["errors"] == []

    refreshed = await _fetch_location(location_id)
    assert refreshed is not None
    assert refreshed["state"] == "VERIFIED"
    assert refreshed["last_verified_at"] is not None
    assert float(refreshed["confidence_score"]) >= 0.9


async def test_bulk_retire_sets_state_and_stamp(admin_client: AsyncClient, cleanup_locations: List[int]) -> None:
    location_id = await _insert_location(
        name="Retire Me",
        state="PENDING_VERIFICATION",
        confidence=0.65,
        category="restaurant",
    )
    cleanup_locations.append(location_id)

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={"ids": [location_id], "action": {"type": "retire"}},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["updated"] == [location_id]
    assert payload["errors"] == []

    refreshed = await _fetch_location(location_id)
    assert refreshed is not None
    assert refreshed["state"] == "RETIRED"
    assert refreshed["last_verified_at"] is not None
    assert refreshed["is_retired"] is True


async def test_bulk_adjust_confidence_updates_score(admin_client: AsyncClient, cleanup_locations: List[int]) -> None:
    location_id = await _insert_location(
        name="Adjust Me",
        state="VERIFIED",
        confidence=0.87,
        category="butcher",
    )
    cleanup_locations.append(location_id)

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={
            "ids": [location_id],
            "action": {"type": "adjust_confidence", "value": 0.42},
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["updated"] == [location_id]
    assert payload["errors"] == []

    refreshed = await _fetch_location(location_id)
    assert refreshed is not None
    assert refreshed["state"] == "VERIFIED"
    assert refreshed["last_verified_at"] is not None
    assert pytest.approx(float(refreshed["confidence_score"]), rel=1e-3) == 0.42


async def test_bulk_verify_retired_without_force_stays_retired(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    location_id = await _insert_location(
        name="Retired Bakery",
        state="RETIRED",
        confidence=0.92,
        category="bakery",
        is_retired=True,
    )
    cleanup_locations.append(location_id)

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={"ids": [location_id], "action": {"type": "verify"}},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["updated"] == [location_id]

    refreshed = await _fetch_location(location_id)
    assert refreshed is not None
    assert refreshed["state"] == "RETIRED"
    assert refreshed["is_retired"] is True


async def test_bulk_verify_retired_with_force_promotes(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    location_id = await _insert_location(
        name="Retired With Force",
        state="RETIRED",
        confidence=0.82,
        category="supermarket",
        is_retired=True,
    )
    cleanup_locations.append(location_id)

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={"ids": [location_id], "action": {"type": "verify", "force": True}},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["updated"] == [location_id]
    refreshed = await _fetch_location(location_id)
    assert refreshed is not None
    assert refreshed["state"] == "VERIFIED"
    assert refreshed["is_retired"] is False
    assert refreshed["last_verified_at"] is not None


async def test_bulk_verify_retired_with_clear_retired_promotes(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
) -> None:
    location_id = await _insert_location(
        name="Retired With Clear Flag",
        state="RETIRED",
        confidence=0.88,
        category="restaurant",
        is_retired=True,
    )
    cleanup_locations.append(location_id)

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={"ids": [location_id], "action": {"type": "verify", "clear_retired": True}},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["updated"] == [location_id]
    refreshed = await _fetch_location(location_id)
    assert refreshed is not None
    assert refreshed["state"] == "VERIFIED"
    assert refreshed["is_retired"] is False
    assert refreshed["last_verified_at"] is not None


async def test_bulk_update_collects_partial_failures(admin_client: AsyncClient, cleanup_locations: List[int]) -> None:
    location_id = await _insert_location(
        name="Partial Success",
        state="CANDIDATE",
        confidence=0.33,
        category="supermarket",
    )
    cleanup_locations.append(location_id)
    missing_id = max(location_id + 99999, 1)

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={
            "ids": [location_id, missing_id],
            "action": {"type": "retire"},
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is False
    assert location_id in payload["updated"]
    assert any(error["id"] == missing_id for error in payload["errors"])

    refreshed = await _fetch_location(location_id)
    assert refreshed is not None
    assert refreshed["state"] == "RETIRED"


async def test_bulk_update_requires_admin_auth() -> None:
    app.dependency_overrides.pop(verify_admin_user, None)

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        resp = await client.patch(
            "/api/v1/admin/locations/bulk-update",
            json={"ids": [123], "action": {"type": "verify"}},
        )
    assert resp.status_code in (401, 403)


async def test_bulk_update_returns_504_when_all_time_out(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location_id = await _insert_location(
        name="Timeout All",
        state="CANDIDATE",
        confidence=0.4,
        category="bakery",
    )
    cleanup_locations.append(location_id)

    async def _timeout_fetchrow(*args: Any, **kwargs: Any) -> Any:
        raise asyncio.TimeoutError("forced timeout")

    original_fetchrow = db_service.fetchrow
    monkeypatch.setattr(db_service, "fetchrow", _timeout_fetchrow)

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={"ids": [location_id], "action": {"type": "retire"}},
    )

    # Restore original to avoid affecting other tests
    monkeypatch.setattr(db_service, "fetchrow", original_fetchrow)

    assert resp.status_code == 504
    payload = resp.json()
    assert payload["detail"]["updated"] == []
    assert payload["detail"]["errors"][0]["id"] == location_id
    assert "timeout" in payload["detail"]["errors"][0]["detail"]


async def test_bulk_update_partial_timeout_continues_processing(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    success_id = await _insert_location(
        name="Success Item",
        state="CANDIDATE",
        confidence=0.5,
        category="restaurant",
    )
    timeout_id = await _insert_location(
        name="Timeout Item",
        state="CANDIDATE",
        confidence=0.5,
        category="restaurant",
    )
    cleanup_locations.extend([success_id, timeout_id])

    original_execute_with_conn = db_service.execute_with_conn

    async def _conditional_execute_with_conn(
        conn: Any,
        query: str,
        *args: Any,
        timeout: float | None = None,
    ) -> Any:
        target_id = int(args[-1])
        if target_id == timeout_id:
            raise asyncio.TimeoutError("forced timeout")
        return await original_execute_with_conn(conn, query, *args, timeout=timeout)

    monkeypatch.setattr(
        db_service,
        "execute_with_conn",
        _conditional_execute_with_conn,
    )

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={"ids": [success_id, timeout_id], "action": {"type": "retire"}},
    )

    # Restore original execute to avoid affecting other tests
    monkeypatch.setattr(
        db_service,
        "execute_with_conn",
        original_execute_with_conn,
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert success_id in payload["updated"]
    assert any(error["id"] == timeout_id for error in payload["errors"])
    assert payload["ok"] is False


async def test_retire_endpoint_returns_504_on_timeout(
    admin_client: AsyncClient,
    cleanup_locations: List[int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location_id = await _insert_location(
        name="Timeout Delete",
        state="VERIFIED",
        confidence=0.9,
        category="bakery",
    )
    cleanup_locations.append(location_id)

    original_execute_with_conn = db_service.execute_with_conn

    async def _timeout_execute_with_conn(
        conn: Any,
        query: str,
        *args: Any,
        timeout: float | None = None,
    ) -> Any:
        raise asyncio.TimeoutError("forced timeout")

    monkeypatch.setattr(
        db_service,
        "execute_with_conn",
        _timeout_execute_with_conn,
    )

    resp = await admin_client.delete(
        f"/api/v1/admin/locations/{location_id}",
    )

    monkeypatch.setattr(
        db_service,
        "execute_with_conn",
        original_execute_with_conn,
    )

    assert resp.status_code == 504
    payload = resp.json()
    assert payload["detail"] == "retire operation timed out"

