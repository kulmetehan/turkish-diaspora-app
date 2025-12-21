from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.main import app
from services.db_service import execute, fetch, fetchrow, init_db_pool
from services.event_candidate_service import EventCandidateRecord

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture
async def admin_client() -> AsyncClient:
    async def _override() -> AdminUser:
        return AdminUser(email="admin@test.local")

    app.dependency_overrides[verify_admin_user] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(verify_admin_user, None)


async def test_list_event_raw(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    row = {
        "id": 1,
        "event_source_id": 5,
        "source_key": "rotterdam_culture",
        "title": "Event Title",
        "description": "Desc",
        "location_text": "Rotterdam",
        "venue": "Community Hall",
        "event_url": "https://example.com",
        "start_at": datetime.now(timezone.utc),
        "end_at": None,
        "processing_state": "enriched",
        "language_code": "nl",
        "category_key": "community",
        "summary_ai": "Summary",
        "confidence_score": 0.9,
        "enriched_at": datetime.now(timezone.utc),
        "enriched_by": "event_enrichment_bot",
        "processing_errors": None,
        "fetched_at": datetime.now(timezone.utc),
    }

    async def fake_fetch(sql: str, *params):
        return [row]

    async def fake_fetchrow(sql: str, *params):
        return {"total": 1}

    monkeypatch.setattr("api.routers.admin_events.fetch", fake_fetch)
    monkeypatch.setattr("api.routers.admin_events.fetchrow", fake_fetchrow)

    resp = await admin_client.get("/api/v1/admin/events/raw?processing_state=enriched&limit=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["category_key"] == "community"
    assert data["items"][0]["processing_state"] == "enriched"


async def test_list_event_raw_db_error(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(*args, **kwargs):
        raise asyncpg.InterfaceError("boom")

    monkeypatch.setattr("api.routers.admin_events.fetch", fake_fetch)
    monkeypatch.setattr("api.routers.admin_events.fetchrow", fake_fetch)

    resp = await admin_client.get("/api/v1/admin/events/raw")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "event data unavailable"


@pytest.mark.asyncio
async def test_list_event_candidates(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    record = EventCandidateRecord(
        id=1,
        event_source_id=5,
        event_raw_id=9,
        title="Community Meetup",
        description="Desc",
        duplicate_of_id=None,
        duplicate_score=None,
        start_time_utc=now,
        end_time_utc=None,
        location_text="Rotterdam",
        url="https://example.com",
        source_key="rotterdam_culture",
        ingest_hash="a" * 40,
        state="candidate",
        created_at=now,
        updated_at=now,
        source_name="Rotterdam Culture",
        has_duplicates=False,
    )

    async def fake_list_event_candidates(**kwargs):
        fake_list_event_candidates.captured = kwargs  # type: ignore[attr-defined]
        return [record], 1

    monkeypatch.setattr("api.routers.admin_events.list_event_candidates", fake_list_event_candidates)

    resp = await admin_client.get(
        "/api/v1/admin/events/candidates?state=candidate&source_key=rotterdam_culture&search=meet",
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Community Meetup"
    assert fake_list_event_candidates.captured["state"] == "candidate"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_list_event_candidates_invalid_state(admin_client: AsyncClient) -> None:
    resp = await admin_client.get("/api/v1/admin/events/candidates?state=unknown")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_event_candidates_duplicates_filter(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    record = EventCandidateRecord(
        id=2,
        event_source_id=5,
        event_raw_id=9,
        title="Community Meetup",
        description="Desc",
        duplicate_of_id=None,
        duplicate_score=None,
        start_time_utc=now,
        end_time_utc=None,
        location_text="Rotterdam",
        url="https://example.com",
        source_key="rotterdam_culture",
        ingest_hash="a" * 40,
        state="candidate",
        created_at=now,
        updated_at=now,
        source_name="Rotterdam Culture",
        has_duplicates=True,
    )

    async def fake_list_event_candidates(**kwargs):
        fake_list_event_candidates.captured = kwargs  # type: ignore[attr-defined]
        return [record], 1

    monkeypatch.setattr("api.routers.admin_events.list_event_candidates", fake_list_event_candidates)

    resp = await admin_client.get("/api/v1/admin/events/candidates?duplicates_only=true")
    assert resp.status_code == 200
    assert fake_list_event_candidates.captured["duplicates_only"] is True  # type: ignore[attr-defined]

    resp = await admin_client.get("/api/v1/admin/events/candidates?canonical_only=true")
    assert resp.status_code == 200
    assert fake_list_event_candidates.captured["canonical_only"] is True  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_verify_event_candidate(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)

    async def fake_update_event_candidate_state(**kwargs):
        assert kwargs["candidate_id"] == 123
        assert kwargs["new_state"] == "verified"
        return EventCandidateRecord(
            id=123,
            event_source_id=7,
            event_raw_id=1,
            title="Concert",
            description=None,
            duplicate_of_id=None,
            duplicate_score=None,
            start_time_utc=now,
            end_time_utc=None,
            location_text=None,
            url=None,
            source_key="foo",
            ingest_hash="b" * 40,
            state="verified",
            created_at=now,
            updated_at=now,
            source_name=None,
            has_duplicates=False,
        )

    monkeypatch.setattr(
        "api.routers.admin_events.update_event_candidate_state",
        fake_update_event_candidate_state,
    )

    resp = await admin_client.post("/api/v1/admin/events/candidates/123/verify")
    assert resp.status_code == 200
    assert resp.json()["state"] == "verified"


@pytest.mark.asyncio
async def test_event_candidate_action_not_found(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_update_event_candidate_state(**kwargs):
        raise LookupError("missing")

    monkeypatch.setattr(
        "api.routers.admin_events.update_event_candidate_state",
        fake_update_event_candidate_state,
    )

    resp = await admin_client.post("/api/v1/admin/events/candidates/999/reject")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_event_candidate_duplicates(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    canonical = EventCandidateRecord(
        id=10,
        event_source_id=5,
        event_raw_id=1,
        title="Canonical Event",
        description=None,
        duplicate_of_id=None,
        duplicate_score=None,
        start_time_utc=now,
        end_time_utc=None,
        location_text=None,
        url=None,
        source_key="canon",
        ingest_hash="c" * 40,
        state="verified",
        created_at=now,
        updated_at=now,
        source_name="Source",
        has_duplicates=True,
    )
    duplicate = EventCandidateRecord(
        id=11,
        event_source_id=6,
        event_raw_id=2,
        title="Duplicate Event",
        description=None,
        duplicate_of_id=10,
        duplicate_score=0.9,
        start_time_utc=now,
        end_time_utc=None,
        location_text=None,
        url=None,
        source_key="dup",
        ingest_hash="d" * 40,
        state="candidate",
        created_at=now,
        updated_at=now,
        source_name="Other Source",
        has_duplicates=False,
    )

    async def fake_list_candidate_duplicates(candidate_id: int):
        assert candidate_id == 10
        return canonical, [duplicate]

    monkeypatch.setattr(
        "api.routers.admin_events.list_candidate_duplicates",
        fake_list_candidate_duplicates,
    )

    resp = await admin_client.get("/api/v1/admin/events/candidates/10/duplicates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["canonical"]["id"] == 10
    assert data["duplicates"][0]["id"] == 11


@pytest.mark.asyncio
async def test_event_metrics_endpoint(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the /admin/events/metrics endpoint returns correct structure."""
    
    async def fake_fetchrow_total(sql: str, *params):
        if "COUNT(*)::int AS count FROM events_candidate" in sql:
            return {"count": 100}
        elif "COUNT(*)::int AS count FROM events_public" in sql:
            return {"count": 25}
        elif "published_not_visible" in sql.lower():
            return {"count": 5}
        elif "duplicate_of_id IS NOT NULL" in sql:
            return {"count": 10}
        return {"count": 0}
    
    async def fake_fetch_state_counts(sql: str, *params):
        if "SELECT state, COUNT(*)::int AS count" in sql:
            return [
                {"state": "candidate", "count": 50},
                {"state": "verified", "count": 20},
                {"state": "published", "count": 30},
                {"state": "rejected", "count": 0},
            ]
        return []
    
    monkeypatch.setattr("api.routers.admin_events.fetchrow", fake_fetchrow_total)
    monkeypatch.setattr("api.routers.admin_events.fetch", fake_fetch_state_counts)
    
    resp = await admin_client.get("/api/v1/admin/events/metrics")
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["total_candidates"] == 100
    assert data["by_state"]["candidate"] == 50
    assert data["by_state"]["verified"] == 20
    assert data["by_state"]["published"] == 30
    assert data["by_state"]["rejected"] == 0
    assert data["visible_in_frontend"] == 25
    assert data["published_not_visible"] == 5
    assert data["duplicate_count"] == 10


@pytest.mark.asyncio
async def test_event_metrics_endpoint_db_error(admin_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that metrics endpoint handles database errors gracefully."""
    
    async def fake_fetchrow(*args, **kwargs):
        raise asyncpg.InterfaceError("Database error")
    
    monkeypatch.setattr("api.routers.admin_events.fetchrow", fake_fetchrow)
    monkeypatch.setattr("api.routers.admin_events.fetch", fake_fetchrow)
    
    resp = await admin_client.get("/api/v1/admin/events/metrics")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "event metrics unavailable"

