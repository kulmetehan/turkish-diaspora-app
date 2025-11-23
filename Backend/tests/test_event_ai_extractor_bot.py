from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.models.event_extraction import ExtractedEvent, ExtractedEventsPayload
from app.models.event_pages_raw import EventPageRaw
from app.models.event_sources import EventSource
from app.workers import event_ai_extractor_bot as bot


def _make_page() -> EventPageRaw:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return EventPageRaw(
        id=11,
        event_source_id=1,
        page_url="https://sahmeran.nl/events",
        http_status=200,
        response_headers={"Content-Type": "text/html"},
        response_body="<html>Event</html>",
        content_hash="a" * 40,
        processing_state="pending",
        processing_errors=None,
        fetched_at=now,
        created_at=now,
    )


def _make_source(key: str = "sahmeran_events") -> EventSource:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return EventSource(
        id=1,
        key=key,
        name="Şahmeran",
        base_url="https://sahmeran.nl",
        list_url="https://sahmeran.nl/events",
        city_key="rotterdam",
        selectors={"format": "html", "item_selector": ".card", "title_selector": ".title"},
        interval_minutes=60,
        status="active",
        last_run_at=now,
        last_success_at=now,
        last_error_at=None,
        last_error=None,
        created_at=now,
        updated_at=now,
    )


class FakeExtractionService:
    def __init__(self, *args, **kwargs) -> None:
        self.calls = 0

    def extract_events_from_html(self, **kwargs):
        self.calls += 1
        payload = ExtractedEventsPayload(
            events=[
                ExtractedEvent(
                    title="Community Night",
                    description="Fun",
                    start_at=datetime(2025, 1, 2, 18, tzinfo=timezone.utc),
                    end_at=datetime(2025, 1, 2, 20, tzinfo=timezone.utc),
                    location_text="Rotterdam",
                )
            ]
        )
        return payload, {"ok": True}


@pytest.mark.asyncio
async def test_run_extractor_creates_event(monkeypatch):
    captured = {"states": [], "raw": []}

    async def fake_start_worker_run(*args, **kwargs) -> UUID:
        return UUID(int=0)

    async def fake_finish_worker_run(run_id, status, progress, counters, error):
        captured["counters"] = counters
        captured["status"] = status

    monkeypatch.setattr(bot, "start_worker_run", fake_start_worker_run)
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(bot, "mark_worker_run_running", _noop)
    monkeypatch.setattr(bot, "update_worker_run_progress", _noop)
    monkeypatch.setattr(bot, "finish_worker_run", fake_finish_worker_run)
    async def fake_fetch_pages(limit):
        return [_make_page()]

    async def fake_get_source(source_id):
        return _make_source()

    monkeypatch.setattr(bot, "fetch_pending_event_pages", fake_fetch_pages)
    monkeypatch.setattr(bot, "get_event_source", fake_get_source)

    async def fake_insert_event_raw(raw):
        captured["raw"].append(raw)
        return 101

    async def fake_update_page(page_id, state, errors=None):
        captured["states"].append((page_id, state, errors))

    monkeypatch.setattr(bot, "insert_event_raw", fake_insert_event_raw)
    monkeypatch.setattr(bot, "update_event_page_processing_state", fake_update_page)
    monkeypatch.setattr(bot, "EventExtractionService", lambda model=None: FakeExtractionService())

    exit_code = await bot.run_extractor(
        limit=5,
        chunk_size=16000,
        model=None,
        worker_run_id=None,
    )

    assert exit_code == 0
    assert captured["status"] == "finished"
    assert captured["raw"]
    assert captured["states"][-1][1] == "extracted"
    payload = captured["raw"][0].raw_payload
    assert isinstance(payload["extracted_event"]["start_at"], str)


@pytest.mark.asyncio
async def test_run_extractor_missing_source_marks_error(monkeypatch):
    captured_states = []

    async def fake_start_worker_run(*args, **kwargs) -> UUID:
        return UUID(int=0)

    monkeypatch.setattr(bot, "start_worker_run", fake_start_worker_run)
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(bot, "mark_worker_run_running", _noop)
    monkeypatch.setattr(bot, "update_worker_run_progress", _noop)
    monkeypatch.setattr(bot, "finish_worker_run", _noop)

    async def fake_fetch_pages(limit):
        return [_make_page()]

    async def fake_get_source(source_id):
        return None

    monkeypatch.setattr(bot, "fetch_pending_event_pages", fake_fetch_pages)
    monkeypatch.setattr(bot, "get_event_source", fake_get_source)

    async def fake_update_page(page_id, state, errors=None):
        captured_states.append((page_id, state, errors))

    monkeypatch.setattr(bot, "update_event_page_processing_state", fake_update_page)

    async def fake_insert(*_args, **_kwargs):
        return 1

    monkeypatch.setattr(bot, "insert_event_raw", fake_insert)
    monkeypatch.setattr(bot, "EventExtractionService", lambda model=None: FakeExtractionService())

    exit_code = await bot.run_extractor(
        limit=5,
        chunk_size=16000,
        model=None,
        worker_run_id=None,
    )

    assert exit_code == 0
    assert captured_states
    assert captured_states[-1][1] == "error_extract"


@pytest.mark.asyncio
async def test_run_extractor_handles_ediz(monkeypatch):
    captured = {"states": [], "raw": []}

    async def fake_start_worker_run(*args, **kwargs) -> UUID:
        return UUID(int=0)

    async def fake_finish_worker_run(run_id, status, progress, counters, error):
        captured["status"] = status
        captured["counters"] = counters

    monkeypatch.setattr(bot, "start_worker_run", fake_start_worker_run)
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(bot, "mark_worker_run_running", _noop)
    monkeypatch.setattr(bot, "update_worker_run_progress", _noop)
    monkeypatch.setattr(bot, "finish_worker_run", fake_finish_worker_run)

    async def fake_fetch_pages(limit):
        return [_make_page()]

    async def fake_get_source(source_id):
        return _make_source("ediz_events")

    monkeypatch.setattr(bot, "fetch_pending_event_pages", fake_fetch_pages)
    monkeypatch.setattr(bot, "get_event_source", fake_get_source)

    async def fake_insert_event_raw(raw):
        captured["raw"].append(raw)
        return 201

    async def fake_update_page(page_id, state, errors=None):
        captured["states"].append((page_id, state, errors))

    monkeypatch.setattr(bot, "insert_event_raw", fake_insert_event_raw)
    monkeypatch.setattr(bot, "update_event_page_processing_state", fake_update_page)
    monkeypatch.setattr(bot, "EventExtractionService", lambda model=None: FakeExtractionService())

    exit_code = await bot.run_extractor(limit=5, chunk_size=16000, model=None, worker_run_id=None)

    assert exit_code == 0
    assert captured["status"] == "finished"
    assert captured["raw"]
    assert captured["states"][-1][1] == "extracted"

