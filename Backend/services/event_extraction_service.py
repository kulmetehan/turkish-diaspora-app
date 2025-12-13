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
        "If multiple events are present, include each one.\n"
        "LOCATION EXTRACTION RULES (CRITICAL - READ CAREFULLY):\n"
        "- venue: Extract the specific venue name (e.g., 'Theater Zuidplein', 'Meervaart', 'Rode Zaal', 'Capitol Theater', 'Grote Zaal'). "
        "This is the name of the building, hall, or specific location where the event takes place. "
        "If the venue name appears with additional details like 'Grote Zaal' or 'Rode Zaal', include the full venue name.\n"
        "- location_text: Extract the COMPLETE location information for geocoding. This is the MOST IMPORTANT field for accurate map display.\n"
        "  SEARCH STRATEGY: Look carefully through the entire HTML for location information. Check:\n"
        "    * Address sections (look for 'adres', 'address', 'locatie', 'location', 'waar', 'where')\n"
        "    * Venue information sections\n"
        "    * Event details sections\n"
        "    * Any text that contains street names, postal codes, or venue names\n"
        "  EXTRACTION PRIORITY (in order of preference):\n"
        "    1. FULL ADDRESS: If you find a complete address (street name + number + postal code + city), use it EXACTLY as written.\n"
        "       Examples: 'Strevelsweg 700-301, 3083 Rotterdam, Netherlands' or 'Theaterplein 1, 3012 CK Rotterdam'\n"
        "       DO NOT simplify or shorten addresses - include ALL parts (street, number, postal code, city).\n"
        "    2. VENUE + ADDRESS: If venue name and address are separate, combine them: 'Venue Name, Street + Number, Postal Code, City'\n"
        "       Example: 'Theater Zuidplein, Strevelsweg 700-301, 3083 Rotterdam'\n"
        "    3. VENUE + CITY: If only venue name and city are available: 'Venue Name, City'\n"
        "       Example: 'Theater Zuidplein, Rotterdam' or 'Meervaart, Amsterdam'\n"
        "    4. CITY ONLY: Only use city name if no venue or address information is found anywhere in the HTML.\n"
        "  IMPORTANT NOTES:\n"
        "    - Always include the city name in location_text for context, even when a full address is present.\n"
        "    - If you see multiple location references (e.g., venue name in one place, address in another), COMBINE them into one complete location_text.\n"
        "    - Look for postal codes (4 digits + 2 letters format like '3083 AB' or '3012 CK') - these indicate a full address is available.\n"
        "    - Never translate or infer a different country; only include a country when it appears in the source text.\n"
        "    - Do not append 'Netherlands' or any country unless it is explicitly written in the HTML.\n"
        "    - If the HTML shows 'Theater Zuidplein, Grote Zaal' with an address, include both: 'Theater Zuidplein, Grote Zaal, [full address]'\n"
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


