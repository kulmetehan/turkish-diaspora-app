# services/openai_service.py
from __future__ import annotations

import asyncio
import json
import math
import re
import time
from typing import Any, Dict, Optional, Tuple, Type

from openai import OpenAI  # pip install openai>=2
from pydantic import BaseModel, ValidationError

from app.config import settings, require_openai
from services.db_service import ai_log  # logt naar jouw ai_logs-schema

_JSON_HINT = (
    "Reageer uitsluitend met één geldige JSON, zonder uitleg, "
    "zonder extra tekst, geen markdown, geen codeblokken."
)

def _pydantic_schema_dict(model: Type[BaseModel]) -> Dict[str, Any]:
    return model.model_json_schema()  # pydantic v2

def _extract_first_json(text: str) -> str:
    """
    Robuuste parser: pak het eerste {...}-blok en verwijder trailing commas.
    """
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    candidate = m.group(0) if m else text.strip()
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)  # trailing commas weg
    return candidate.strip()

def _to_jsonable(obj: Any) -> Any:
    """
    Zet OpenAI SDK objecten (bv. usage) om naar JSON-serialiseerbare dicts.
    Probeert .model_dump(), .model_dump_json(), dict(), en valt terug op str().
    """
    # Al JSONable?
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}

    # pydantic-like
    try:
        return {k: _to_jsonable(v) for k, v in obj.model_dump().items()}  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        return json.loads(obj.model_dump_json())  # type: ignore[attr-defined]
    except Exception:
        pass

    # mapping-like
    try:
        return {k: _to_jsonable(v) for k, v in dict(obj).items()}
    except Exception:
        pass

    # laatste redmiddel
    return str(obj)

class OpenAIService:
    """
    JSON-gedwongen AI-service met Pydantic-validatie en logging naar ai_logs.
    Mapt 1-op-1 op jouw kolommen in ai_logs.
    """

    def __init__(self, model: Optional[str] = None, max_retries: int = 2, timeout_s: int = 60):
        require_openai()
        self.model = model or settings.OPENAI_MODEL
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def _build_messages(self, system_prompt: str, user_prompt: str, schema: Dict[str, Any]) -> list[dict]:
        schema_hint = json.dumps(schema, ensure_ascii=False)
        system = (
            f"{system_prompt}\n\n{_JSON_HINT}\n"
            f"Het JSON moet exact overeenkomen met deze JSON Schema (Pydantic):\n{schema_hint}"
        )
        user = f"{user_prompt}\n\nNogmaals: {_JSON_HINT}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
        action_type: str = "generic",
        location_id: Optional[int] = None,
        news_id: Optional[int] = None,
    ) -> Tuple[BaseModel, Dict[str, Any]]:
        """
        Returns: (parsed_model_instance, meta_dict)
        """
        schema = _pydantic_schema_dict(response_model)
        messages = self._build_messages(system_prompt, user_prompt, schema)
        prompt_payload = {"system": system_prompt, "user": user_prompt, "schema": schema}

        last_err: Optional[Exception] = None
        t0 = time.perf_counter()

        for attempt in range(self.max_retries + 1):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    timeout=self.timeout_s,
                )
                raw_text = completion.choices[0].message.content or ""
                usage = getattr(completion, "usage", None)
                usage_plain = _to_jsonable(usage)

                candidate = _extract_first_json(raw_text)
                data = json.loads(candidate)

                parsed = response_model.model_validate(data)

                duration_ms = int((time.perf_counter() - t0) * 1000)

                # Logging → aansluitend op jouw schema (async safe)
                asyncio.create_task(ai_log(
                    location_id=location_id,
                    news_id=news_id,
                    action_type=action_type,
                    prompt=prompt_payload,  # als TEXT in DB (JSON-string)
                    raw_response={
                        "raw": raw_text,
                        "usage": usage_plain,
                        "duration_ms": duration_ms,
                    },
                    validated_output=data,
                    model_used=self.model,
                    is_success=True,
                    error_message=None,
                ))

                return parsed, {
                    "ok": True,
                    "model": self.model,
                    "raw_text": raw_text,
                    "usage": usage_plain,
                    "duration_ms": duration_ms,
                }

            except (ValidationError, json.JSONDecodeError) as e:
                last_err = e
                wait = 0.7 * (2 ** attempt)
                messages[-1]["content"] = (
                    f"{user_prompt}\n\nLET OP: {_JSON_HINT}\n"
                    "Beantwoord exact volgens het schema, zonder bijkomende tekst."
                )
                time.sleep(wait)
                continue

            except Exception as e:
                last_err = e
                wait = 0.9 * (2 ** attempt)
                time.sleep(wait)
                continue

        duration_ms = int((time.perf_counter() - t0) * 1000)

        # Failure logging (async safe)
        asyncio.create_task(ai_log(
            location_id=location_id,
            news_id=news_id,
            action_type=action_type,
            prompt=prompt_payload,
            raw_response={"raw": None, "usage": None, "duration_ms": duration_ms},
            validated_output=None,
            model_used=self.model,
            is_success=False,
            error_message=str(last_err),
        ))
        raise RuntimeError(f"OpenAIService failed after retries: {last_err}")