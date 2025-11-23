from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.models.event_sources import EventSource
from app.workers import event_page_fetcher_bot as bot


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


@pytest.mark.asyncio
async def test_run_fetcher_stores_page(monkeypatch):
    captured = {}

    async def fake_start_worker_run(*args, **kwargs) -> UUID:
        return UUID(int=0)

    async def fake_finish_worker_run(run_id, status, progress, counters, error):
        captured["status"] = status
        captured["counters"] = counters
        captured["error"] = error

    monkeypatch.setattr(bot, "start_worker_run", fake_start_worker_run)
    monkeypatch.setattr(bot, "mark_worker_run_running", lambda *args, **kwargs: asyncio.sleep(0))
    monkeypatch.setattr(bot, "update_worker_run_progress", lambda *args, **kwargs: asyncio.sleep(0))
    monkeypatch.setattr(bot, "finish_worker_run", fake_finish_worker_run)

    async def fake_list_event_sources(status=None):
        return [_make_source()]

    monkeypatch.setattr(bot, "list_event_sources", fake_list_event_sources)

    async def fake_fetch_page_content(client, url):
        return 200, {"Content-Type": "text/html"}, "<html>Event</html>"

    monkeypatch.setattr(bot, "_fetch_page_content", fake_fetch_page_content)

    inserted_payloads = []

    async def fake_insert_event_page_raw(payload):
        inserted_payloads.append(payload)
        return 123

    monkeypatch.setattr(bot, "insert_event_page_raw", fake_insert_event_page_raw)

    exit_code = await bot.run_fetcher(limit=None, source_key=None, worker_run_id=None)

    assert exit_code == 0
    assert captured["status"] == "finished"
    assert inserted_payloads
    assert inserted_payloads[0].processing_state == "pending"


@pytest.mark.asyncio
async def test_run_fetcher_records_fetch_error(monkeypatch):
    stored: Dict[str, Any] = {}

    async def fake_start_worker_run(*args, **kwargs) -> UUID:
        return UUID(int=0)

    async def fake_finish_worker_run(run_id, status, progress, counters, error):
        stored["status"] = status
        stored["counters"] = counters

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(bot, "start_worker_run", fake_start_worker_run)
    monkeypatch.setattr(bot, "mark_worker_run_running", _noop)
    monkeypatch.setattr(bot, "update_worker_run_progress", _noop)
    monkeypatch.setattr(bot, "finish_worker_run", fake_finish_worker_run)

    async def fake_list_event_sources(status=None):
        return [_make_source("ajda_events")]

    monkeypatch.setattr(bot, "list_event_sources", fake_list_event_sources)

    async def fake_fetch_page_content(client, url):
        return 200, {"Content-Type": "text/html"}, "<html>Ajda</html>"

    monkeypatch.setattr(bot, "_fetch_page_content", fake_fetch_page_content)

    async def fake_insert_event_page_raw(payload):
        stored["payload"] = payload
        return 99

    monkeypatch.setattr(bot, "insert_event_page_raw", fake_insert_event_page_raw)

    exit_code = await bot.run_fetcher(limit=None, source_key=None, worker_run_id=None)

    assert exit_code == 0
    assert stored["payload"].event_source_id == 1
    assert stored["status"] == "finished"
    captured_payload = {}

    async def fake_start_worker_run(*args, **kwargs) -> UUID:
        return UUID(int=0)

    monkeypatch.setattr(bot, "start_worker_run", fake_start_worker_run)
    monkeypatch.setattr(bot, "mark_worker_run_running", lambda *args, **kwargs: asyncio.sleep(0))
    monkeypatch.setattr(bot, "update_worker_run_progress", lambda *args, **kwargs: asyncio.sleep(0))
    monkeypatch.setattr(bot, "finish_worker_run", lambda *args, **kwargs: asyncio.sleep(0))

    async def fake_list_event_sources(status=None):
        return [_make_source()]

    monkeypatch.setattr(bot, "list_event_sources", fake_list_event_sources)

    async def fake_fetch_page_content(client, url):
        raise RuntimeError("boom")

    monkeypatch.setattr(bot, "_fetch_page_content", fake_fetch_page_content)

    async def fake_insert_event_page_raw(payload):
        captured_payload["payload"] = payload
        return 1

    monkeypatch.setattr(bot, "insert_event_page_raw", fake_insert_event_page_raw)

    exit_code = await bot.run_fetcher(limit=None, source_key=None, worker_run_id=None)

    assert exit_code == 0
    assert captured_payload["payload"].processing_state == "error_fetch"
    assert captured_payload["payload"].processing_errors is not None
    assert stored["status"] == "finished"
    assert stored["status"] == "finished"


@pytest.mark.asyncio
async def test_run_fetcher_handles_ajda(monkeypatch):
    stored: Dict[str, Any] = {}

    async def fake_start_worker_run(*args, **kwargs) -> UUID:
        return UUID(int=0)

    async def fake_finish_worker_run(run_id, status, progress, counters, error):
        stored["status"] = status
        stored["counters"] = counters

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(bot, "start_worker_run", fake_start_worker_run)
    monkeypatch.setattr(bot, "mark_worker_run_running", _noop)
    monkeypatch.setattr(bot, "update_worker_run_progress", _noop)
    monkeypatch.setattr(bot, "finish_worker_run", fake_finish_worker_run)

    async def fake_list_event_sources(status=None):
        return [_make_source("ajda_events")]

    monkeypatch.setattr(bot, "list_event_sources", fake_list_event_sources)

    async def fake_fetch_page_content(client, url):
        return 200, {"Content-Type": "text/html"}, "<html>Ajda</html>"

    monkeypatch.setattr(bot, "_fetch_page_content", fake_fetch_page_content)

    async def fake_insert_event_page_raw(payload):
        stored["payload"] = payload
        return 99

    monkeypatch.setattr(bot, "insert_event_page_raw", fake_insert_event_page_raw)

    exit_code = await bot.run_fetcher(limit=None, source_key=None, worker_run_id=None)

    assert exit_code == 0
    assert stored["payload"].event_source_id == 1
    assert stored["status"] == "finished"

