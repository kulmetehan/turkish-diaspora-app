from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Tuple

import pytest

from app.models.event_enrichment import EventEnrichmentResult
from app.models.event_raw import EventRaw
from services.event_enrichment_service import EventEnrichmentService


class DummyOpenAI:
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload
        self.calls: Dict[str, Any] = {}

    def generate_json(self, **kwargs) -> Tuple[EventEnrichmentResult, Dict[str, Any]]:
        self.calls = kwargs
        return EventEnrichmentResult(**self.payload), {"ok": True}


def _sample_event(**overrides: Any) -> EventRaw:
    defaults = dict(
        id=1,
        event_source_id=10,
        title="Sample Event",
        description="Kültürel gece",
        location_text="Rotterdam",
        venue="Community Center",
        event_url="https://example.com/event",
        start_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_at=None,
        detected_format="html",
        ingest_hash="f" * 40,
        raw_payload={},
        processing_state="pending",
    )
    defaults.update(overrides)
    return EventRaw(**defaults)


def test_enrich_event_normalizes_category_key():
    dummy_payload = {
        "language_code": "TR",
        "category_key": "Community",
        "summary": "Etkinlik özeti",
        "confidence_score": 0.82,
    }
    dummy_ai = DummyOpenAI(dummy_payload)
    service = EventEnrichmentService(openai_client=dummy_ai)

    result, meta = service.enrich_event(_sample_event())

    assert meta["ok"] is True
    assert result.category_key == "community"
    assert result.language_code == "tr"
    assert result.summary == "Etkinlik özeti"
    assert result.confidence_score == pytest.approx(0.82)


def test_enrich_event_requires_id():
    dummy_payload = {
        "language_code": "nl",
        "category_key": "other",
        "summary": "summary",
        "confidence_score": 0.5,
    }
    service = EventEnrichmentService(openai_client=DummyOpenAI(dummy_payload))
    event = _sample_event()
    event.id = None  # type: ignore[assignment]

    with pytest.raises(ValueError):
        service.enrich_event(event)


