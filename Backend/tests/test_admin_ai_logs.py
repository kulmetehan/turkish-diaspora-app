from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Tuple

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture
async def admin_client() -> AsyncClient:
    async def _override() -> AdminUser:
        return AdminUser(email="admin@test.local")

    app.dependency_overrides[verify_admin_user] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(verify_admin_user, None)


@pytest_asyncio.fixture
async def anon_client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


async def test_get_ai_logs_news_only_includes_metadata(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: Dict[str, Any] = {}

    async def fake_fetch(query: str, *args: Any, **kwargs: Any):
        recorded["query"] = query
        recorded["params"] = args
        return [
            {
                "id": 1,
                "location_id": None,
                "news_id": 42,
                "action_type": "news.classify",
                "model_used": "gpt-4o-mini",
                "validated_output": {"category": "news"},
                "is_success": True,
                "error_message": None,
                "created_at": datetime.now(timezone.utc),
                "news_source_key": "anp",
                "news_source_name": "ANP",
            }
        ]

    async def fake_fetchrow(query: str, *args: Any, **kwargs: Any):
        return {"total": 1}

    monkeypatch.setattr("api.routers.admin_ai_logs.fetch", fake_fetch)
    monkeypatch.setattr("api.routers.admin_ai_logs.fetchrow", fake_fetchrow)

    resp = await admin_client.get("/api/v1/admin/ai/logs", params={"news_only": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["news_source_key"] == "anp"
    assert "LEFT JOIN raw_ingested_news" in recorded["query"]
    assert "ai.news_id IS NOT NULL" in recorded["query"]
    assert recorded["params"][-2:] == (20, 0)


async def test_get_ai_logs_filter_by_news_and_source(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: Dict[str, Tuple[Any, ...]] = {}

    async def fake_fetch(query: str, *args: Any, **kwargs: Any):
        recorded["query"] = query
        recorded["params"] = args
        return [
            {
                "id": 11,
                "location_id": None,
                "news_id": 99,
                "action_type": "news.classify",
                "model_used": "gpt",
                "validated_output": {"category": "news"},
                "is_success": True,
                "error_message": None,
                "created_at": datetime.now(timezone.utc),
                "news_source_key": "aa",
                "news_source_name": "Anadolu Ajansı",
            }
        ]

    async def fake_fetchrow(query: str, *args: Any, **kwargs: Any):
        recorded["count_query"] = query
        recorded["count_params"] = args
        return {"total": 1}

    monkeypatch.setattr("api.routers.admin_ai_logs.fetch", fake_fetch)
    monkeypatch.setattr("api.routers.admin_ai_logs.fetchrow", fake_fetchrow)

    resp = await admin_client.get("/api/v1/admin/ai/logs", params={"source_key": "aa"})
    assert resp.status_code == 200
    assert "rin.source_key = $" in recorded["query"]
    assert "LEFT JOIN raw_ingested_news" in recorded["query"]

    resp_id = await admin_client.get("/api/v1/admin/ai/logs", params={"news_id": 99})
    assert resp_id.status_code == 200
    assert "ai.news_id = $" in recorded["query"]


async def test_get_ai_logs_location_only_skips_news_join(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: Dict[str, Any] = {}

    async def fake_fetch(query: str, *args: Any, **kwargs: Any):
        recorded["query"] = query
        return [
            {
                "id": 7,
                "location_id": 123,
                "news_id": None,
                "action_type": "verify_locations.classified",
                "model_used": "gpt",
                "validated_output": {"category": "bakery"},
                "is_success": True,
                "error_message": None,
                "created_at": datetime.now(timezone.utc),
            }
        ]

    async def fake_fetchrow(query: str, *args: Any, **kwargs: Any):
        return {"total": 1}

    monkeypatch.setattr("api.routers.admin_ai_logs.fetch", fake_fetch)
    monkeypatch.setattr("api.routers.admin_ai_logs.fetchrow", fake_fetchrow)

    resp = await admin_client.get("/api/v1/admin/ai/logs", params={"location_id": 123})
    assert resp.status_code == 200
    assert "raw_ingested_news" not in recorded["query"]


async def test_get_ai_logs_requires_admin(anon_client: AsyncClient) -> None:
    resp = await anon_client.get("/api/v1/admin/ai/logs", params={"news_only": True})
    assert resp.status_code == 401


async def test_get_ai_log_detail_news_entry(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetchrow(query: str, *args: Any, **kwargs: Any):
        return {
            "id": 55,
            "location_id": None,
            "news_id": 900,
            "action_type": "news.classify",
            "model_used": "gpt",
            "prompt": {"system": "news"},
            "raw_response": {"raw": "response"},
            "validated_output": {"category": "news"},
            "is_success": True,
            "error_message": None,
            "created_at": datetime.now(timezone.utc),
            "news_source_key": "aa",
            "news_source_name": "Anadolu",
            "news_title": "Nieuws detail",
        }

    monkeypatch.setattr("api.routers.admin_ai_logs.fetchrow", fake_fetchrow)

    resp = await admin_client.get("/api/v1/admin/ai/logs/55")
    assert resp.status_code == 200
    data = resp.json()
    assert data["news_id"] == 900
    assert data["prompt"]["system"] == "news"
    assert data["news_source_key"] == "aa"


async def test_get_ai_log_detail_parses_string_payloads(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetchrow(query: str, *args: Any, **kwargs: Any):
        return {
            "id": 77,
            "location_id": 1,
            "news_id": None,
            "action_type": "verify_locations.classified",
            "model_used": "gpt",
            "prompt": '{"system":"loc"}',
            "raw_response": '{"raw":"txt"}',
            "validated_output": '{"category":"bakery"}',
            "is_success": True,
            "error_message": None,
            "created_at": datetime.now(timezone.utc),
            "news_source_key": None,
            "news_source_name": None,
            "news_title": None,
        }

    monkeypatch.setattr("api.routers.admin_ai_logs.fetchrow", fake_fetchrow)

    resp = await admin_client.get("/api/v1/admin/ai/logs/77")
    assert resp.status_code == 200
    data = resp.json()
    assert data["prompt"]["system"] == "loc"
    assert data["validated_output"]["category"] == "bakery"


async def test_get_ai_log_detail_not_found(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetchrow(query: str, *args: Any, **kwargs: Any):
        return None

    monkeypatch.setattr("api.routers.admin_ai_logs.fetchrow", fake_fetchrow)

    resp = await admin_client.get("/api/v1/admin/ai/logs/999")
    assert resp.status_code == 404


async def test_get_ai_log_detail_requires_admin(anon_client: AsyncClient) -> None:
    resp = await anon_client.get("/api/v1/admin/ai/logs/10")
    assert resp.status_code == 401


