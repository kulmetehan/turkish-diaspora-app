"""
Event Classification Service

Classifies events_candidate records to determine if they are relevant for Turkish diaspora.
Similar to ClassifyService for locations, but adapted for events.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.models.ai import AIEventClassification
from app.models.event_categories import EventCategory
from services.ai_validation import validate_classification_payload
from services.openai_service import OpenAIService

# Prompt file paths
BASE_DIR = Path(__file__).resolve().parent
EVENT_CLASSIFY_SYSTEM_PATH = BASE_DIR / "prompts" / "event_classify_system.txt"


def _load_system_prompt() -> str:
    """Load system prompt for event classification."""
    if EVENT_CLASSIFY_SYSTEM_PATH.exists():
        return EVENT_CLASSIFY_SYSTEM_PATH.read_text(encoding="utf-8")
    # Fallback prompt if file doesn't exist
    return """You classify Turkish diaspora events in the Netherlands.
Determine if the event is relevant for Turkish diaspora (action: keep) or not (action: ignore).
When action=keep, assign a category and confidence_score (0-1).
Categories (ALLEEN deze gebruiken): club, theater, concert, familie.
Return JSON: {"action": "keep|ignore", "category": "...", "confidence_score": 0.0-1.0, "reason": "..."}"""


class EventClassificationService:
    """Service for classifying events as Turkish diaspora relevant or not."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or "gpt-4o-mini"
        self.system_prompt = _load_system_prompt()
        
        try:
            self.ai = OpenAIService(model=self.model)
        except RuntimeError as e:
            error_msg = str(e)
            if "OPENAI_API_KEY" in error_msg or "ontbreekt" in error_msg:
                raise RuntimeError(
                    f"OpenAI API key is not configured. {error_msg} "
                    "Please set OPENAI_API_KEY environment variable."
                ) from e
            raise
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize OpenAIService: {e}. "
                "Check that the 'openai' package is installed and OPENAI_API_KEY is set correctly."
            ) from e

    def _build_user_prompt(
        self,
        *,
        title: str,
        description: Optional[str] = None,
        location_text: Optional[str] = None,
        source_key: Optional[str] = None,
    ) -> str:
        """Build user prompt for event classification."""
        lines = [
            f"Title: {title}",
            f"Description: {description or 'n/a'}",
            f"Location: {location_text or 'n/a'}",
            f"Source: {source_key or 'unknown'}",
        ]
        return "\n".join(lines)

    def classify_event(
        self,
        *,
        title: str,
        description: Optional[str] = None,
        location_text: Optional[str] = None,
        source_key: Optional[str] = None,
        event_raw_id: Optional[int] = None,
    ) -> Tuple[AIEventClassification, Dict[str, Any]]:
        """
        Classify an event to determine if it's relevant for Turkish diaspora.
        
        Returns:
            Tuple of (AIEventClassification, metadata dict)
        """
        user_prompt = self._build_user_prompt(
            title=title,
            description=description,
            location_text=location_text,
            source_key=source_key,
        )
        
        parsed, meta = self.ai.generate_json(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            response_model=AIEventClassification,
            action_type="events.classify",
            event_raw_id=event_raw_id,
        )
        
        return parsed, meta

