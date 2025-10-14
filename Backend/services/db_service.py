# services/db_service.py
from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# --------------------------------------------------------------------
# DB engine
# --------------------------------------------------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment/.env")

# SQLAlchemy async engine (2.x style)
async_engine = create_async_engine(
    DATABASE_URL,
    future=True,
    echo=False,         # zet True voor debug SQL
    pool_pre_ping=True,
)

# --------------------------------------------------------------------
# AI log helper
# --------------------------------------------------------------------
async def ai_log(
    *,
    location_id: Optional[int],
    action_type: str,
    prompt: Optional[Dict[str, Any]],
    raw_response: Optional[Dict[str, Any]],
    validated_output: Optional[Dict[str, Any]],
    model_used: Optional[str],
    is_success: bool,
    error_message: Optional[str],
) -> None:
    """
    Schrijf een auditlog-rij naar ai_logs.
    prompt/raw_response/validated_output worden als JSONB opgeslagen.
    """
    q = text("""
        INSERT INTO ai_logs (
            location_id,
            action_type,
            prompt,
            raw_response,
            validated_output,
            model_used,
            is_success,
            error_message
        ) VALUES (
            :location_id,
            :action_type,
            CAST(:prompt AS JSONB),
            CAST(:raw_response AS JSONB),
            CAST(:validated_output AS JSONB),
            :model_used,
            :is_success,
            :error_message
        )
    """)

    params = {
        "location_id": location_id,
        "action_type": action_type,
        "prompt": json.dumps(prompt, ensure_ascii=False) if prompt is not None else None,
        "raw_response": json.dumps(raw_response, ensure_ascii=False) if raw_response is not None else None,
        "validated_output": json.dumps(validated_output, ensure_ascii=False) if validated_output is not None else None,
        "model_used": model_used,
        "is_success": is_success,
        "error_message": error_message,
    }

    async with async_engine.begin() as conn:
        await conn.execute(q, params)

# --------------------------------------------------------------------
# Fetch candidates to classify
# --------------------------------------------------------------------
async def fetch_candidates_for_classification(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Haal CANDIDATE rows op die nog geen confidence_score hebben.
    Pas de WHERE aan als je (her)classificatie wil.
    """
    q = text("""
        SELECT id, name, address, category AS type
        FROM locations
        WHERE state = 'CANDIDATE' AND confidence_score IS NULL
        ORDER BY first_seen_at ASC
        LIMIT :limit
    """)
    async with async_engine.begin() as conn:
        rows = (await conn.execute(q, {"limit": limit})).mappings().all()
        return [dict(r) for r in rows]

# --------------------------------------------------------------------
# Update classification result on a location  (FIXED)
# --------------------------------------------------------------------
async def update_location_classification(
    *,
    id: int,
    action: str,             # "keep" | "ignore"
    category: str,
    confidence_score: float,
    reason: Optional[str] = None,
) -> None:
    """
    Schrijf classificatie terug en update state:
      - keep   -> PENDING_VERIFICATION
      - ignore -> RETIRED
    Appende reason (indien niet leeg) aan notes met een newline.
    """

    # 1) State
    new_state = "PENDING_VERIFICATION" if action == "keep" else "RETIRED"

    # 2) Zorg dat reason altijd een STRING is voor Postgres/asyncpg
    reason_text = reason or ""   # <-- cruciaal: nooit None doorgeven

    # 3) Update
    # Geen casts of :param::text meer nodig; we gebruiken één tekstparam.
    q = text("""
        UPDATE locations
        SET
            category = :category,
            confidence_score = :score,
            state = :new_state,
            notes = CASE
                      WHEN :reason_text = '' THEN notes
                      ELSE COALESCE(notes, '')
                           || CASE WHEN notes IS NULL OR notes = '' THEN '' ELSE E'\\n' END
                           || :reason_text
                    END
        WHERE id = :id
    """)

    params = {
        "id": id,
        "category": category,
        "score": confidence_score,
        "new_state": new_state,
        "reason_text": reason_text,   # <-- altijd string
    }

    async with async_engine.begin() as conn:
        await conn.execute(q, params)
