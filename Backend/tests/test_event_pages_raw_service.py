from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.event_pages_raw import EventPageRawCreate
from services import event_pages_raw_service
from services.event_pages_raw_service import (
    fetch_pending_event_pages,
    insert_event_page_raw,
    update_event_page_processing_state,
)


def _create_page(**overrides) -> EventPageRawCreate:
    base = {
        "event_source_id": 1,
        "page_url": "https://example.com/events",
        "http_status": 200,
        "response_headers": {"Content-Type": "text/html"},
        "response_body": "<html>events</html>",
        "content_hash": "a" * 40,
        "processing_state": "pending",
    }
    base.update(overrides)
    return EventPageRawCreate(**base)


@pytest.mark.asyncio
async def test_insert_event_page_raw_returns_id(monkeypatch):
    captured = {}

    async def fake_fetchrow(query, *args):
        captured["query"] = query
        captured["args"] = args
        return {"id": 77}

    monkeypatch.setattr(event_pages_raw_service, "fetchrow", fake_fetchrow)

    payload = _create_page()
    new_id = await insert_event_page_raw(payload)

    assert new_id == 77
    assert "event_pages_raw" in captured["query"]


@pytest.mark.asyncio
async def test_insert_event_page_raw_dedup(monkeypatch):
    async def fake_fetchrow(query, *args):
        return None

    monkeypatch.setattr(event_pages_raw_service, "fetchrow", fake_fetchrow)

    payload = _create_page()
    new_id = await insert_event_page_raw(payload)

    assert new_id is None


@pytest.mark.asyncio
async def test_fetch_pending_event_pages(monkeypatch):
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    fake_row = {
        "id": 5,
        "event_source_id": 1,
        "page_url": "https://example.com/events",
        "http_status": 200,
        "response_headers": {"Content-Type": "text/html"},
        "response_body": "<html>Event</html>",
        "content_hash": "b" * 40,
        "processing_state": "pending",
        "processing_errors": None,
        "fetched_at": now,
        "created_at": now,
    }

    async def fake_fetch(query, *args):
        assert "FROM event_pages_raw" in query
        return [dict(fake_row)]

    monkeypatch.setattr(event_pages_raw_service, "fetch", fake_fetch)

    rows = await fetch_pending_event_pages(limit=10)

    assert len(rows) == 1
    assert rows[0].id == 5
    assert rows[0].response_body.startswith("<html>")


@pytest.mark.asyncio
async def test_update_event_page_processing_state(monkeypatch):
    captured = {}

    async def fake_execute(query, *args):
        captured["query"] = query
        captured["args"] = args

    monkeypatch.setattr(event_pages_raw_service, "execute", fake_execute)

    await update_event_page_processing_state(10, state="extracted", errors={"ok": True})

    assert "UPDATE event_pages_raw" in captured["query"]
    assert captured["args"][0] == 10
    assert captured["args"][1] == "extracted"

