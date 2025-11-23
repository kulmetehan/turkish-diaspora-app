from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.models.event_sources import EventSource
from app.workers import event_scraper_bot
from services.event_scraper_service import EventScraperResult


def _make_source() -> EventSource:
    now = datetime.now(timezone.utc)
    return EventSource(
        id=1,
        key="test_source",
        name="Test Source",
        base_url="https://example.com",
        list_url="https://example.com/events",
        selectors={
            "format": "html",
            "item_selector": ".event",
            "title_selector": ".event-title",
        },
        interval_minutes=60,
        status="active",
        last_run_at=None,
        last_success_at=None,
        last_error_at=None,
        last_error=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_run_scraper_success(monkeypatch: pytest.MonkeyPatch) -> None:
    source = _make_source()

    async def fake_list_event_sources(status: str | None = None):
        return [source]

    monkeypatch.setattr(event_scraper_bot, "list_event_sources", fake_list_event_sources)

    class DummyService:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def scrape_source(self, src: EventSource) -> EventScraperResult:
            return EventScraperResult(
                event_source_id=src.id,
                total_items=3,
                inserted=2,
                errors=0,
                skipped=False,
            )

    monkeypatch.setattr(event_scraper_bot, "EventScraperService", DummyService)

    recorded_update: dict[str, object] = {}

    async def fake_mark_event_source_run(source_id: int, *, success: bool, error_message: str | None):
        recorded_update["source_id"] = source_id
        recorded_update["success"] = success
        recorded_update["error_message"] = error_message

    monkeypatch.setattr(event_scraper_bot, "mark_event_source_run", fake_mark_event_source_run)

    dummy_run_id = uuid4()

    async def fake_start_worker_run(bot: str, city, category):
        return dummy_run_id

    async def noop(*args, **kwargs):
        return None

    captured_finish: dict[str, object] = {}

    async def fake_finish_worker_run(
        run_id: UUID,
        status: str,
        progress: int,
        counters,
        error_message,
    ):
        captured_finish["run_id"] = run_id
        captured_finish["status"] = status
        captured_finish["progress"] = progress
        captured_finish["counters"] = counters
        captured_finish["error_message"] = error_message

    monkeypatch.setattr(event_scraper_bot, "start_worker_run", fake_start_worker_run)
    monkeypatch.setattr(event_scraper_bot, "mark_worker_run_running", noop)
    monkeypatch.setattr(event_scraper_bot, "update_worker_run_progress", noop)
    monkeypatch.setattr(event_scraper_bot, "finish_worker_run", fake_finish_worker_run)

    exit_code = await event_scraper_bot.run_scraper(limit=None, worker_run_id=None)

    assert exit_code == 0
    assert recorded_update["source_id"] == 1
    assert recorded_update["success"] is True
    counters = captured_finish["counters"]
    assert counters["total_sources"] == 1
    assert counters["processed_sources"] == 1
    assert counters["inserted_items"] == 2

