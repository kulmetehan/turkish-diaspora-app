# -*- coding: utf-8 -*-
"""
EventLocationValidator — AI-based location validator for events
- Validates if event locations are relevant for Turkish diaspora in Netherlands/Belgium/Germany/Europe
- Reuses OpenAIService patterns from ClassifyService
- Used as backup validation for edge cases after text-based filtering
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel

from app.core.logging import get_logger
from services.openai_service import OpenAIService

logger = get_logger()


class LocationValidationResult(BaseModel):
    """AI validation result for event location."""

    is_relevant: bool
    country: str
    confidence: float
    reason: str


class EventLocationValidator:
    """
    AI-based location validator for events.
    Reuses OpenAIService patterns from ClassifyService.
    """

    def __init__(self, model: Optional[str] = None):
        self._openai = OpenAIService(model=model)
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build system prompt for geographic validation."""
        return """You validate if event locations are relevant for Turkish diaspora in Netherlands/Belgium/Germany/Europe.

Return ONLY valid JSON (no markdown) that matches the schema:
{
  "is_relevant": boolean,
  "country": string (e.g., "Netherlands", "Belgium", "Germany", "United States"),
  "confidence": float (0-1),
  "reason": string
}

Rules:
- ALLOW: Netherlands, Belgium, Germany, Europe, Dutch cities (Rotterdam, Amsterdam, etc.)
- BLOCK: United States, USA, America, Canada, Mexico, Asia, Africa
- If unsure, default to is_relevant=false
- Confidence should reflect how certain you are about the location
- Reason should briefly explain your decision

Never invent details—use only provided data."""

    def validate_location(
        self,
        location_text: Optional[str],
        title: Optional[str] = None,
        event_raw_id: Optional[int] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate if event location is relevant.

        Args:
            location_text: Location text from event
            title: Event title (for context)
            event_raw_id: Optional event ID for logging

        Returns:
            (is_relevant: bool, meta: dict)
        """
        if not location_text and not title:
            logger.debug("location_validation_no_data")
            return False, {"reason": "no_location_info"}

        user_prompt = f"Location: {location_text or 'N/A'}\nTitle: {title or 'N/A'}"

        try:
            # Reuse OpenAIService.generate_json pattern
            result, meta = self._openai.generate_json(
                system_prompt=self._system_prompt,
                user_prompt=user_prompt,
                response_model=LocationValidationResult,
                action_type="events.location_validate",
                event_raw_id=event_raw_id,
            )

            is_relevant = result.is_relevant
            country = result.country

            logger.info(
                "event_location_validated",
                location=location_text,
                title=title,
                is_relevant=is_relevant,
                country=country,
                confidence=result.confidence,
                event_raw_id=event_raw_id,
            )

            return is_relevant, {
                "country": country,
                "confidence": result.confidence,
                "reason": result.reason,
                "meta": meta,
            }
        except Exception as e:
            logger.warning(
                "event_location_validation_failed",
                location=location_text,
                title=title,
                error=str(e),
                event_raw_id=event_raw_id,
            )
            # Default to blocking on error (safer)
            return False, {"error": str(e)}
















