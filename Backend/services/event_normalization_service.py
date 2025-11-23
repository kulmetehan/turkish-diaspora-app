from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from app.models.ai import _normalize_url
from app.models.event_candidate import EventCandidateCreate
from app.models.event_raw import EventRaw
from app.models.event_sources import EventSource

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class EventNormalizationError(Exception):
    """
    Raised when an EventRaw record cannot be normalized into a candidate row.
    """


def _strip_html(value: str) -> str:
    without_tags = _HTML_TAG_RE.sub(" ", value or "")
    return _WHITESPACE_RE.sub(" ", without_tags).strip()


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = _strip_html(value.strip())
    return cleaned or None


def _normalize_optional_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if any(ch.isspace() for ch in candidate):
        return None
    try:
        return _normalize_url(candidate)
    except Exception:
        return None


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _resolve_title(raw: EventRaw) -> Optional[str]:
    for candidate in (
        raw.title,
        raw.raw_payload.get("title") if isinstance(raw.raw_payload, dict) else None,
    ):
        cleaned = _clean_text(candidate) if isinstance(candidate, str) else None
        if cleaned:
            return cleaned
    return None


def _resolve_description(raw: EventRaw) -> Optional[str]:
    candidates = [
        raw.description,
    ]
    if isinstance(raw.raw_payload, dict):
        candidates.extend(
            [
                raw.raw_payload.get("description"),
                raw.raw_payload.get("summary"),
            ]
        )
    for candidate in candidates:
        cleaned = _clean_text(candidate) if isinstance(candidate, str) else None
        if cleaned:
            return cleaned
    return None


def _resolve_location(raw: EventRaw) -> Optional[str]:
    parts = []
    for candidate in (raw.location_text, raw.venue):
        cleaned = _clean_text(candidate)
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    if not parts and isinstance(raw.raw_payload, dict):
        extra_location = _clean_text(raw.raw_payload.get("location") or raw.raw_payload.get("venue"))
        if extra_location:
            parts.append(extra_location)
    if not parts:
        return None
    return ", ".join(parts)


def _resolve_url(raw: EventRaw) -> Optional[str]:
    candidates = [raw.event_url]
    if isinstance(raw.raw_payload, dict):
        candidates.append(raw.raw_payload.get("url"))
        link = raw.raw_payload.get("link")
        if link:
            candidates.append(link)
    for candidate in candidates:
        normalized = _normalize_optional_url(candidate if isinstance(candidate, str) else None)
        if normalized:
            return normalized
    return None


def normalize_event(raw: EventRaw, source: EventSource) -> EventCandidateCreate:
    """
    Convert an EventRaw record into the canonical EventCandidateCreate payload.

    Raises:
        EventNormalizationError: when mandatory fields are missing (title/start).
    """

    title = _resolve_title(raw)
    if not title:
        raise EventNormalizationError("missing_title")

    if raw.start_at is None:
        raise EventNormalizationError("missing_start_time")

    start_time_utc = _ensure_utc(raw.start_at)
    end_time_utc = _ensure_utc(raw.end_at) if raw.end_at else None

    description = _resolve_description(raw)
    location_text = _resolve_location(raw)
    url = _resolve_url(raw)

    source_key = source.key if source and source.key else str(raw.event_source_id)

    return EventCandidateCreate(
        event_source_id=raw.event_source_id,
        event_raw_id=raw.id,
        title=title,
        description=description,
        start_time_utc=start_time_utc,
        end_time_utc=end_time_utc,
        location_text=location_text,
        url=url,
        source_key=source_key,
        ingest_hash=raw.ingest_hash,
        state="candidate",
    )


