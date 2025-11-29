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
except (ImportError, ModuleNotFoundError):  # Only catch import-related errors
    try:
        from app.services.openai_service import OpenAIService  # type: ignore
        _HAVE_OPENAI = True
    except (ImportError, ModuleNotFoundError):
        OpenAIService = None  # type: ignore
        _HAVE_OPENAI = False
except Exception as e:
    # For non-import errors (e.g., config issues during import), log and mark unavailable
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
        "category": {
            "type": ["string", "null"],
            "description": "Required when action='keep'. Optional (may be null or omitted) when action='ignore'."
        },
        "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reason": {"type": "string"}
    },
    "required": ["action", "confidence_score", "reason"],
    "additionalProperties": False
}

# Explicit mapping from canonical category keys to enum values
COLLAPSE_MAP: Dict[str, Category] = {
    "bakery": Category.bakery,
    "restaurant": Category.restaurant,
    "supermarket": Category.supermarket,
    "butcher": Category.butcher,
    "barber": Category.barber,
    "fast_food": Category.fast_food,
    "cafe": Category.cafe,
    "mosque": Category.mosque,
    "travel_agency": Category.travel_agency,
}


def map_llm_category_to_enum(raw: Optional[str]) -> Category:
    """
    Map a raw LLM category string (e.g. 'bakkal/supermarket', 'barber', 'kebab')
    into a valid Category enum value.

    Uses category_map.normalize_category to get canonical key from YAML,
    then maps to enum via COLLAPSE_MAP.
    """
    if not raw or not str(raw).strip():
        return Category.other

    # Normalize via category_map (uses YAML aliases)
    try:
        normalized = normalize_category(str(raw))
    except Exception:
        # Be defensive: never let normalization errors crash classification
        return Category.other

    # Extract normalized key from dict result
    normalized_key = None
    if isinstance(normalized, dict):
        normalized_key = normalized.get("category_key")
    elif isinstance(normalized, str):
        normalized_key = normalized
    else:
        normalized_key = None

    if not normalized_key:
        return Category.other

    key = normalized_key.lower().strip()

    # Try explicit mapping first
    if key in COLLAPSE_MAP:
        return COLLAPSE_MAP[key]

    # If not in COLLAPSE_MAP but matches an enum member name exactly, use it
    try:
        # Check if key matches any Category enum member name
        for cat in Category:
            if cat.value == key:
                return cat
    except Exception:
        pass

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

        if not _HAVE_OPENAI:
            raise RuntimeError(
                "OpenAIService is not available; check dependencies and OPENAI_API_KEY. "
                "ClassifyService requires OpenAI to be properly configured for production use."
            )

        # Runtime check: verify OpenAIService can actually be instantiated
        try:
            self.ai = OpenAIService(model=self.model)  # type: ignore
        except RuntimeError as e:
            # OpenAIService.__init__ calls require_openai() which raises RuntimeError if key missing
            error_msg = str(e)
            if "OPENAI_API_KEY" in error_msg or "ontbreekt" in error_msg:
                raise RuntimeError(
                    f"OpenAI API key is not configured. {error_msg} "
                    "Please set OPENAI_API_KEY environment variable."
                ) from e
            raise
        except Exception as e:
            # Catch any other unexpected initialization errors
            raise RuntimeError(
                f"Failed to initialize OpenAIService: {e}. "
                "Check that the 'openai' package is installed and OPENAI_API_KEY is set correctly."
            ) from e

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

        # Defensive check: ensure we have a proper OpenAIService instance
        if not hasattr(self.ai, "generate_json"):
            raise RuntimeError(
                f"ClassifyService.ai does not have generate_json method. "
                f"Expected OpenAIService instance, got {type(self.ai)}"
            )

        # Call OpenAI service with compatibility layer
        parsed, meta = self._call_generate_json_compat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # Category normalization / defaulting
        # For action="ignore": preserve None (don't force to "other")
        # For action="keep": normalize category or use fallback
        if parsed.action == "keep":
            if not parsed.category:
                parsed.category = Category.other.value
            else:
                # Normalize LLM category output to valid enum value
                parsed.category = map_llm_category_to_enum(parsed.category).value
        # else: action="ignore" -> leave parsed.category as None (preserves existing DB category)

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


# NOTE: Stub client only for unit tests / offline experiments; not used in production pipeline.
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
