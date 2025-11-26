from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from services.openai_service import OpenAIService

logger = get_logger()

SYSTEM_PROMPT = (
    "You are an AI assistant that classifies news stories about the Turkish diaspora in the Netherlands. "
    "Respond ONLY with valid JSON that matches the provided schema. "
    "Scores must be floats between 0.0 and 1.0. "
    "Topics MUST be one or more of these exact values: \"politics\", \"economy\", \"culture\", \"religion\", \"sports\", \"security\". "
    "Do NOT use other topic values like \"diaspora\", \"migration\", or any other tags. "
    "Language must be an ISO 639-1 code like \"nl\", \"tr\", or \"en\". "
    "You MUST always include `location_mentions` (an array, possibly empty). "
    "Use these exact NL city_key values: rotterdam, amsterdam, den_haag, schiedam, vlaardingen. "
    "Use these exact TR city_key values: istanbul, ankara, izmir, antalya, bursa. "
    "Detect literal words AND morphological forms (e.g., \"Rotterdammers\", \"İstanbul'da\", \"Şişli'de\"). "
    "When a city appears in any inflected form, emit an object "
    "{\"city_key\": \"<key>\", \"country\": \"nl\"|\"tr\", \"confidence\": 0.0-1.0}."
)


class LocationMention(BaseModel):
    city_key: str
    country: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class NewsClassificationResult(BaseModel):
    relevance_diaspora: float = Field(..., ge=0.0, le=1.0)
    relevance_nl: float = Field(..., ge=0.0, le=1.0)
    relevance_tr: float = Field(..., ge=0.0, le=1.0)
    relevance_geo: float = Field(..., ge=0.0, le=1.0)
    topics: List[str] = Field(default_factory=list)
    language: str
    location_mentions: List[LocationMention] = Field(default_factory=list)


class NewsClassificationService:
    """LLM-powered classifier for raw news entries."""

    def __init__(self, *, model: Optional[str] = None) -> None:
        self._openai = OpenAIService(model=model)

    def classify_news_item(
        self,
        *,
        news_id: int,
        title: str,
        summary: Optional[str],
        content: Optional[str],
        source_key: str,
        language_hint: Optional[str] = None,
    ) -> Tuple[Optional[NewsClassificationResult], Dict[str, object]]:
        """
        Classify a news article. Returns (result, meta) where result is None when classification fails.
        """
        user_prompt = self._build_user_prompt(
            title=title,
            summary=summary,
            content=content,
            source_key=source_key,
            language_hint=language_hint,
        )

        try:
            parsed, meta = self._openai.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_model=NewsClassificationResult,
                action_type="news.classify",
                location_id=None,
                news_id=news_id,
            )
            meta = {"ok": True, **meta}
            return parsed, meta
        except Exception as exc:  # pragma: no cover - OpenAI failures already logged upstream
            logger.warning(
                "news_classification_failed",
                news_id=news_id,
                error=str(exc),
            )
            return None, {"ok": False, "error": str(exc)}

    def _build_user_prompt(
        self,
        *,
        title: str,
        summary: Optional[str],
        content: Optional[str],
        source_key: str,
        language_hint: Optional[str],
    ) -> str:
        parts = [
            f"Source key: {source_key}",
            f"Title: {title.strip()}",
        ]
        if language_hint:
            parts.append(f"Language hint: {language_hint}")
        if summary:
            parts.append(f"Summary: {_truncate(summary)}")
        if content:
            parts.append(f"Content: {_truncate(content, max_len=4000)}")
        parts.append(
            "Return JSON with relevance scores for diaspora focus (relevance_diaspora), "
            "Dutch context (relevance_nl), Turkish context (relevance_tr), geopolitics (relevance_geo), "
            "topics array, detected language, AND location_mentions (city_key, country, confidence). "
            "If any listed NL/TR city appears in ANY form (including suffixes like \"İstanbul'da\" or pluralized names), "
            "you MUST include a location mention using the canonical city_key."
        )
        return "\n".join(parts)


def _truncate(value: str, max_len: int = 2000) -> str:
    cleaned = value.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


