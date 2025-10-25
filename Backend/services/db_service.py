# services/db_service.py
from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional
import asyncio
from urllib.parse import urlparse

from dotenv import load_dotenv
import logging
import asyncpg

# --------------------------------------------------------------------
# DB config
# --------------------------------------------------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment/.env")


def normalize_database_url(raw_dsn: str) -> str:
    """
    Keep Supabase username EXACT (ex: postgres.shkzerlxzuzourbxujwx),
    keep encoded password EXACT,
    keep host/port/db EXACT,
    just rewrite scheme from postgresql+asyncpg:// → postgresql:// if needed.
    No other rewriting. No default user. No port swapping.
    """
    raw_dsn = raw_dsn.strip()
    if raw_dsn.startswith("postgresql+asyncpg://"):
        raw_dsn = "postgresql://" + raw_dsn[len("postgresql+asyncpg://"):]
    return raw_dsn

logger = logging.getLogger(__name__)

# No DSN rebuilding here; we keep DATABASE_URL as-is and only normalize scheme at pool creation time.

# --------------------------------------------------------------------
# Lightweight asyncpg pool + helpers (pool size clamped to 1)
# --------------------------------------------------------------------
_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()

async def ensure_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool

    async with _pool_lock:
        if _pool is not None:
            return _pool

        raw_dsn = os.getenv("DATABASE_URL", "").strip()
        final_dsn = normalize_database_url(raw_dsn)

        # --- DEBUG START ---
        try:
            parsed = urlparse(final_dsn)
            debug_user = parsed.username
            debug_host = parsed.hostname
            debug_port = parsed.port
            print(
                "db_engine_debug_user_host_port",
                debug_user,
                debug_host,
                debug_port,
                flush=True,
            )
            # print DSN prefix without leaking host/password
            print(
                "db_engine_debug_prefix",
                final_dsn.split("@")[0],
                flush=True,
            )
        except Exception as e:
            print("db_engine_debug_parse_error", str(e), flush=True)
        # --- DEBUG END ---

        logger.info("Initializing asyncpg connection pool (min=1, max=1)...")
        _pool = await asyncpg.create_pool(
            dsn=final_dsn,
            min_size=1,
            max_size=1,
            command_timeout=60,
            timeout=60,
            statement_cache_size=0,
            max_inactive_connection_lifetime=30,
        )
        return _pool

async def init_db_pool() -> asyncpg.Pool:
    # Backwards-compatible wrapper; safe to call multiple times
    return await ensure_pool()

async def fetch(query: str, *args):
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def execute(query: str, *args):
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)

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
    try:
        sql = (
            """
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
                $1,
                $2,
                CAST($3 AS JSONB),
                CAST($4 AS JSONB),
                CAST($5 AS JSONB),
                $6,
                $7,
                $8
            )
            """
        )

        await execute(
            sql,
            location_id,
            action_type,
            json.dumps(prompt, ensure_ascii=False) if prompt is not None else None,
            json.dumps(raw_response, ensure_ascii=False) if raw_response is not None else None,
            json.dumps(validated_output, ensure_ascii=False) if validated_output is not None else None,
            model_used,
            is_success,
            error_message,
        )
    except Exception as e:
        logger.warning("ai_log failed", exc_info=e)
        return

# --------------------------------------------------------------------
# Fetch candidates to classify
# --------------------------------------------------------------------
async def fetch_candidates_for_classification(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Haal CANDIDATE rows op die nog geen confidence_score hebben.
    Pas de WHERE aan als je (her)classificatie wil.
    """
    sql = (
        """
        SELECT id, name, address, category AS type
        FROM locations
        WHERE state = 'CANDIDATE' AND confidence_score IS NULL
        ORDER BY first_seen_at ASC
        LIMIT $1
        """
    )
    rows = await fetch(sql, limit)
    return [dict(r) for r in rows]

# --------------------------------------------------------------------
# Update classification result on a location (idempotent + no-downgrade)
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
    Persist AI/manual classification while enforcing:
      - State thresholds (keep=VERIFIED/PENDING_VERIFICATION/CANDIDATE by confidence; ignore=RETIRED)
      - No downgrade of VERIFIED, no resurrection of RETIRED
      - Always stamps last_verified_at = NOW()
      - Appends reason into notes (newline-separated)
    """

    # Fetch current state to enforce no-downgrade/no-resurrection
    row_sql = """
        SELECT state, COALESCE(is_retired, false) AS is_retired
        FROM locations
        WHERE id = $1
    """
    rows = await fetch(row_sql, int(id))
    current_state = None
    is_retired = False
    if rows:
        rec = dict(rows[0])
        current_state = (rec.get("state") or "").upper()
        is_retired = bool(rec.get("is_retired"))

    # Derive desired target state from action + confidence
    action_l = (action or "").strip().lower()
    if action_l == "ignore":
        desired_state = "RETIRED"
    elif action_l == "keep":
        if float(confidence_score) >= 0.90:
            desired_state = "VERIFIED"
        elif float(confidence_score) >= 0.80:
            desired_state = "PENDING_VERIFICATION"
        else:
            desired_state = "CANDIDATE"
    else:
        desired_state = "CANDIDATE"

    # Enforce no-downgrade/no-resurrection
    final_state = desired_state
    if current_state == "VERIFIED":
        final_state = "VERIFIED"  # never demote VERIFIED
    elif current_state == "RETIRED" or is_retired:
        final_state = "RETIRED"   # never resurrect RETIRED

    reason_text = reason or ""

    # Update with stamp
    sql = (
        """
        UPDATE locations
        SET
            category = $1,
            confidence_score = $2,
            state = $3,
            notes = CASE
                      WHEN $4 = '' THEN notes
                      ELSE COALESCE(notes, '')
                           || CASE WHEN notes IS NULL OR notes = '' THEN '' ELSE E'\\n' END
                           || $4
                    END,
            last_verified_at = NOW()
        WHERE id = $5
        """
    )

    await execute(
        sql,
        category,
        float(confidence_score),
        final_state,
        reason_text,
        int(id),
    )


# --------------------------------------------------------------------
# Mark as inspected without changing classification
# --------------------------------------------------------------------
async def mark_last_verified(id: int, note: Optional[str] = None) -> None:
    """
    Set last_verified_at = NOW() and optionally append a note, without changing
    confidence_score/state/category. Use to avoid reprocessing items repeatedly.
    """
    note_text = note or ""
    sql = (
        """
        UPDATE locations
        SET
            last_verified_at = NOW(),
            notes = CASE
                      WHEN $1 = '' THEN notes
                      ELSE COALESCE(notes, '')
                           || CASE WHEN notes IS NULL OR notes = '' THEN '' ELSE E'\\n' END
                           || $1
                    END
        WHERE id = $2
        """
    )
    await execute(sql, note_text, int(id))
