from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import unicodedata

from app.models.news_city_tags import get_aliases

CountryCode = str

LOCAL_COUNTRY: CountryCode = "nl"
ORIGIN_COUNTRY: CountryCode = "tr"

TAG_LOCAL = "local"
TAG_ORIGIN = "origin"
TAG_NONE = "none"


def _normalize_text_to_tokens(value: Optional[str]) -> List[str]:
    if not value:
        return []
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    sanitized = "".join(ch if ch.isalnum() else " " for ch in text)
    return [token for token in sanitized.split() if token]


def _normalize_country(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if lowered in (LOCAL_COUNTRY, ORIGIN_COUNTRY):
        return lowered
    return None


def _clamp_confidence(value: Any, default: float = 0.5) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, num))


def _coerce_article_text(parts: Sequence[Optional[str]]) -> str:
    tokens = [segment.strip() for segment in parts if isinstance(segment, str) and segment.strip()]
    return " ".join(tokens)


def _extract_ai_matches(ai_mentions: Sequence[Any]) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for mention in ai_mentions or []:
        payload: Dict[str, Any]
        if hasattr(mention, "model_dump"):
            payload = mention.model_dump()
        elif isinstance(mention, dict):
            payload = mention
        else:
            continue

        city_key = str(payload.get("city_key") or "").strip()
        country = _normalize_country(payload.get("country"))
        if not city_key or not country:
            continue

        matches.append(
            {
                "city_key": city_key,
                "country": country,
                "confidence": _clamp_confidence(payload.get("confidence"), default=payload.get("confidence", 0.6) or 0.6),
                "source": "ai",
            }
        )
    return matches


def _extract_text_matches(text: str, *, config_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    tokens = _normalize_text_to_tokens(text)
    if not tokens:
        return []

    normalized_text = f" {' '.join(tokens)} "
    matches: List[Dict[str, Any]] = []

    for country in (LOCAL_COUNTRY, ORIGIN_COUNTRY):
        alias_map = get_aliases(country, path=config_path)
        confidence = 0.8 if country == LOCAL_COUNTRY else 0.7
        for alias, tag in alias_map.items():
            if not alias:
                continue

            found = False
            for token in tokens:
                if token == alias or token.startswith(alias):
                    found = True
                    matched_token = token
                    break

            if not found and f" {alias} " in normalized_text:
                found = True
                matched_token = alias

            if found:
                matches.append(
                    {
                        "city_key": tag.city_key,
                        "country": tag.country,
                        "confidence": confidence,
                        "source": "text",
                        "alias": alias,
                        "token": matched_token,
                    }
                )
    return matches


def _dedupe_matches(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[Tuple[str, str, str, Optional[str]]] = set()
    ordered: List[Dict[str, Any]] = []
    for match in matches:
        key = (
            match.get("source", ""),
            match.get("country", ""),
            match.get("city_key", ""),
            match.get("alias"),
        )
        if key in seen:
            continue
        seen.add(key)
        ordered.append(match)
    return ordered


def _compute_tag(matches: Sequence[Dict[str, Any]]) -> str:
    has_local = any(m.get("country") == LOCAL_COUNTRY for m in matches)
    has_origin = any(m.get("country") == ORIGIN_COUNTRY for m in matches)
    if has_local and not has_origin:
        return TAG_LOCAL
    if has_origin and not has_local:
        return TAG_ORIGIN
    return TAG_NONE


def derive_location_tag(
    *,
    title: Optional[str],
    summary: Optional[str],
    content: Optional[str],
    ai_mentions: Optional[Sequence[Any]],
    config_path: Optional[Path] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Combine AI signals and deterministic alias matching to derive the location tag.

    Returns:
        (location_tag, context_dict)
    """
    article_text = _coerce_article_text((title, summary, content))
    matches = _extract_ai_matches(ai_mentions or [])
    matches.extend(_extract_text_matches(article_text, config_path=config_path))
    matches = _dedupe_matches(matches)
    tag = _compute_tag(matches)
    return tag, {"matches": matches}

