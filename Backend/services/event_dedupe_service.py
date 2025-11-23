from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, List, Optional, Sequence, Tuple

from app.core.logging import get_logger
from pydantic import BaseModel, Field
from services.db_service import execute, fetch, fetchrow
from services.openai_service import OpenAIService
class _SimilarityResponse(BaseModel):
    similarity: float = Field(..., ge=0.0, le=1.0)


logger = get_logger()

STATE_SCOPE: Tuple[str, ...] = ("candidate", "verified", "published")
TIME_WINDOW_HOURS = int(os.getenv("EVENT_DEDUPE_TIME_WINDOW_HOURS", "48"))
TITLE_WEIGHT = float(os.getenv("EVENT_DEDUPE_TITLE_WEIGHT", "0.6"))
LOCATION_WEIGHT = float(os.getenv("EVENT_DEDUPE_LOCATION_WEIGHT", "0.2"))
TIME_WEIGHT = float(os.getenv("EVENT_DEDUPE_TIME_WEIGHT", "0.2"))
AI_WEIGHT = float(os.getenv("EVENT_DEDUPE_AI_WEIGHT", "0.25"))
DUPLICATE_SCORE_THRESHOLD = float(os.getenv("EVENT_DEDUPE_SCORE_THRESHOLD", "0.82"))
AI_TRIGGER_THRESHOLD = float(os.getenv("EVENT_DEDUPE_AI_TRIGGER", "0.7"))
ENABLE_AI = os.getenv("EVENT_DEDUPE_AI_ENABLED", "0").lower() in ("1", "true", "yes")


@dataclass
class CandidateContext:
    id: int
    event_source_id: int
    source_key: str
    city_key: Optional[str]
    title: str
    description: Optional[str]
    location_text: Optional[str]
    start_time_utc: datetime
    end_time_utc: Optional[datetime]


@dataclass
class DedupeResult:
    candidate_id: int
    duplicate_of_id: Optional[int]
    score: Optional[float]
    reason: str


def _normalize_text(value: Optional[str]) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def _string_similarity(a: Optional[str], b: Optional[str]) -> float:
    a_norm = _normalize_text(a)
    b_norm = _normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def _time_similarity(a: datetime, b: datetime) -> float:
    delta_seconds = abs((a - b).total_seconds())
    window_seconds = TIME_WINDOW_HOURS * 3600
    if window_seconds <= 0:
        return 0.0
    if delta_seconds >= window_seconds:
        return 0.0
    # Linear decay within window
    return max(0.0, 1.0 - (delta_seconds / window_seconds))


async def _fetch_candidate_context(candidate_id: int) -> Optional[CandidateContext]:
    row = await fetchrow(
        """
        SELECT
            ec.id,
            ec.event_source_id,
            ec.source_key,
            ec.title,
            ec.description,
            ec.location_text,
            ec.start_time_utc,
            ec.end_time_utc,
            es.city_key
        FROM events_candidate ec
        LEFT JOIN event_sources es ON es.id = ec.event_source_id
        WHERE ec.id = $1
        """,
        candidate_id,
    )
    if not row:
        return None
    return CandidateContext(
        id=row["id"],
        event_source_id=row["event_source_id"],
        source_key=row["source_key"],
        city_key=row.get("city_key"),
        title=row["title"],
        description=row.get("description"),
        location_text=row.get("location_text"),
        start_time_utc=row["start_time_utc"],
        end_time_utc=row.get("end_time_utc"),
    )


async def _fetch_potential_duplicates(ctx: CandidateContext) -> List[CandidateContext]:
    window_seconds = TIME_WINDOW_HOURS * 3600
    rows = await fetch(
        """
        SELECT
            ec.id,
            ec.event_source_id,
            ec.source_key,
            ec.title,
            ec.description,
            ec.location_text,
            ec.start_time_utc,
            ec.end_time_utc,
            es.city_key
        FROM events_candidate ec
        LEFT JOIN event_sources es ON es.id = ec.event_source_id
        WHERE ec.id <> $1
          AND (ec.duplicate_of_id IS NULL)
          AND ec.state = ANY($2::text[])
          AND ($3::text IS NULL AND es.city_key IS NULL OR es.city_key = $3)
          AND ABS(EXTRACT(EPOCH FROM (ec.start_time_utc - $4))) <= $5
        """,
        ctx.id,
        list(STATE_SCOPE),
        ctx.city_key,
        ctx.start_time_utc,
        window_seconds,
    )
    contexts: List[CandidateContext] = []
    for row in rows or []:
        contexts.append(
            CandidateContext(
                id=row["id"],
                event_source_id=row["event_source_id"],
                source_key=row["source_key"],
                city_key=row.get("city_key"),
                title=row["title"],
                description=row.get("description"),
                location_text=row.get("location_text"),
                start_time_utc=row["start_time_utc"],
                end_time_utc=row.get("end_time_utc"),
            )
        )
    return contexts


def _aggregate_score(
    ctx: CandidateContext,
    other: CandidateContext,
) -> Tuple[float, float, float]:
    title_score = _string_similarity(ctx.title, other.title)
    location_score = _string_similarity(ctx.location_text, other.location_text)
    time_score = _time_similarity(ctx.start_time_utc, other.start_time_utc)
    return title_score, location_score, time_score


async def _ai_similarity(ctx: CandidateContext, other: CandidateContext) -> Optional[float]:
    if not ENABLE_AI:
        return None
    payload = (
        f"Event A: title={ctx.title}; description={ctx.description or ''}\n"
        f"Event B: title={other.title}; description={other.description or ''}"
    )
    try:
        client = OpenAIService()
        parsed, _meta = client.generate_json(
            system_prompt=(
                "Compare two diaspora events and return a JSON object "
                'with {"similarity": float between 0 and 1}. '
                "Higher similarity means duplicates."
            ),
            user_prompt=payload,
            response_model=_SimilarityResponse,
            action_type="events.dedupe",
            event_raw_id=None,
        )
        return float(parsed.similarity)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("event_dedupe_ai_failed", candidate_a=ctx.id, candidate_b=other.id, error=str(exc))
    return None


async def run_dedupe(candidate_id: int) -> DedupeResult:
    ctx = await _fetch_candidate_context(candidate_id)
    if ctx is None:
        return DedupeResult(candidate_id=candidate_id, duplicate_of_id=None, score=None, reason="missing_candidate")

    if ctx.city_key is None:
        return DedupeResult(candidate_id=candidate_id, duplicate_of_id=None, score=None, reason="missing_city")

    potential = await _fetch_potential_duplicates(ctx)
    if not potential:
        await _mark_canonical(candidate_id)
        return DedupeResult(candidate_id=candidate_id, duplicate_of_id=None, score=None, reason="no_candidates")

    best_score = 0.0
    best_match: Optional[CandidateContext] = None
    best_components: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    for other in potential:
        if other.id == candidate_id:
            continue
        title_score, location_score, time_score = _aggregate_score(ctx, other)
        composite = (
            TITLE_WEIGHT * title_score
            + LOCATION_WEIGHT * location_score
            + TIME_WEIGHT * time_score
        )
        if composite > best_score:
            best_score = composite
            best_match = other
            best_components = (title_score, location_score, time_score)

    ai_score = None
    if (
        best_match
        and best_score >= AI_TRIGGER_THRESHOLD
        and best_score < DUPLICATE_SCORE_THRESHOLD
    ):
        ai_score = await _ai_similarity(ctx, best_match)
        if ai_score is not None:
            best_score = min(1.0, (best_score * (1 - AI_WEIGHT)) + (ai_score * AI_WEIGHT))

    if best_match and best_score >= DUPLICATE_SCORE_THRESHOLD:
        await _mark_duplicate(candidate_id, best_match.id, best_score)
        logger.info(
            "event_dedupe_marked_duplicate",
            candidate_id=candidate_id,
            duplicate_of=best_match.id,
            score=best_score,
            components=best_components,
            ai_score=ai_score,
        )
        return DedupeResult(
            candidate_id=candidate_id,
            duplicate_of_id=best_match.id,
            score=best_score,
            reason="duplicate",
        )

    await _mark_canonical(candidate_id)
    logger.info(
        "event_dedupe_kept_canonical",
        candidate_id=candidate_id,
        score=best_score,
        components=best_components,
        ai_score=ai_score,
    )
    return DedupeResult(candidate_id=candidate_id, duplicate_of_id=None, score=best_score, reason="canonical")


async def _mark_duplicate(candidate_id: int, canonical_id: int, score: float) -> None:
    await execute(
        """
        UPDATE events_candidate
        SET duplicate_of_id = $2,
            duplicate_score = $3,
            updated_at = $4
        WHERE id = $1
        """,
        candidate_id,
        canonical_id,
        score,
        datetime.now(timezone.utc),
    )


async def _mark_canonical(candidate_id: int) -> None:
    await execute(
        """
        UPDATE events_candidate
        SET duplicate_of_id = NULL,
            duplicate_score = NULL,
            updated_at = $2
        WHERE id = $1
        """,
        candidate_id,
        datetime.now(timezone.utc),
    )


