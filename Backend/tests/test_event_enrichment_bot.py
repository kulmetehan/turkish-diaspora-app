from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.models.event_enrichment import EventEnrichmentResult
from app.models.event_raw import EventRaw
from app.workers import event_enrichment_bot


def _sample_event() -> EventRaw:
    return EventRaw(
        id=101,
        event_source_id=5,
        title="Sosyal buluşma",
        description="Türk topluluğu için networking etkinliği.",
        location_text="Den Haag",
        venue="Community Hub",
        event_url="https://example.com/events/1",
        start_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
        end_at=None,
        detected_format="html",
        ingest_hash="a" * 40,
        raw_payload={},
        processing_state="normalized",
        fetched_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_run_enrichment_success(monkeypatch: pytest.MonkeyPatch) -> None:
    event = _sample_event()

    async def fake_init_db_pool():
        return None

    async def fake_fetch_normalized_event_raw(*, limit: int):
        return [event]

    recorded_apply = {}

    async def fake_apply_event_enrichment(**kwargs):
        recorded_apply.update(kwargs)

    async def fake_mark_event_enrichment_error(**_):
        raise AssertionError("error handler should not be called")

    class DummyService:
        def __init__(self, *args, **kwargs):
            pass

        def enrich_event(self, event_row: EventRaw):
            assert event_row.id == event.id
            result = EventEnrichmentResult(
                language_code="tr",
                category_key="community",
                summary="Kısa özet",
                confidence_score=0.9,
            )
            return result, {"ok": True}

    dummy_run_id = uuid4()

    async def fake_start_worker_run(bot: str, city, category):
        return dummy_run_id

    async def noop(*args, **kwargs):
        return None

    captured_finish = {}

    async def fake_finish_worker_run(run_id: UUID, status: str, progress: int, counters, error_message):
        captured_finish.update(
            {"run_id": run_id, "status": status, "progress": progress, "counters": counters, "error_message": error_message}
        )

    monkeypatch.setattr(event_enrichment_bot, "init_db_pool", fake_init_db_pool)
    monkeypatch.setattr(event_enrichment_bot, "fetch_normalized_event_raw", fake_fetch_normalized_event_raw)
    monkeypatch.setattr(event_enrichment_bot, "apply_event_enrichment", fake_apply_event_enrichment)
    monkeypatch.setattr(event_enrichment_bot, "mark_event_enrichment_error", fake_mark_event_enrichment_error)
    monkeypatch.setattr(event_enrichment_bot, "EventEnrichmentService", DummyService)
    monkeypatch.setattr(event_enrichment_bot, "start_worker_run", fake_start_worker_run)
    monkeypatch.setattr(event_enrichment_bot, "mark_worker_run_running", noop)
    monkeypatch.setattr(event_enrichment_bot, "update_worker_run_progress", noop)
    monkeypatch.setattr(event_enrichment_bot, "finish_worker_run", fake_finish_worker_run)

    exit_code = await event_enrichment_bot.run_enrichment(limit=5, model=None, worker_run_id=None)

    assert exit_code == 0
    assert recorded_apply["event_id"] == event.id
    assert recorded_apply["category_key"] == "community"
    assert captured_finish["status"] == "finished"
    assert captured_finish["counters"]["enriched"] == 1
    assert captured_finish["counters"]["errors"] == 0


@pytest.mark.asyncio
async def test_run_enrichment_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    event = _sample_event()

    async def fake_init_db_pool():
        return None

    async def fake_fetch_normalized_event_raw(*, limit: int):
        return [event]

    async def fake_apply_event_enrichment(**_):
        raise AssertionError("should not apply on failure path")

    recorded_errors = {}

    async def fake_mark_event_enrichment_error(**kwargs):
        recorded_errors.update(kwargs)

    class FailingService:
        def __init__(self, *args, **kwargs):
            pass

        def enrich_event(self, event_row: EventRaw):
            raise RuntimeError("boom")

    dummy_run_id = uuid4()

    async def fake_start_worker_run(bot: str, city, category):
        return dummy_run_id

    async def noop(*args, **kwargs):
        return None

    async def fake_finish_worker_run(run_id: UUID, status: str, progress: int, counters, error_message):
        return None

    monkeypatch.setattr(event_enrichment_bot, "init_db_pool", fake_init_db_pool)
    monkeypatch.setattr(event_enrichment_bot, "fetch_normalized_event_raw", fake_fetch_normalized_event_raw)
    monkeypatch.setattr(event_enrichment_bot, "apply_event_enrichment", fake_apply_event_enrichment)
    monkeypatch.setattr(event_enrichment_bot, "mark_event_enrichment_error", fake_mark_event_enrichment_error)
    monkeypatch.setattr(event_enrichment_bot, "EventEnrichmentService", FailingService)
    monkeypatch.setattr(event_enrichment_bot, "start_worker_run", fake_start_worker_run)
    monkeypatch.setattr(event_enrichment_bot, "mark_worker_run_running", noop)
    monkeypatch.setattr(event_enrichment_bot, "update_worker_run_progress", noop)
    monkeypatch.setattr(event_enrichment_bot, "finish_worker_run", fake_finish_worker_run)

    exit_code = await event_enrichment_bot.run_enrichment(limit=1, model=None, worker_run_id=None)

    assert exit_code == 0  # worker completes even with individual errors
    assert recorded_errors["event_id"] == event.id
    assert recorded_errors["error"]["error"] == "boom"


