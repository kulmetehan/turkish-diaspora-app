from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from app.models.event_enrichment import EventEnrichmentResult
from app.models.event_raw import EventRaw
from services.event_categories_service import (
    get_event_category_keys,
    normalize_event_category_key,
)
from services.openai_service import OpenAIService

def _build_system_prompt() -> str:
    categories = ", ".join(get_event_category_keys())
    return (
        "You analyze Turkish diaspora events in the Netherlands.\n"
        "Return ONLY valid JSON (no markdown) that matches the schema:\n"
        "{\n"
        '  "language_code": one of ["nl","tr","en","other"],\n'
        '  "category_key": one of [' + categories + '],\n'
        '  "summary": short natural-language summary (<=1000 chars),\n'
        '  "confidence_score": float between 0 and 1,\n'
        '  "extracted_location_text": optional location string extracted from title/description/venue if location_text is missing or empty (max 500 chars). Extract city, venue, or address if mentioned. Return null if no location found.\n'
        "}\n"
        "Language detection must be based on the event title/description.\n"
        "category_key should describe the event purpose (community, religion, culture, business, education, sports, other).\n"
        "If location_text is missing or empty, try to extract location info from title/description/venue.\n"
        "extracted_location_text should contain a city name (Rotterdam, Amsterdam, etc.), venue name, or address if found in the event data.\n"
        "Only extract location if location_text is missing or empty. If location_text exists, set extracted_location_text to null.\n"
        "If unsure, choose 'other' for category_key.\n"
        "Never invent details—use only provided data."
    )


class EventEnrichmentService:
    def __init__(
        self,
        *,
        model: Optional[str] = None,
        openai_client: Optional[OpenAIService] = None,
    ) -> None:
        self._openai = openai_client or OpenAIService(model=model)
        self._system_prompt = _build_system_prompt()

    def _format_datetime(self, value: Optional[datetime]) -> str:
        if not value:
            return ""
        return value.astimezone().isoformat()

    def _build_user_prompt(self, event: EventRaw) -> str:
        lines = [
            f"Title: {event.title or 'Untitled'}",
            f"Description: {event.description or 'n/a'}",
            f"Venue: {event.venue or 'n/a'}",
            f"Location text: {event.location_text or 'n/a'}",
            f"Event URL: {event.event_url or 'n/a'}",
            f"Start: {self._format_datetime(event.start_at) or 'unknown'}",
            f"End: {self._format_datetime(event.end_at) or 'unknown'}",
        ]
        return "\n".join(lines)

    def enrich_event(self, event: EventRaw) -> Tuple[EventEnrichmentResult, Dict[str, Any]]:
        if not event.id:
            raise ValueError("EventRaw.id is required for enrichment")

        user_prompt = self._build_user_prompt(event)
        parsed, meta = self._openai.generate_json(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            response_model=EventEnrichmentResult,
            action_type="events.enrich",
            event_raw_id=event.id,
        )
        parsed.category_key = normalize_event_category_key(parsed.category_key)
        return parsed, meta


