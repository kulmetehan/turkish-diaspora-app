from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.event_extraction import ExtractedEvent, ExtractedEventsPayload
from services.event_extraction_service import EventExtractionService


class DummyOpenAI:
    def __init__(self, location_text: str = "Rotterdam") -> None:
        self.calls = []
        self.location_text = location_text

    def generate_json(self, **kwargs):
        self.calls.append(kwargs)
        payload = ExtractedEventsPayload(
            events=[
                ExtractedEvent(
                    title="Community Night",
                    description="Fun times",
                    start_at=datetime(2025, 1, 1, 18, tzinfo=timezone.utc),
                    end_at=datetime(2025, 1, 1, 20, tzinfo=timezone.utc),
                    location_text=self.location_text,
                )
            ]
        )
        return payload, {"ok": True}


def test_extract_events_from_html_calls_openai():
    dummy = DummyOpenAI()
    service = EventExtractionService(openai_client=dummy)

    payload, meta = service.extract_events_from_html(
        html="<div>Event</div>",
        source_key="sahmeran_events",
        page_url="https://sahmeran.nl/events",
        event_source_id=1,
    )

    assert payload.events
    assert meta["ok"] is True
    assert dummy.calls
    call = dummy.calls[0]
    assert call["action_type"] == "events.extract_from_html"


def test_extract_events_requires_html():
    service = EventExtractionService(openai_client=DummyOpenAI())
    with pytest.raises(ValueError):
        service.extract_events_from_html(
            html="   ",
            source_key="sahmeran_events",
            page_url="https://sahmeran.nl/events",
            event_source_id=1,
        )


def test_extract_events_model_dump_json_is_serializable():
    dummy = DummyOpenAI()
    service = EventExtractionService(openai_client=dummy)
    payload, _ = service.extract_events_from_html(
        html="<div>Event</div>",
        source_key="sahmeran_events",
        page_url="https://sahmeran.nl/events",
        event_source_id=1,
    )
    data = payload.model_dump(mode="json")
    assert isinstance(data["events"][0]["start_at"], str)


def test_extract_events_preserves_country_in_location():
    dummy = DummyOpenAI(location_text="Offenbach, Germany")
    service = EventExtractionService(openai_client=dummy)
    payload, _ = service.extract_events_from_html(
        html="<div>Event</div>",
        source_key="sahmeran_events",
        page_url="https://sahmeran.nl/events",
        event_source_id=1,
    )
    assert payload.events[0].location_text == "Offenbach, Germany"


def test_extract_events_does_not_add_country_when_missing():
    dummy = DummyOpenAI(location_text="Offenbach")
    service = EventExtractionService(openai_client=dummy)
    payload, _ = service.extract_events_from_html(
        html="<div>Event</div>",
        source_key="sahmeran_events",
        page_url="https://sahmeran.nl/events",
        event_source_id=1,
    )
    assert payload.events[0].location_text == "Offenbach"
