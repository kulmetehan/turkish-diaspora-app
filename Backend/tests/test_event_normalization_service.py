from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from app.models.event_raw import EventRaw
from app.models.event_sources import EventSource
from services.event_normalization_service import (
    EventNormalizationError,
    normalize_event,
)


def _make_event_raw(**overrides) -> EventRaw:
    now = datetime.now(timezone.utc)
    base = {
        "id": 1,
        "event_source_id": 1,
        "title": " Gala Night ",
        "description": "<p>Great evening</p>",
        "location_text": "Amsterdam",
        "venue": None,
        "event_url": "https://example.com/gala",
        "image_url": None,
        "start_at": datetime(2025, 5, 1, 18, 0, tzinfo=timezone.utc),
        "end_at": datetime(2025, 5, 1, 20, 0, tzinfo=timezone.utc),
        "detected_format": "html",
        "ingest_hash": "a" * 40,
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
        "id": 1,
        "key": "sample_source",
        "name": "Sample Source",
        "base_url": "https://example.com",
        "list_url": "https://example.com/events",
        "selectors": {"format": "html", "item_selector": ".card", "title_selector": ".title"},
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


def test_normalize_event_basic():
    raw = _make_event_raw()
    source = _make_event_source()

    candidate = normalize_event(raw, source)

    assert candidate.event_source_id == raw.event_source_id
    assert candidate.title == "Gala Night"
    assert candidate.description == "Great evening"
    assert candidate.location_text == "Amsterdam"
    assert candidate.url == "https://example.com/gala"
    assert candidate.start_time_utc.tzinfo == timezone.utc
    assert candidate.end_time_utc.tzinfo == timezone.utc


def test_normalize_event_without_end_time():
    start_local = datetime(2025, 6, 1, 19, 30)  # naive value
    raw = _make_event_raw(start_at=start_local, end_at=None)
    source = _make_event_source()

    candidate = normalize_event(raw, source)

    assert candidate.end_time_utc is None
    assert candidate.start_time_utc.tzinfo == timezone.utc


def test_normalize_event_invalid_url_becomes_none():
    raw = _make_event_raw(event_url="not a valid url")
    source = _make_event_source()

    candidate = normalize_event(raw, source)

    assert candidate.url is None


def test_normalize_event_missing_start_raises():
    raw = _make_event_raw(start_at=None)
    source = _make_event_source()

    with pytest.raises(EventNormalizationError):
        normalize_event(raw, source)


