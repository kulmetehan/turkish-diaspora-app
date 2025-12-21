# services/content_curation_service.py
from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

from pydantic import BaseModel, Field, field_validator

# --- Imports met fallback zodat zowel `services.*` als `app.services.*` werken ---
try:
    from services.db_service import ai_log
except Exception:  # pragma: no cover
    from app.services.db_service import ai_log  # type: ignore

try:
    from services.openai_service import OpenAIService
    _HAVE_OPENAI = True
except (ImportError, ModuleNotFoundError):
    try:
        from app.services.openai_service import OpenAIService  # type: ignore
        _HAVE_OPENAI = True
    except (ImportError, ModuleNotFoundError):
        OpenAIService = None  # type: ignore
        _HAVE_OPENAI = False
except Exception as e:
    import sys
    if "pytest" not in sys.modules:
        import logging
        logging.warning(f"Unexpected error importing OpenAIService: {e}")
    OpenAIService = None  # type: ignore
    _HAVE_OPENAI = False

# -----------------------------------------------------------------------------
# Prompt-bestanden relatief t.o.v. deze file
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
NEWS_SYSTEM_PATH = BASE_DIR / "prompts" / "curate_news_system.txt"
EVENTS_SYSTEM_PATH = BASE_DIR / "prompts" / "curate_events_system.txt"

# -----------------------------------------------------------------------------
# Outputmodellen
# -----------------------------------------------------------------------------
class RankedNewsItem(BaseModel):
    """Ranked news item with relevance score."""
    news_id: int
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    reason: str

class RankedEventItem(BaseModel):
    """Ranked event item with relevance score."""
    event_id: int
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    reason: str

class RankedNewsResponse(BaseModel):
    """Response from AI ranking news items."""
    rankings: List[RankedNewsItem]

class RankedEventsResponse(BaseModel):
    """Response from AI ranking events."""
    rankings: List[RankedEventItem]

JSON_SCHEMA_NEWS = {
    "type": "object",
    "properties": {
        "rankings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "news_id": {"type": "integer"},
                    "relevance_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "reason": {"type": "string"}
                },
                "required": ["news_id", "relevance_score", "reason"],
                "additionalProperties": False
            }
        }
    },
    "required": ["rankings"],
    "additionalProperties": False
}

JSON_SCHEMA_EVENTS = {
    "type": "object",
    "properties": {
        "rankings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer"},
                    "relevance_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "reason": {"type": "string"}
                },
                "required": ["event_id", "relevance_score", "reason"],
                "additionalProperties": False
            }
        }
    },
    "required": ["rankings"],
    "additionalProperties": False
}

def _maybe_schedule(func, *args, **kwargs) -> None:
    """
    ai_log kan sync of async zijn. Deze helper roept 'm veilig aan.
    """
    try:
        if asyncio.iscoroutinefunction(func):
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                asyncio.create_task(func(*args, **kwargs))
            else:
                asyncio.run(func(*args, **kwargs))
        else:
            func(*args, **kwargs)
    except Exception:
        # Logging-fouten mogen ranking niet breken.
        pass

class ContentCurationService:
    """
    AI service voor content curation op feed page.
    Rankt nieuwsitems en events op relevantie voor Turkse diaspora in Nederland.
    """
    
    def __init__(self, model: Optional[str] = None):
        self.model = model or "gpt-4o-mini"
        self.news_system_prompt = NEWS_SYSTEM_PATH.read_text(encoding="utf-8")
        self.events_system_prompt = EVENTS_SYSTEM_PATH.read_text(encoding="utf-8")
        self.JSON_SCHEMA_NEWS = JSON_SCHEMA_NEWS
        self.JSON_SCHEMA_EVENTS = JSON_SCHEMA_EVENTS

        if not _HAVE_OPENAI:
            raise RuntimeError(
                "OpenAIService is not available; check dependencies and OPENAI_API_KEY. "
                "ContentCurationService requires OpenAI to be properly configured for production use."
            )

        try:
            self.ai = OpenAIService(model=self.model)  # type: ignore
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

    def _call_generate_json_compat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        json_schema: Dict[str, Any],
    ) -> Tuple[BaseModel, Dict[str, Any]]:
        """
        Probeer meerdere signature-varianten van generate_json.
        Retourneert: (parsed: BaseModel, meta: dict)
        """
        errors = []

        # Variant A: met response_model via kwargs
        try:
            parsed, meta = self.ai.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=response_model,
            )
            return parsed, meta
        except TypeError as e:
            errors.append(("A", str(e)))

        # Variant B: met json_schema via kwargs
        try:
            raw, meta = self.ai.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema=json_schema,
            )
            if isinstance(raw, response_model):
                parsed = raw
            else:
                if isinstance(raw, (str, bytes)):
                    data = json.loads(raw)
                else:
                    data = raw
                parsed = response_model(**data)
            return parsed, meta
        except TypeError as e:
            errors.append(("B", str(e)))

        # Variant C: positioneel met response_model
        try:
            parsed, meta = self.ai.generate_json(system_prompt, user_prompt, response_model)
            return parsed, meta
        except TypeError as e:
            errors.append(("C", str(e)))

        # Variant D: positioneel met json_schema
        try:
            raw, meta = self.ai.generate_json(system_prompt, user_prompt, json_schema)
            if isinstance(raw, response_model):
                parsed = raw
            else:
                if isinstance(raw, (str, bytes)):
                    data = json.loads(raw)
                else:
                    data = raw
                parsed = response_model(**data)
            return parsed, meta
        except TypeError as e:
            errors.append(("D", str(e)))

        raise TypeError(
            "OpenAIService.generate_json() signature wordt niet herkend. "
            f"Probeerde varianten: {errors}"
        )

    def _build_news_prompt(self, news_items: List[Dict[str, Any]]) -> str:
        """Build user prompt for news ranking."""
        lines = ["Rangschik de volgende nieuwsitems op relevantie voor Turkse Nederlanders:\n"]
        for item in news_items:
            lines.append(f"ID: {item.get('id')}")
            lines.append(f"Titel: {item.get('title', '')}")
            if item.get('snippet'):
                lines.append(f"Snippet: {item.get('snippet')}")
            if item.get('source'):
                lines.append(f"Bron: {item.get('source')}")
            if item.get('tags'):
                lines.append(f"Tags: {', '.join(item.get('tags', []))}")
            lines.append("")
        lines.append("Geef enkel JSON output conform schema.")
        return "\n".join(lines)

    def _build_events_prompt(self, events: List[Dict[str, Any]]) -> str:
        """Build user prompt for events ranking."""
        lines = ["Rangschik de volgende events op relevantie voor Turkse diaspora in Nederland:\n"]
        for event in events:
            lines.append(f"ID: {event.get('id')}")
            lines.append(f"Titel: {event.get('title', '')}")
            if event.get('description'):
                lines.append(f"Beschrijving: {event.get('description')}")
            if event.get('location_text'):
                lines.append(f"Locatie: {event.get('location_text')}")
            if event.get('category_key'):
                lines.append(f"Categorie: {event.get('category_key')}")
            if event.get('city_key'):
                lines.append(f"Stad: {event.get('city_key')}")
            lines.append("")
        lines.append("Geef enkel JSON output conform schema.")
        return "\n".join(lines)

    async def rank_news_items(
        self,
        news_items: List[Dict[str, Any]],
        context: str = "Turkish diaspora in Netherlands",
    ) -> List[RankedNewsItem]:
        """
        Rank news items by relevance to Turkish Dutch people.
        
        Args:
            news_items: List of news item dicts with id, title, snippet, source, tags
            context: Context for ranking (default: Turkish diaspora in Netherlands)
            
        Returns:
            List of RankedNewsItem sorted by relevance_score (highest first)
        """
        if not news_items:
            return []

        # Batch processing: max 20 items per AI call
        batch_size = 20
        all_rankings: List[RankedNewsItem] = []

        for i in range(0, len(news_items), batch_size):
            batch = news_items[i:i + batch_size]
            user_prompt = self._build_news_prompt(batch)

            try:
                parsed, meta = self._call_generate_json_compat(
                    system_prompt=self.news_system_prompt,
                    user_prompt=user_prompt,
                    response_model=RankedNewsResponse,
                    json_schema=self.JSON_SCHEMA_NEWS,
                )

                # Log AI call
                _maybe_schedule(
                    ai_log,
                    location_id=None,
                    news_id=None,
                    event_raw_id=None,
                    action_type="content_curation",
                    prompt={"type": "rank_news", "items_count": len(batch), "context": context},
                    raw_response=meta.get("raw_response"),
                    validated_output=parsed.model_dump() if hasattr(parsed, "model_dump") else None,
                    model_used=self.model,
                    is_success=True,
                    error_message=None,
                )

                all_rankings.extend(parsed.rankings)

            except Exception as e:
                # Log error
                _maybe_schedule(
                    ai_log,
                    location_id=None,
                    news_id=None,
                    event_raw_id=None,
                    action_type="content_curation",
                    prompt={"type": "rank_news", "items_count": len(batch), "context": context},
                    raw_response=None,
                    validated_output=None,
                    model_used=self.model,
                    is_success=False,
                    error_message=str(e),
                )

                # Fallback: sort by published_at (newest first) with low relevance
                for item in batch:
                    all_rankings.append(RankedNewsItem(
                        news_id=item.get("id", 0),
                        relevance_score=0.3,
                        reason="Fallback: AI ranking failed, using default score"
                    ))

        # Sort by relevance_score (highest first)
        all_rankings.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_rankings

    async def rank_events(
        self,
        events: List[Dict[str, Any]],
        context: str = "Turkish diaspora in Netherlands",
    ) -> List[RankedEventItem]:
        """
        Rank events by relevance to Turkish diaspora.
        
        Args:
            events: List of event dicts with id, title, description, location_text, category_key, city_key
            context: Context for ranking (default: Turkish diaspora in Netherlands)
            
        Returns:
            List of RankedEventItem sorted by relevance_score (highest first)
        """
        if not events:
            return []

        # Batch processing: max 20 items per AI call
        batch_size = 20
        all_rankings: List[RankedEventItem] = []

        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            user_prompt = self._build_events_prompt(batch)

            try:
                parsed, meta = self._call_generate_json_compat(
                    system_prompt=self.events_system_prompt,
                    user_prompt=user_prompt,
                    response_model=RankedEventsResponse,
                    json_schema=self.JSON_SCHEMA_EVENTS,
                )

                # Log AI call
                _maybe_schedule(
                    ai_log,
                    location_id=None,
                    news_id=None,
                    event_raw_id=None,
                    action_type="content_curation",
                    prompt={"type": "rank_events", "items_count": len(batch), "context": context},
                    raw_response=meta.get("raw_response"),
                    validated_output=parsed.model_dump() if hasattr(parsed, "model_dump") else None,
                    model_used=self.model,
                    is_success=True,
                    error_message=None,
                )

                all_rankings.extend(parsed.rankings)

            except Exception as e:
                # Log error
                _maybe_schedule(
                    ai_log,
                    location_id=None,
                    news_id=None,
                    event_raw_id=None,
                    action_type="content_curation",
                    prompt={"type": "rank_events", "items_count": len(batch), "context": context},
                    raw_response=None,
                    validated_output=None,
                    model_used=self.model,
                    is_success=False,
                    error_message=str(e),
                )

                # Fallback: sort by start_time (upcoming first) with low relevance
                for event in batch:
                    all_rankings.append(RankedEventItem(
                        event_id=event.get("id", 0),
                        relevance_score=0.3,
                        reason="Fallback: AI ranking failed, using default score"
                    ))

        # Sort by relevance_score (highest first)
        all_rankings.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_rankings






