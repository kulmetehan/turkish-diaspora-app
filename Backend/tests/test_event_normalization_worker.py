from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.event_raw import EventRaw
from app.models.event_sources import EventSource
from app.workers import event_normalization_bot as bot
from services.event_normalization_service import EventNormalizationError


def _make_event_raw(**overrides) -> EventRaw:
    now = datetime.now(timezone.utc)
    base = {
        "id": 5,
        "event_source_id": 3,
        "title": "Morning Tea",
        "description": "Tea meetup",
        "location_text": "Utrecht",
        "venue": None,
        "event_url": "https://example.com/tea",
        "image_url": None,
        "start_at": datetime(2025, 7, 1, 9, 0, tzinfo=timezone.utc),
        "end_at": datetime(2025, 7, 1, 10, 0, tzinfo=timezone.utc),
        "detected_format": "html",
        "ingest_hash": "b" * 40,
        "raw_payload": {},
        "processing_state": "pending",
        "processing_errors": None,
        "fetched_at": now,
        "created_at": now,
    }
    base.update(overrides)
    return EventRaw(**base)


def _make_event_source(**overrides) -> EventSource:
    base = {
        "id": 3,
        "key": "tea_club",
        "name": "Tea Club",
        "base_url": "https://example.com",
        "list_url": "https://example.com/events",
        "selectors": {"format": "html", "item_selector": ".item", "title_selector": ".title"},
        "interval_minutes": 60,
        "status": "active",
        "last_run_at": None,
        "last_success_at": None,
        "last_error_at": None,
        "last_error": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return EventSource(**base)


@pytest.mark.asyncio
async def test_run_normalization_success(monkeypatch):
    raw = _make_event_raw()
    source = _make_event_source()
    updated_states = []
    inserted = []
    finished_payload = {}

    async def fake_fetch_pending(limit):
        return [raw]

    async def fake_get_source(source_id):
        return source

    async def fake_insert_candidate(candidate):
        inserted.append(candidate)

    async def fake_update_state(row_id, *, state, errors):
        updated_states.append((row_id, state, errors))

    async def fake_mark(*args, **kwargs):
        return None

    async def fake_update_progress(*args, **kwargs):
        return None

    async def fake_finish(run_id, status, progress, counters, error_message):
        finished_payload["status"] = status
        finished_payload["counters"] = counters

    monkeypatch.setattr(bot, "fetch_pending_event_raw", fake_fetch_pending)
    monkeypatch.setattr(bot, "get_event_source", fake_get_source)
    monkeypatch.setattr(bot, "insert_event_candidate", fake_insert_candidate)
    monkeypatch.setattr(bot, "update_event_raw_processing_state", fake_update_state)
    monkeypatch.setattr(bot, "mark_worker_run_running", fake_mark)
    monkeypatch.setattr(bot, "update_worker_run_progress", fake_update_progress)
    monkeypatch.setattr(bot, "finish_worker_run", fake_finish)

    exit_code = await bot.run_normalization(limit=10, worker_run_id=uuid4())

    assert exit_code == 0
    assert inserted, "expected candidate insert"
    assert updated_states[-1][1] == "normalized"
    assert finished_payload["status"] == "finished"
    assert finished_payload["counters"]["normalized"] == 1


@pytest.mark.asyncio
async def test_run_normalization_handles_normalization_error(monkeypatch):
    raw = _make_event_raw()
    source = _make_event_source()
    updated_states = []
    finished_payload = {}

    async def fake_fetch_pending(limit):
        return [raw]

    async def fake_get_source(source_id):
        return source

    async def fake_insert_candidate(candidate):  # pragma: no cover - should not be called
        raise AssertionError("insert_event_candidate should not be called on failure")

    async def fake_update_state(row_id, *, state, errors):
        updated_states.append((row_id, state, errors))

    async def fake_mark(*args, **kwargs):
        return None

    async def fake_update_progress(*args, **kwargs):
        return None

    async def fake_finish(run_id, status, progress, counters, error_message):
        finished_payload["status"] = status
        finished_payload["counters"] = counters

    def fake_normalize(raw_record, source_record):
        raise EventNormalizationError("missing_start_time")

    monkeypatch.setattr(bot, "fetch_pending_event_raw", fake_fetch_pending)
    monkeypatch.setattr(bot, "get_event_source", fake_get_source)
    monkeypatch.setattr(bot, "insert_event_candidate", fake_insert_candidate)
    monkeypatch.setattr(bot, "update_event_raw_processing_state", fake_update_state)
    monkeypatch.setattr(bot, "mark_worker_run_running", fake_mark)
    monkeypatch.setattr(bot, "update_worker_run_progress", fake_update_progress)
    monkeypatch.setattr(bot, "finish_worker_run", fake_finish)
    monkeypatch.setattr(bot, "normalize_event", fake_normalize)

    exit_code = await bot.run_normalization(limit=10, worker_run_id=uuid4())

    assert exit_code == 0
    assert updated_states[-1][1] == "error_norm"
    assert finished_payload["counters"]["errors"] == 1


