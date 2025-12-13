from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from app.models.event_extraction import ExtractedEventsPayload
from services.openai_service import OpenAIService


def _build_system_prompt() -> str:
    return (
        "You extract structured event information from raw HTML snippets. "
        "Return ONLY valid JSON with the schema:\n"
        "{\n"
        '  "events": [\n'
        "    {\n"
        '      "title": string,\n'
        '      "description": string | null,\n'
        '      "start_at": ISO 8601 datetime (Europe/Amsterdam if ambiguous),\n'
        '      "end_at": ISO 8601 datetime | null,\n'
        '      "location_text": string | null,\n'
        '      "venue": string | null,\n'
        '      "event_url": string | null,\n'
        '      "image_url": string | null\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Ignore navigation, ads, or non-event content. "
        "If multiple events are present, include each one. "
        "Copy location_text exactly as stated in the HTML (city + optional region or country). "
        "Never translate or infer a different country; only include a country when it appears in the source text. "
        "Do not append 'Netherlands' or any country unless it is explicitly written in the HTML.\n"
        "IMPORTANT: For start_at, always try to extract the actual event time (hour and minute) from the page. "
        "Only use midnight (00:00) if the page explicitly shows no time or only a date. "
        "Look for time patterns like '20:00', '8 PM', '20u', 'acht uur', time ranges, or opening times mentioned in the event details."
    )


class EventExtractionService:
    def __init__(
        self,
        *,
        model: Optional[str] = None,
        openai_client: Optional[OpenAIService] = None,
    ) -> None:
        self._openai = openai_client or OpenAIService(model=model)
        self._system_prompt = _build_system_prompt()

    def _build_user_prompt(
        self,
        *,
        html: str,
        source_key: str,
        page_url: str,
    ) -> str:
        return (
            f"Source key: {source_key}\n"
            f"Page URL: {page_url}\n"
            "HTML snippet:\n"
            f"{html.strip()}\n"
        )

    def extract_events_from_html(
        self,
        *,
        html: str,
        source_key: str,
        page_url: str,
        event_source_id: int,
    ) -> Tuple[ExtractedEventsPayload, Dict[str, Any]]:
        if not html or not html.strip():
            raise ValueError("html cannot be empty")

        user_prompt = self._build_user_prompt(
            html=html,
            source_key=source_key,
            page_url=page_url,
        )
        parsed, meta = self._openai.generate_json(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            response_model=ExtractedEventsPayload,
            action_type="events.extract_from_html",
            location_id=None,
            news_id=None,
            event_raw_id=None,
        )
        return parsed, meta


