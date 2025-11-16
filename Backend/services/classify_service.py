# services/classify_service.py
from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Literal, Callable

from pydantic import BaseModel, Field, field_validator

from app.models.ai import Category
from app.services.category_map import normalize_category

# --- Imports met fallback zodat zowel `services.*` als `app.services.*` werken ---
try:
    from services.db_service import ai_log  # kan sync of async zijn
except Exception:  # pragma: no cover
    from app.services.db_service import ai_log  # type: ignore

try:
    from services.openai_service import OpenAIService
    _HAVE_OPENAI = True
except Exception:  # pragma: no cover
    try:
        from app.services.openai_service import OpenAIService  # type: ignore
        _HAVE_OPENAI = True
    except Exception:
        OpenAIService = None  # type: ignore
        _HAVE_OPENAI = False

# -----------------------------------------------------------------------------
# Prompt-bestanden relatief t.o.v. deze file
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
SYSTEM_PATH = BASE_DIR / "prompts" / "classify_system.txt"
FEWSHOT_PATH = BASE_DIR / "prompts" / "classify_fewshot_nltr.md"

# -----------------------------------------------------------------------------
# Outputmodel
# -----------------------------------------------------------------------------
class ClassificationResult(BaseModel):
    action: Literal["keep", "ignore"]
    category: Optional[str] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reason: str

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return str(v).strip().lower()

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["keep", "ignore"]},
        "category": {"type": ["string", "null"]},
        "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reason": {"type": "string"}
    },
    "required": ["action", "confidence_score", "reason"],
    "additionalProperties": False
}

def map_llm_category_to_enum(raw: Optional[str]) -> Category:
    """
    Map a raw LLM category string (e.g. 'bakkal/supermarket', 'barber', 'kebab')
    into a valid Category enum value.

    Uses category_map.normalize_category and then collapses to our enum set.
    """
    if not raw or not str(raw).strip():
        return Category.other

    # Normalize via category_map
    try:
        normalized = normalize_category(str(raw))
    except Exception:
        # Be defensive: never let normalization errors crash classification
        return Category.other

    # Extract normalized key from dict result
    normalized_key = None
    if isinstance(normalized, dict):
        normalized_key = normalized.get("category_key") or normalized.get("key") or normalized.get("category")
    elif isinstance(normalized, str):
        normalized_key = normalized
    else:
        normalized_key = None

    if not normalized_key:
        return Category.other

    key = normalized_key.lower().strip()

    # Map normalized keys to enum values
    if key in ("bakery",):
        return Category.bakery
    if key in ("restaurant", "fast_food", "kebab"):
        # We treat fast food / kebab as restaurant for now
        return Category.restaurant
    if key in ("supermarket", "bakkal", "bakkal_supermarket", "bakkal/supermarket"):
        return Category.supermarket
    if key in ("barber", "barbershop", "kapper"):
        return Category.barbershop
    if key in ("mosque",):
        return Category.mosque
    if key in ("travel_agency", "travel", "agency"):
        return Category.travel_agency

    # Fallback: anything else
    return Category.other

def _build_user_prompt(name: str, address: Optional[str], typ: Optional[str]) -> str:
    parts = [f'Naam: "{name}"']
    if address:
        parts.append(f'Adres: "{address}"')
    if typ:
        parts.append(f'Type: "{typ}"')
    parts.append("Geef enkel JSON output conform schema.")
    return "\n".join(parts)

def _maybe_schedule(func: Callable, *args, **kwargs) -> None:
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
                asyncio.run(func(*args, **kwargs))  # fallback
        else:
            func(*args, **kwargs)
    except Exception:
        # Logging-fouten mogen classificatie niet breken.
        pass

class ClassifyService:
    def __init__(self, model: Optional[str] = None):
        self.model = model or "gpt-4.1-mini"
        self.system_prompt = SYSTEM_PATH.read_text(encoding="utf-8")
        self.fewshot = FEWSHOT_PATH.read_text(encoding="utf-8")
        self.JSON_SCHEMA = JSON_SCHEMA

        if _HAVE_OPENAI:
            self.ai = OpenAIService(model=self.model)  # type: ignore
        else:
            self.ai = SimpleOpenAIClient(model=self.model)

    def _call_generate_json_compat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> Tuple[ClassificationResult, Dict[str, Any]]:
        """
        Probeer meerdere signature-varianten van generate_json, zonder 'temperature', 'model', etc.
        Retourneert: (parsed: ClassificationResult, meta: dict)
        """
        errors = []

        # Variant A: met response_model via kwargs
        try:
            parsed, meta = self.ai.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=ClassificationResult,
            )
            return parsed, meta
        except TypeError as e:
            errors.append(("A", str(e)))

        # Variant B: met json_schema via kwargs
        try:
            raw, meta = self.ai.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema=self.JSON_SCHEMA,
            )
            # sommige implementaties retourneren direct dict/string i.p.v. (text, meta)
            if isinstance(raw, ClassificationResult):
                parsed = raw
            else:
                if isinstance(raw, (str, bytes)):
                    data = json.loads(raw)
                else:
                    data = raw  # hopelijk dict
                parsed = ClassificationResult(**data)
            return parsed, meta
        except TypeError as e:
            errors.append(("B", str(e)))

        # Variant C: positioneel met response_model
        try:
            parsed, meta = self.ai.generate_json(system_prompt, user_prompt, ClassificationResult)
            return parsed, meta
        except TypeError as e:
            errors.append(("C", str(e)))

        # Variant D: positioneel met json_schema
        try:
            raw, meta = self.ai.generate_json(system_prompt, user_prompt, self.JSON_SCHEMA)
            if isinstance(raw, ClassificationResult):
                parsed = raw
            else:
                if isinstance(raw, (str, bytes)):
                    data = json.loads(raw)
                else:
                    data = raw
                parsed = ClassificationResult(**data)
            return parsed, meta
        except TypeError as e:
            errors.append(("D", str(e)))

        # Als alles faalt, gooi de meest recente fout door met context
        raise TypeError(
            "OpenAIService.generate_json() signature wordt niet herkend. "
            f"Probeerde varianten: {errors}"
        )

    def classify(
        self,
        *,
        name: str,
        address: Optional[str],
        typ: Optional[str],
        location_id: Optional[int] = None,
    ) -> Tuple[ClassificationResult, Dict[str, Any]]:
        system_prompt = f"{self.system_prompt}\n\n-- FEW-SHOT --\n{self.fewshot}"
        user_prompt = _build_user_prompt(name, address, typ)

        # ---- Pad 1: echte OpenAIService met compat-call ----
        if _HAVE_OPENAI and hasattr(self.ai, "generate_json"):
            parsed, meta = self._call_generate_json_compat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            # Normalisatie / defaulting van category
            if parsed.action != "keep":
                parsed.category = Category.other.value
            elif not parsed.category:
                parsed.category = Category.other.value
            else:
                # Normalize LLM category output to valid enum value
                parsed.category = map_llm_category_to_enum(parsed.category).value

            # log non-blocking
            _maybe_schedule(
                ai_log,
                location_id=location_id,
                action_type="classify",
                prompt={"system": self.system_prompt, "fewshot": self.fewshot, "user": user_prompt},
                raw_response={"raw_text": meta.get("raw_text") if isinstance(meta, dict) else None, "meta": meta},
                validated_output=parsed.model_dump(),
                model_used=self.model,
                is_success=True,
                error_message=None,
            )
            return parsed, meta

        # ---- Pad 2: fallback client (zonder echte OpenAI-call) ----
        raw_text, raw_meta = self.ai.generate_json_like(system_prompt, user_prompt)
        try:
            data = json.loads(raw_text)
            parsed = ClassificationResult(**data)
            if parsed.action != "keep":
                parsed.category = Category.other.value
            elif not parsed.category:
                parsed.category = Category.other.value
            else:
                # Normalize LLM category output to valid enum value
                parsed.category = map_llm_category_to_enum(parsed.category).value

            is_success = True
            error_message = None
            validated_output = parsed.model_dump()
        except Exception as e:
            parsed = ClassificationResult(
                action="ignore", category=Category.other.value, confidence_score=0.0, reason="parse_error"
            )
            is_success = False
            error_message = str(e)
            validated_output = None

        _maybe_schedule(
            ai_log,
            location_id=location_id,
            action_type="classify",
            prompt={"system": self.system_prompt, "fewshot": self.fewshot, "user": user_prompt},
            raw_response={"raw_text": raw_text, "meta": raw_meta},
            validated_output=validated_output,
            model_used=self.model,
            is_success=is_success,
            error_message=error_message,
        )
        return parsed, raw_meta


class SimpleOpenAIClient:
    def __init__(self, model: str):
        self.model = model

    def generate_json_like(self, system_prompt: str, user_prompt: str) -> Tuple[str, Dict[str, Any]]:
        dummy = {
            "action": "ignore",
            "category": "other",
            "confidence_score": 0.0,
            "reason": "stub",
        }
        return json.dumps(dummy, ensure_ascii=False), {"model": self.model, "stub": True}
