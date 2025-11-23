from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.event_candidate import EventCandidateCreate
from services import event_candidate_service
from services.event_candidate_service import (
    fetch_event_candidate_by_id,
    insert_event_candidate,
)


def _create_candidate(**overrides) -> EventCandidateCreate:
    base = {
        "event_source_id": 1,
        "event_raw_id": 10,
        "title": "Sample Event",
        "description": "Desc",
        "start_time_utc": datetime(2025, 1, 1, 12, tzinfo=timezone.utc),
        "end_time_utc": datetime(2025, 1, 1, 14, tzinfo=timezone.utc),
        "location_text": "Rotterdam",
        "url": "https://example.com/event",
        "source_key": "sample_source",
        "ingest_hash": "abc123hashvalue",
        "state": "candidate",
    }
    base.update(overrides)
    return EventCandidateCreate(**base)


@pytest.mark.asyncio
async def test_insert_event_candidate_returns_id(monkeypatch):
    captured = {}

    async def fake_fetchrow(query, *args):
        captured["query"] = query
        captured["args"] = args
        return {"id": 42}

    monkeypatch.setattr(event_candidate_service, "fetchrow", fake_fetchrow)

    candidate = _create_candidate()
    new_id = await insert_event_candidate(candidate)

    assert new_id == 42
    assert "events_candidate" in captured["query"]


@pytest.mark.asyncio
async def test_insert_event_candidate_dedup(monkeypatch):
    async def fake_fetchrow(query, *args):
        return None

    monkeypatch.setattr(event_candidate_service, "fetchrow", fake_fetchrow)

    candidate = _create_candidate()
    new_id = await insert_event_candidate(candidate)

    assert new_id is None


@pytest.mark.asyncio
async def test_fetch_event_candidate_by_id(monkeypatch):
    fake_row = {
        "id": 99,
        "event_source_id": 1,
        "event_raw_id": 5,
        "title": "Normalized Event",
        "description": "info",
        "start_time_utc": datetime(2025, 2, 1, 10, tzinfo=timezone.utc),
        "end_time_utc": None,
        "location_text": "Den Haag",
        "url": "https://example.com/norm",
        "source_key": "source_key",
        "ingest_hash": "somehashvalue123",
        "state": "candidate",
        "created_at": datetime(2025, 2, 1, 9, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 2, 1, 9, tzinfo=timezone.utc),
    }

    async def fake_fetchrow(query, *args):
        assert "FROM events_candidate" in query
        return dict(fake_row)

    monkeypatch.setattr(event_candidate_service, "fetchrow", fake_fetchrow)

    item = await fetch_event_candidate_by_id(99)

    assert item is not None
    assert item.id == 99
    assert item.start_time_utc.tzinfo == timezone.utc
    assert item.location_text == "Den Haag"


