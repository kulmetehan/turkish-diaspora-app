from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.workers import news_ingest_bot


@pytest.mark.asyncio
async def test_run_ingest_success(monkeypatch):
    generated_run_id = uuid4()
    called = {"start": 0, "mark": 0, "progress": [], "finish": []}

    async def fake_start_worker_run(bot, city, category):
        called["start"] += 1
        return generated_run_id

    async def fake_mark_worker_run_running(run_id):
        called["mark"] += 1

    async def fake_update_worker_run_progress(run_id, progress):
        called["progress"].append(progress)

    async def fake_finish_worker_run(run_id, status, progress, counters, error_message):
        called["finish"].append(
            {
                "run_id": run_id,
                "status": status,
                "progress": progress,
                "counters": counters,
                "error_message": error_message,
            }
        )

    async def fake_ingest_all_sources(limit=None):
        return {"total_sources": 1, "total_inserted": 1, "failed_feeds": 0, "degraded": False}

    monkeypatch.setattr(news_ingest_bot, "start_worker_run", fake_start_worker_run)
    monkeypatch.setattr(news_ingest_bot, "mark_worker_run_running", fake_mark_worker_run_running)
    monkeypatch.setattr(news_ingest_bot, "update_worker_run_progress", fake_update_worker_run_progress)
    monkeypatch.setattr(news_ingest_bot, "finish_worker_run", fake_finish_worker_run)
    monkeypatch.setattr(news_ingest_bot, "ingest_all_sources", fake_ingest_all_sources)

    exit_code = await news_ingest_bot.run_ingest(limit=None, worker_run_id=None)

    assert exit_code == 0
    assert called["start"] == 1
    assert called["mark"] == 1
    assert called["finish"][0]["status"] == "finished"
    assert called["finish"][0]["counters"]["total_inserted"] == 1


@pytest.mark.asyncio
async def test_run_ingest_failure(monkeypatch):
    run_id = uuid4()
    finish_calls = []

    async def fake_start_worker_run(bot, city, category):
        return run_id

    async def fake_mark_worker_run_running(run_id):
        return None

    async def fake_update_worker_run_progress(run_id, progress):
        return None

    async def fake_finish_worker_run(run_id, status, progress, counters, error_message):
        finish_calls.append((status, error_message))

    async def fake_ingest_all_sources(limit=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(news_ingest_bot, "start_worker_run", fake_start_worker_run)
    monkeypatch.setattr(news_ingest_bot, "mark_worker_run_running", fake_mark_worker_run_running)
    monkeypatch.setattr(news_ingest_bot, "update_worker_run_progress", fake_update_worker_run_progress)
    monkeypatch.setattr(news_ingest_bot, "finish_worker_run", fake_finish_worker_run)
    monkeypatch.setattr(news_ingest_bot, "ingest_all_sources", fake_ingest_all_sources)

    exit_code = await news_ingest_bot.run_ingest(limit=1, worker_run_id=None)

    assert exit_code == 1
    assert finish_calls[0][0] == "failed"
    assert "boom" in finish_calls[0][1]




