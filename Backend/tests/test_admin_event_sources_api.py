from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.main import app
from app.models.event_sources import EventSource

pytestmark = pytest.mark.asyncio(loop_scope="module")


def _sample_event_source(**overrides: Any) -> EventSource:
    base = {
        "id": 1,
        "key": "rotterdam_culture",
        "name": "Rotterdam Cultuur",
        "base_url": "https://www.rotterdam.nl",
        "list_url": "https://www.rotterdam.nl/events",
        "selectors": {"list": ".card", "title": ".card-title"},
        "interval_minutes": 120,
        "status": "active",
        "last_run_at": datetime.now(timezone.utc),
        "last_success_at": datetime.now(timezone.utc),
        "last_error_at": None,
        "last_error": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return EventSource(**base)


@pytest_asyncio.fixture
async def admin_client() -> AsyncClient:
    async def _override() -> AdminUser:
        return AdminUser(email="admin@test.local")

    app.dependency_overrides[verify_admin_user] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(verify_admin_user, None)


async def test_list_event_sources(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: Dict[str, Any] = {}

    async def fake_list(status: str | None = None) -> List[EventSource]:
        recorded["status"] = status
        return [_sample_event_source()]

    monkeypatch.setattr(
        "api.routers.admin_event_sources.svc_list_event_sources",
        fake_list,
    )

    resp = await admin_client.get("/api/v1/admin/event-sources")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"][0]["key"] == "rotterdam_culture"
    assert recorded["status"] is None


async def test_create_event_source(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "key": "denhaag_events",
        "name": "Den Haag Events",
        "base_url": "https://denhaag.com",
        "list_url": "https://denhaag.com/events",
        "selectors": {"list": ".item", "title": ".item-title"},
        "interval_minutes": 90,
        "status": "active",
    }

    async def fake_create(body):
        assert body.key == payload["key"]
        return _sample_event_source(id=2, **payload)

    monkeypatch.setattr("api.routers.admin_event_sources.create_event_source", fake_create)

    resp = await admin_client.post("/api/v1/admin/event-sources", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 2
    assert data["key"] == "denhaag_events"


async def test_update_event_source(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    updated = _sample_event_source(name="Rotterdam Events Updated")

    async def fake_update(source_id: int, payload):
        assert source_id == 1
        assert payload.name == "Rotterdam Events Updated"
        return updated

    monkeypatch.setattr("api.routers.admin_event_sources.svc_update_event_source", fake_update)

    resp = await admin_client.put(
        "/api/v1/admin/event-sources/1",
        json={"name": "Rotterdam Events Updated", "selectors": {"list": ".card", "title": ".title"}},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Rotterdam Events Updated"


async def test_create_event_source_invalid_selectors(admin_client: AsyncClient) -> None:
    payload = {
        "key": "invalid_selectors",
        "name": "Invalid Selectors",
        "base_url": "https://example.com",
        "selectors": {"format": "xml"},
        "interval_minutes": 60,
    }
    resp = await admin_client.post("/api/v1/admin/event-sources", json=payload)
    assert resp.status_code == 422

async def test_toggle_event_source_status(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    existing = _sample_event_source(status="active")
    toggled = _sample_event_source(status="disabled")

    async def fake_get(source_id: int):
        assert source_id == 1
        return existing

    async def fake_set(source_id: int, status: str):
        assert source_id == 1
        assert status == "disabled"
        return toggled

    monkeypatch.setattr("api.routers.admin_event_sources.get_event_source", fake_get)
    monkeypatch.setattr("api.routers.admin_event_sources.set_event_source_status", fake_set)

    resp = await admin_client.post("/api/v1/admin/event-sources/1/toggle-status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


