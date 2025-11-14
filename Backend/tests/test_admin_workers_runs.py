from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.main import app
from services.db_service import execute, fetchrow
from services.worker_runs_service import start_worker_run, finish_worker_run

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def cleanup_worker_runs() -> List[UUID]:
    """Cleanup worker runs created during tests."""
    created: List[UUID] = []
    yield created
    if created:
        await execute(
            "DELETE FROM worker_runs WHERE id = ANY($1::uuid[])",
            created,
        )


@pytest_asyncio.fixture
async def admin_client(cleanup_worker_runs: List[UUID]):  # noqa: D401
    """HTTP client with admin auth override applied."""
    from services.db_service import init_db_pool
    await init_db_pool()

    async def _override() -> AdminUser:
        return AdminUser(email="admin@test.local")

    app.dependency_overrides[verify_admin_user] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(verify_admin_user, None)


async def _create_test_run(
    bot: str = "discovery_bot",
    city: str | None = "rotterdam",
    category: str | None = "restaurant",
    status: str = "finished",
    counters: dict | None = None,
) -> UUID:
    """Helper to create a test worker run."""
    run_id = await start_worker_run(bot=bot, city=city, category=category)
    if status in ("finished", "failed"):
        await finish_worker_run(
            run_id=run_id,
            status=status,
            progress=100,
            counters=counters or {"processed": 10},
            error_message=None if status == "finished" else "Test error",
        )
    return run_id


async def test_list_worker_runs_basic(admin_client: AsyncClient, cleanup_worker_runs: List[UUID]) -> None:
    """Test basic listing of worker runs."""
    run_id = await _create_test_run()
    cleanup_worker_runs.append(run_id)

    resp = await admin_client.get("/api/v1/admin/workers/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 1


async def test_list_worker_runs_pagination(admin_client: AsyncClient, cleanup_worker_runs: List[UUID]) -> None:
    """Test pagination with limit and offset."""
    # Create multiple runs
    run1 = await _create_test_run(bot="discovery_bot")
    run2 = await _create_test_run(bot="verify_locations_bot")
    run3 = await _create_test_run(bot="classify_bot")
    cleanup_worker_runs.extend([run1, run2, run3])

    # Test first page
    resp = await admin_client.get("/api/v1/admin/workers/runs", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 3
    assert data["limit"] == 2
    assert data["offset"] == 0

    # Test second page
    resp2 = await admin_client.get("/api/v1/admin/workers/runs", params={"limit": 2, "offset": 2})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) >= 1
    assert data2["total"] == data["total"]


async def test_list_worker_runs_filter_by_bot(admin_client: AsyncClient, cleanup_worker_runs: List[UUID]) -> None:
    """Test filtering by bot name."""
    run1 = await _create_test_run(bot="discovery_bot")
    run2 = await _create_test_run(bot="verify_locations_bot")
    cleanup_worker_runs.extend([run1, run2])

    resp = await admin_client.get("/api/v1/admin/workers/runs", params={"bot": "discovery_bot"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["bot"] == "discovery_bot" for item in data["items"])


async def test_list_worker_runs_filter_by_status(admin_client: AsyncClient, cleanup_worker_runs: List[UUID]) -> None:
    """Test filtering by status."""
    run1 = await _create_test_run(status="finished")
    run2 = await _create_test_run(status="failed")
    cleanup_worker_runs.extend([run1, run2])

    resp = await admin_client.get("/api/v1/admin/workers/runs", params={"status": "finished"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["status"] == "finished" for item in data["items"])


async def test_list_worker_runs_filter_by_since(admin_client: AsyncClient, cleanup_worker_runs: List[UUID]) -> None:
    """Test filtering by since timestamp."""
    from datetime import timedelta
    
    # Create a run now
    run_id = await _create_test_run()
    cleanup_worker_runs.append(run_id)

    # Use a timestamp from 1 hour ago
    since_dt = datetime.now(timezone.utc) - timedelta(hours=1)
    since_iso = since_dt.isoformat()

    resp = await admin_client.get("/api/v1/admin/workers/runs", params={"since": since_iso})
    assert resp.status_code == 200
    data = resp.json()
    # Should include our run (created after the since timestamp)
    run_ids = [UUID(item["id"]) for item in data["items"]]
    assert run_id in run_ids


async def test_get_worker_run_detail_success(admin_client: AsyncClient, cleanup_worker_runs: List[UUID]) -> None:
    """Test getting a single worker run by ID."""
    counters = {"processed": 42, "errors": 2}
    run_id = await _create_test_run(counters=counters)
    cleanup_worker_runs.append(run_id)

    resp = await admin_client.get(f"/api/v1/admin/workers/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(run_id)
    assert data["bot"] == "discovery_bot"
    assert data["status"] == "finished"
    assert data["counters"] == counters
    assert "duration_seconds" in data
    assert "parameters" in data


async def test_get_worker_run_detail_not_found(admin_client: AsyncClient) -> None:
    """Test getting a non-existent worker run returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await admin_client.get(f"/api/v1/admin/workers/runs/{fake_id}")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_get_worker_run_detail_includes_parameters(admin_client: AsyncClient, cleanup_worker_runs: List[UUID]) -> None:
    """Test that detail endpoint includes derived parameters."""
    counters = {"limit": 100, "min_confidence": 0.8, "chunks": 4}
    run_id = await _create_test_run(city="rotterdam", category="restaurant", counters=counters)
    cleanup_worker_runs.append(run_id)

    resp = await admin_client.get(f"/api/v1/admin/workers/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["parameters"] is not None
    assert data["parameters"]["city"] == "rotterdam"
    assert data["parameters"]["category"] == "restaurant"
    assert data["parameters"]["limit"] == 100
    assert data["parameters"]["min_confidence"] == 0.8


async def test_list_worker_runs_invalid_since_format(admin_client: AsyncClient) -> None:
    """Test that invalid since timestamp format returns 400."""
    resp = await admin_client.get("/api/v1/admin/workers/runs", params={"since": "not-a-timestamp"})
    assert resp.status_code == 400
    assert "timestamp" in resp.json()["detail"].lower()


async def test_worker_run_duration_computation(admin_client: AsyncClient, cleanup_worker_runs: List[UUID]) -> None:
    """Test that duration is computed correctly from started_at and finished_at."""
    run_id = await _create_test_run()
    cleanup_worker_runs.append(run_id)

    resp = await admin_client.get(f"/api/v1/admin/workers/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    
    if data["started_at"] and data["finished_at"]:
        assert data["duration_seconds"] is not None
        assert data["duration_seconds"] >= 0

