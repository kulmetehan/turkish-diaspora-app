from __future__ import annotations

from datetime import date, datetime, timezone
import os
from typing import Any, Dict, List, Tuple

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import dotenv

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")


def _noop_load_dotenv(*args: Any, **kwargs: Any) -> bool:
    return False


dotenv.load_dotenv = _noop_load_dotenv  # type: ignore[assignment]

from api.routers import events as events_router
from app.models.events_public import EventItem

events_test_app = FastAPI()
events_test_app.include_router(events_router.router, prefix="/api/v1")
client = TestClient(events_test_app)


@pytest.mark.asyncio
async def test_get_events_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    sample = EventItem(
        id=1,
        title="Community Meetup",
        description="Desc",
        start_time_utc=now,
        end_time_utc=None,
        city_key="rotterdam",
        category_key="community",
        location_text="Rotterdam",
        url="https://example.com/event",
        source_key="rotterdam_culture",
        summary_ai="Summary",
        updated_at=now,
    )

    async def fake_list_public_events(**kwargs: Any) -> Tuple[List[EventItem], int]:
        assert kwargs["city"] is None
        assert kwargs["categories"] is None
        assert kwargs["limit"] == 10
        assert kwargs["offset"] == 0
        return [sample], 1

    monkeypatch.setattr(events_router, "list_public_events", fake_list_public_events)

    response = await events_router.get_events(
        city=None,
        date_from=None,
        date_to=None,
        categories=None,
        limit=10,
        offset=0,
    )
    payload = response.model_dump()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == sample.title
    assert payload["items"][0]["city_key"] == "rotterdam"


@pytest.mark.asyncio
async def test_get_events_normalizes_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: Dict[str, Any] = {}

    async def fake_list_public_events(**kwargs: Any) -> Tuple[List[EventItem], int]:
        captured.update(kwargs)
        return [], 0

    monkeypatch.setattr(events_router, "list_public_events", fake_list_public_events)

    df = date(2025, 1, 1)
    dt = date(2025, 1, 3)
    await events_router.get_events(
        city="Rotterdam ",
        categories=["community,culture", "business"],
        date_from=df,
        date_to=dt,
        limit=5,
        offset=15,
    )

    assert captured["city"] == "rotterdam"
    assert captured["categories"] == ["community", "culture", "business"]
    assert captured["date_from"] == df
    assert captured["date_to"] == dt
    assert captured["limit"] == 5
    assert captured["offset"] == 15


@pytest.mark.asyncio
async def test_get_events_invalid_city(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_list_public_events(**kwargs: Any) -> Tuple[List[EventItem], int]:
        return [], 0

    monkeypatch.setattr(events_router, "list_public_events", fake_list_public_events)

    with pytest.raises(HTTPException) as exc:
        await events_router.get_events(
            city="unknownville",
            date_from=None,
            date_to=None,
            categories=None,
            limit=20,
            offset=0,
        )
    assert exc.value.status_code == 400
    assert "Unknown city" in exc.value.detail


@pytest.mark.asyncio
async def test_get_events_invalid_category(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_list_public_events(**kwargs: Any) -> Tuple[List[EventItem], int]:
        return [], 0

    monkeypatch.setattr(events_router, "list_public_events", fake_list_public_events)

    with pytest.raises(HTTPException) as exc:
        await events_router.get_events(
            city=None,
            date_from=None,
            date_to=None,
            categories=["unknown"],
            limit=20,
            offset=0,
        )
    assert exc.value.status_code == 400
    assert "Unknown category" in exc.value.detail


@pytest.mark.asyncio
async def test_get_events_invalid_date_range(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_list_public_events(**kwargs: Any) -> Tuple[List[EventItem], int]:
        return [], 0

    monkeypatch.setattr(events_router, "list_public_events", fake_list_public_events)

    with pytest.raises(HTTPException) as exc:
        await events_router.get_events(
            city=None,
            date_from=date(2025, 2, 1),
            date_to=date(2025, 1, 1),
            categories=None,
            limit=20,
            offset=0,
        )
    assert exc.value.status_code == 400
    assert "date_to" in exc.value.detail


def test_get_events_endpoint_via_http(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    sample = EventItem(
        id=42,
        title="Community Brunch",
        description="Delicious food and networking",
        start_time_utc=now,
        end_time_utc=None,
        city_key="rotterdam",
        category_key="community",
        location_text="Central Rotterdam",
        url="https://example.com/events/42",
        source_key="sample_source",
        summary_ai="Sample summary",
        updated_at=now,
    )

    async def fake_list_public_events(**kwargs: Any) -> Tuple[List[EventItem], int]:
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 0
        return [sample], 1

    monkeypatch.setattr(events_router, "list_public_events", fake_list_public_events)

    response = client.get("/api/v1/events?limit=20&offset=0")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["items"][0]["title"] == sample.title

