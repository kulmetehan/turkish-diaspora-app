from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest
from httpx import AsyncClient

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.main import app
from services.db_service import (
    APPLICATION_NAME,
    execute,
    execute_with_conn,
    fetch,
    fetchrow,
    run_in_transaction,
)


pytestmark = pytest.mark.asyncio


async def _count_idle_transactions() -> int:
    rows = await fetch(
        """
        SELECT COUNT(*) AS idle_count
        FROM pg_stat_activity
        WHERE datname = current_database()
          AND application_name = $1
          AND state = 'idle in transaction'
        """,
        APPLICATION_NAME,
    )
    return int(dict(rows[0]).get("idle_count", 0)) if rows else 0


async def _create_location(**overrides: Any) -> int:
    defaults: Dict[str, Any] = {
        "name": "Idle Monitor Test",
        "address": "Teststraat 2",
        "category": "bakery",
        "state": "VERIFIED",
        "confidence_score": 0.95,
        "last_verified_at": None,
        "is_retired": False,
    }
    defaults.update(overrides)
    row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score, last_verified_at, is_retired)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
        """,
        defaults["name"],
        defaults["address"],
        defaults["category"],
        defaults["state"],
        defaults["confidence_score"],
        defaults["last_verified_at"],
        defaults["is_retired"],
    )
    assert row is not None
    return int(row["id"])


@pytest.fixture
async def admin_client() -> AsyncClient:
    async def _override() -> AdminUser:
        return AdminUser(email="admin@test.local")

    app.dependency_overrides[verify_admin_user] = _override
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(verify_admin_user, None)


@pytest.fixture
async def cleanup_location_ids() -> List[int]:
    created: List[int] = []
    yield created
    if created:
        await execute("DELETE FROM locations WHERE id = ANY($1::bigint[])", created)


async def test_get_admin_location_does_not_leave_idle_transactions(
    admin_client: AsyncClient,
    cleanup_location_ids: List[int],
) -> None:
    location_id = await _create_location()
    cleanup_location_ids.append(location_id)

    resp = await admin_client.get(f"/api/v1/admin/locations/{location_id}")
    assert resp.status_code == 200

    # Allow connection cleanup to complete
    await asyncio.sleep(0.05)
    assert await _count_idle_transactions() == 0


async def test_run_in_transaction_rollback_closes_session(cleanup_location_ids: List[int]) -> None:
    location_id = await _create_location(state="CANDIDATE", confidence_score=0.42)
    cleanup_location_ids.append(location_id)

    async def _failing_transaction() -> None:
        async with run_in_transaction() as conn:
            await execute_with_conn(conn, "UPDATE locations SET notes = 'temp' WHERE id = $1", location_id)
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await _failing_transaction()

    await asyncio.sleep(0.05)
    assert await _count_idle_transactions() == 0


async def test_bulk_update_success_and_no_idle_transactions(
    admin_client: AsyncClient,
    cleanup_location_ids: List[int],
) -> None:
    location_id = await _create_location(state="CANDIDATE", confidence_score=0.42)
    cleanup_location_ids.append(location_id)

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={"ids": [location_id], "action": {"type": "verify"}},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["updated"] == [location_id]

    refreshed = await fetchrow(
        """
        SELECT state, confidence_score
        FROM locations
        WHERE id = $1
        """,
        location_id,
    )
    assert refreshed is not None
    assert refreshed["state"] == "VERIFIED"
    assert float(refreshed["confidence_score"]) >= 0.9

    await asyncio.sleep(0.05)
    assert await _count_idle_transactions() == 0


async def test_bulk_update_invalid_payload_returns_422(
    admin_client: AsyncClient,
    cleanup_location_ids: List[int],
) -> None:
    location_id = await _create_location()
    cleanup_location_ids.append(location_id)

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={
            "ids": [location_id],
            "action": {"type": "verify", "unexpected": True},
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]
    assert any("extra fields not permitted" in (issue.get("msg") or "") for issue in body["detail"])


async def test_bulk_update_server_error_has_cors_headers(
    admin_client: AsyncClient,
    cleanup_location_ids: List[int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location_id = await _create_location(state="CANDIDATE", confidence_score=0.42)
    cleanup_location_ids.append(location_id)

    class _FailingContext:
        async def __aenter__(self):
            raise RuntimeError("boom")

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    def _failing_run_in_transaction(*args: Any, **kwargs: Any) -> _FailingContext:
        return _FailingContext()

    monkeypatch.setattr("services.db_service.run_in_transaction", _failing_run_in_transaction)

    resp = await admin_client.patch(
        "/api/v1/admin/locations/bulk-update",
        json={"ids": [location_id], "action": {"type": "verify"}},
        headers={"Origin": "http://localhost:5173"},
    )
    assert resp.status_code == 500
    assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert resp.headers.get("Access-Control-Allow-Credentials") == "true"
    assert "Origin" in (resp.headers.get("Vary") or "")

