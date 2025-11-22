# services/db_service.py
from __future__ import annotations

import os
import json
from typing import Any, AsyncIterator, Dict, List, Optional
import asyncio
from contextlib import asynccontextmanager
from time import monotonic
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

APPLICATION_NAME = "tda-backend"
STATEMENT_TIMEOUT_MS = int(os.getenv("STATEMENT_TIMEOUT_MS", "30000"))
IDLE_IN_TX_TIMEOUT_MS = int(os.getenv("IDLE_IN_TX_TIMEOUT_MS", "60000"))
LOCK_TIMEOUT_MS = int(os.getenv("LOCK_TIMEOUT_MS", "5000"))
DB_POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
DB_POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "4"))
DEFAULT_QUERY_TIMEOUT_MS = int(os.getenv("DEFAULT_QUERY_TIMEOUT_MS", "30000"))
SLOW_QUERY_THRESHOLD_MS = 1_000  # 1 second

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

        logger.info(
            "db_pool_initializing",
            extra={
                "dsn_host": urlparse(final_dsn).hostname if final_dsn else None,
                "dsn_port": urlparse(final_dsn).port if final_dsn else None,
                "application_name": APPLICATION_NAME,
            },
        )
        _pool = await asyncpg.create_pool(
            dsn=final_dsn,
            min_size=DB_POOL_MIN_SIZE,
            max_size=DB_POOL_MAX_SIZE,
            command_timeout=60,
            timeout=60,
            statement_cache_size=0,
            max_inactive_connection_lifetime=30,
            server_settings={
                "application_name": APPLICATION_NAME,
                "statement_timeout": str(STATEMENT_TIMEOUT_MS),
                "idle_in_transaction_session_timeout": str(IDLE_IN_TX_TIMEOUT_MS),
                "lock_timeout": str(LOCK_TIMEOUT_MS),
            },
        )
        return _pool

async def init_db_pool() -> asyncpg.Pool:
    # Backwards-compatible wrapper; safe to call multiple times
    return await ensure_pool()

async def _execute_with_timing(
    conn: asyncpg.Connection,
    method: str,
    query: str,
    *args: Any,
    timeout: Optional[float] = None,
) -> Any:
    if not isinstance(conn, asyncpg.Connection):
        raise TypeError("conn must be an asyncpg.Connection instance")
    if not isinstance(method, str):
        raise TypeError("method must be a string")
    if not isinstance(query, str):
        raise TypeError("query must be a string")

    start_ms = monotonic() * 1000
    try:
        func = getattr(conn, method)
        effective_timeout = (
            timeout if timeout is not None else DEFAULT_QUERY_TIMEOUT_MS / 1000
        )
        return await func(query, *args, timeout=effective_timeout)
    finally:
        duration_ms = (monotonic() * 1000) - start_ms
        if duration_ms >= SLOW_QUERY_THRESHOLD_MS:
            logger.warning(
                "db_slow_query",
                extra={
                    "duration_ms": round(duration_ms, 2),
                    "method": method,
                    "arg_count": len(args),
                    "query_snippet": query.strip().split("\n")[0][:200],
                },
            )

@asynccontextmanager
async def connection() -> AsyncIterator[asyncpg.Connection]:
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        yield conn

async def fetch(
    query: str,
    *args: Any,
    timeout: Optional[float] = None,
) -> List[asyncpg.Record]:
    async with connection() as conn:
        return await _execute_with_timing(conn, "fetch", query, *args, timeout=timeout)

async def fetchrow(
    query: str,
    *args: Any,
    timeout: Optional[float] = None,
) -> Optional[asyncpg.Record]:
    async with connection() as conn:
        return await _execute_with_timing(
            conn, "fetchrow", query, *args, timeout=timeout
        )

async def fetchval(query: str, *args: Any) -> Any:
    async with connection() as conn:
        return await _execute_with_timing(conn, "fetchval", query, *args)

async def execute(
    query: str,
    *args: Any,
    timeout: Optional[float] = None,
) -> str:
    async with connection() as conn:
        return await _execute_with_timing(conn, "execute", query, *args, timeout=timeout)

@asynccontextmanager
async def run_in_transaction(
    *,
    isolation: Optional[str] = None,
    readonly: bool = False,
) -> AsyncIterator[asyncpg.Connection]:
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        tx = conn.transaction(isolation=isolation, readonly=readonly)
        await tx.start()
        try:
            yield conn
        except Exception:
            await tx.rollback()
            raise
        else:
            await tx.commit()

async def fetch_with_conn(
    conn: asyncpg.Connection,
    query: str,
    *args: Any,
    timeout: Optional[float] = None,
) -> List[asyncpg.Record]:
    return await _execute_with_timing(conn, "fetch", query, *args, timeout=timeout)

async def fetchrow_with_conn(
    conn: asyncpg.Connection,
    query: str,
    *args: Any,
    timeout: Optional[float] = None,
) -> Optional[asyncpg.Record]:
    return await _execute_with_timing(
        conn, "fetchrow", query, *args, timeout=timeout
    )

async def execute_with_conn(
    conn: asyncpg.Connection,
    query: str,
    *args: Any,
    timeout: Optional[float] = None,
) -> str:
    return await _execute_with_timing(conn, "execute", query, *args, timeout=timeout)

# --------------------------------------------------------------------
# AI log helper
# --------------------------------------------------------------------
async def ai_log(
    *,
    location_id: Optional[int],
    news_id: Optional[int] = None,
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
                news_id,
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
                $3,
                CAST($4 AS JSONB),
                CAST($5 AS JSONB),
                CAST($6 AS JSONB),
                $7,
                $8,
                $9
            )
            """
        )

        await execute(
            sql,
            location_id,
            news_id,
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
    category: Optional[str],  # Can be None for action="ignore" to preserve existing category
    confidence_score: float,
    reason: Optional[str] = None,
    conn: Optional[asyncpg.Connection] = None,
    allow_resurrection: bool = False,
) -> None:
    """
    Canonical function for updating location classification and state.
    
    This is the single source of truth for state transitions. All workers and
    admin actions should use this function to ensure consistent state management.
    
    **Input Expectations:**
    - `action`: "keep" or "ignore" (case-insensitive)
    - `confidence_score`: Float in range [0.0, 1.0]
    - `category`: Optional string (None for action="ignore" preserves existing category)
    - `reason`: Optional string appended to notes
    
    **State Derivation Rules:**
    - `action="ignore"` → `state="RETIRED"`
    - `action="keep"` + `confidence >= 0.90` → `state="VERIFIED"`
    - `action="keep"` + `0.80 <= confidence < 0.90` → `state="PENDING_VERIFICATION"`
    - `action="keep"` + `confidence < 0.80` → `state="CANDIDATE"`
    
    **No-Downgrade Behavior:**
    - Locations in `VERIFIED` state are never demoted (always stay `VERIFIED`)
    - Locations in `RETIRED` state are never resurrected unless `allow_resurrection=True`
    - This prevents accidental loss of verified data or resurrection of rejected locations
    
    **Side Effects:**
    - Always sets `last_verified_at = NOW()` (even for no-op updates)
    - Appends `reason` to `notes` field (newline-separated)
    - Updates `category` and `confidence_score` fields
    - Clears `is_retired` flag if `allow_resurrection=True` and new state is not RETIRED
    
    **Performance Optimizations:**
    - Uses lightweight UPDATE for VERIFIED→VERIFIED no-op cases (only updates timestamp)
    - Full UPDATE for all state transitions or category/confidence changes
    
    **Usage:**
    - Primary: `verify_locations` worker (promotes CANDIDATE/PENDING_VERIFICATION to VERIFIED)
    - Secondary: `classify_bot` worker (legacy, sets PENDING_VERIFICATION)
    - Admin: Manual classification overrides
    """

    # Fetch current state to enforce no-downgrade/no-resurrection
    row_sql = """
        SELECT state, COALESCE(is_retired, false) AS is_retired, category, confidence_score
        FROM locations
        WHERE id = $1
    """
    if conn is not None:
        row = await fetchrow_with_conn(conn, row_sql, int(id))
    else:
        row = await fetchrow(row_sql, int(id))
    current_state = None
    is_retired = False
    current_category = None
    current_confidence = None
    if row:
        rec = dict(row)
        current_state = (rec.get("state") or "").upper()
        is_retired = bool(rec.get("is_retired"))
        current_category = rec.get("category")
        current_confidence = rec.get("confidence_score")

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
    elif not allow_resurrection and (current_state == "RETIRED" or is_retired):
        final_state = "RETIRED"   # never resurrect RETIRED unless explicitly allowed

    reason_text = reason or ""
    should_clear_retired = (
        allow_resurrection
        and (current_state == "RETIRED" or is_retired)
        and final_state != "RETIRED"
    )

    # Optimize: Use lightweight UPDATE for VERIFIED→VERIFIED no-op cases
    # Only when: state stays VERIFIED, no resurrection, confidence already high
    is_noop_reverify = (
        current_state == "VERIFIED"
        and final_state == "VERIFIED"
        and not should_clear_retired
        and float(confidence_score) >= 0.90
        and (current_confidence is None or float(current_confidence) >= 0.90)
    )

    if is_noop_reverify:
        # Check if category or confidence actually need to change
        category_changes = category is not None and category != current_category
        confidence_changes = abs(float(confidence_score) - (float(current_confidence) if current_confidence is not None else 0.0)) > 0.001
        
        if not category_changes and not confidence_changes:
            # True no-op: only update last_verified_at and notes (if reason provided)
            if reason_text:
                sql_lightweight = """
                    UPDATE locations
                    SET last_verified_at = NOW(),
                        notes = CASE
                                  WHEN $1::text = '' THEN notes
                                  ELSE COALESCE(notes, '')
                                       || CASE WHEN notes IS NULL OR notes = '' THEN '' ELSE E'\\n' END
                                       || $1::text
                                END
                    WHERE id = $2::bigint
                """
                if conn is not None:
                    await execute_with_conn(conn, sql_lightweight, reason_text, int(id))
                else:
                    await execute(sql_lightweight, reason_text, int(id))
            else:
                # Even lighter: just update last_verified_at
                sql_minimal = """
                    UPDATE locations
                    SET last_verified_at = NOW()
                    WHERE id = $1::bigint
                """
                if conn is not None:
                    await execute_with_conn(conn, sql_minimal, int(id))
                else:
                    await execute(sql_minimal, int(id))
            return  # Early exit for true no-op

    # Full UPDATE for all other cases
    # Preserve existing category when new category is None (for action="ignore" cases)
    # All parameters must have explicit type context to avoid AmbiguousParameterError
    sql = (
        """
        UPDATE locations
        SET
            category = CASE 
                         WHEN $1::text IS NOT NULL THEN $1::text
                         ELSE category  -- Preserve existing category when new one is NULL
                       END,
            confidence_score = $2::numeric,
            state = $3::location_state,
            notes = CASE
                      WHEN $4::text = '' THEN notes
                      ELSE COALESCE(notes, '')
                           || CASE WHEN notes IS NULL OR notes = '' THEN '' ELSE E'\\n' END
                           || $4::text
                    END,
            last_verified_at = NOW(),
            is_retired = CASE WHEN $5::boolean THEN false ELSE is_retired END
        WHERE id = $6::bigint
        """
    )

    exec_args = (
        category,  # Can be None to preserve existing category
        float(confidence_score),
        final_state,
        reason_text,
        should_clear_retired,
        int(id),
    )

    if conn is not None:
        await execute_with_conn(conn, sql, *exec_args)
    else:
        await execute(sql, *exec_args)


async def unretire_and_verify(
    *,
    id: int,
    actor: str,
    conn: asyncpg.Connection,
) -> None:
    """
    Convenience helper to resurrect a retired row and stamp it as VERIFIED within an active transaction.
    """
    if conn is None:
        raise ValueError("conn is required for unretire_and_verify")

    row = await fetchrow_with_conn(
        conn,
        """
        SELECT category, confidence_score
        FROM locations
        WHERE id = $1
        """,
        int(id),
    )
    if row is None:
        raise ValueError(f"location {id} not found")

    rec = dict(row)
    category = rec.get("category") or "other"
    raw_confidence = rec.get("confidence_score")
    confidence = float(raw_confidence) if raw_confidence is not None else 0.95
    if confidence < 0.9:
        confidence = 0.9

    await update_location_classification(
        id=int(id),
        action="keep",
        category=category,
        confidence_score=confidence,
        reason=f"admin unretire and verify by {actor}",
        conn=conn,
        allow_resurrection=True,
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
