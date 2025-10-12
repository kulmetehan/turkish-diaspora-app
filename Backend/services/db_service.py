# services/db_service.py
from __future__ import annotations

import json
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings

# Maak hier zelf de Async Engine; geen aparte services/database.py meer nodig
# DATABASE_URL in jouw .env is al asyncpg-compatibel:
# postgresql+asyncpg://user:pass@host:5432/db
async_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    echo=False,  # zet True voor SQL-debug
)

async def _insert_ai_log(
    *,
    location_id: Optional[int],
    action_type: str,
    prompt: Dict[str, Any],
    raw_response: Dict[str, Any],
    validated_output: Optional[Dict[str, Any]],
    model_used: str,
    is_success: bool,
    error_message: Optional[str],
) -> None:
    """
    Schrijft naar jouw ai_logs tabel met exact jouw kolomnamen:
      id bigint (SERIAL/BIGSERIAL),
      location_id bigint,
      action_type text,
      prompt text,
      raw_response jsonb,
      validated_output jsonb,
      model_used text,
      is_success boolean,
      error_message text,
      created_at timestamptz
    """
    q = text("""
        INSERT INTO ai_logs
        (location_id, action_type, prompt, raw_response, validated_output, model_used, is_success, error_message, created_at)
        VALUES
        (:location_id, :action_type, :prompt, :raw_response, :validated_output, :model_used, :is_success, :error_message, :created_at)
    """)

    params = {
        "location_id": location_id,
        "action_type": action_type,
        "prompt": json.dumps(prompt, ensure_ascii=False),  # als TEXT in DB
        "raw_response": json.dumps(raw_response, ensure_ascii=False),  # JSONB
        "validated_output": json.dumps(validated_output, ensure_ascii=False) if validated_output is not None else None,  # JSONB
        "model_used": model_used,
        "is_success": is_success,
        "error_message": error_message,
        "created_at": datetime.now(timezone.utc),
    }

    async with async_engine.begin() as conn:
        await conn.execute(q, params)


def ai_log(
    *,
    location_id: Optional[int],
    action_type: str,
    prompt: Dict[str, Any],
    raw_response: Dict[str, Any],
    validated_output: Optional[Dict[str, Any]],
    model_used: str,
    is_success: bool,
    error_message: Optional[str],
) -> None:
    """
    Synchronous façade. Start een background task als we in een event loop zitten.
    """
    import asyncio

    async def _runner():
        await _insert_ai_log(
            location_id=location_id,
            action_type=action_type,
            prompt=prompt,
            raw_response=raw_response,
            validated_output=validated_output,
            model_used=model_used,
            is_success=is_success,
            error_message=error_message,
        )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        asyncio.create_task(_runner())
    else:
        asyncio.run(_runner())
