"""
News city tags registry loader.

Provides access to NL/TR city alias lists for the news location intelligence layer.
The structure mirrors the pattern used by `app.models.news_sources`.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import unicodedata
import textwrap

import yaml

from app.core.logging import get_logger

logger = get_logger()

THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent  # Backend/app
BACKEND_DIR = APP_DIR.parent       # Backend
REPO_ROOT = BACKEND_DIR.parent     # repo root
NEWS_CITY_TAGS_YML = REPO_ROOT / "configs" / "news_city_tags.yml"

SUPPORTED_COUNTRIES = ("nl", "tr")


@dataclass(frozen=True)
class CityTag:
    """Represents a single city definition plus all normalized aliases."""

    city_key: str
    country: str
    city_name: str
    aliases: Tuple[str, ...]


@dataclass(frozen=True)
class CityMatch:
    """Return type for match_city."""

    city_key: str
    country: str
    city_name: str
    alias: str


def _normalize_yaml_text(value: str) -> str:
    lines = value.splitlines()
    non_empty = [(idx, line) for idx, line in enumerate(lines) if line.strip()]
    if not non_empty:
        return value

    first_idx, first_line = non_empty[0]
    base_indent = len(first_line) - len(first_line.lstrip())
    other_indents = [len(line) - len(line.lstrip()) for _, line in non_empty[1:]]

    if other_indents:
        min_other = min(other_indents)
        if min_other > base_indent and all(indent >= min_other for indent in other_indents):
            pad = min_other - base_indent
            lines[first_idx] = " " * pad + first_line

    return textwrap.dedent("\n".join(lines))


def _read_config(path: Path) -> Dict[str, object]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("news_city_tags_config_not_found", path=str(path))
        return {}
    except OSError as exc:  # pragma: no cover - defensive
        logger.error("news_city_tags_config_read_error", path=str(path), error=str(exc))
        return {}

    try:
        normalized = _normalize_yaml_text(text)
        data = yaml.safe_load(normalized) or {}
    except Exception as exc:
        logger.error("news_city_tags_config_parse_error", path=str(path), error=str(exc))
        raise

    if not isinstance(data, dict):
        logger.error(
            "news_city_tags_config_invalid_root",
            path=str(path),
            root_type=type(data).__name__,
        )
        raise ValueError("news_city_tags config root must be a mapping")
    return data


def _normalize_alias(value: str) -> str:
    """
    Normalize aliases and search text using NFKD + casefold + whitespace collapse.
    """
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKD", value.strip().casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    sanitized = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(sanitized.split())


def _coerce_aliases(entry: Dict[str, object]) -> List[str]:
    raw_aliases = entry.get("aliases") or []
    aliases: List[str] = []
    if isinstance(raw_aliases, list):
        for candidate in raw_aliases:
            if isinstance(candidate, str):
                norm = _normalize_alias(candidate)
                if norm:
                    aliases.append(norm)
    return aliases


def _validate_city(country: str, entry: Dict[str, object]) -> Optional[CityTag]:
    city_key = str(entry.get("city_key") or "").strip()
    city_name = str(entry.get("city_name") or "").strip() or city_key
    aliases = _coerce_aliases(entry)

    if not city_key:
        logger.warning("news_city_tag_missing_key", country=country, entry=entry)
        return None

    if not aliases:
        # Always include at least the normalized city name
        fallback = _normalize_alias(city_name)
        if fallback:
            aliases = [fallback]
        else:
            logger.warning("news_city_tag_missing_aliases", country=country, entry=entry)
            return None

    return CityTag(
        city_key=city_key,
        country=country,
        city_name=city_name or city_key,
        aliases=tuple(dict.fromkeys(aliases)),  # dedupe while preserving order
    )


@lru_cache(maxsize=4)
def _load_city_tags_from_path(path_str: str) -> Dict[str, List[CityTag]]:
    path = Path(path_str)
    data = _read_config(path)
    result: Dict[str, List[CityTag]] = {country: [] for country in SUPPORTED_COUNTRIES}

    for country in SUPPORTED_COUNTRIES:
        section = data.get(country)
        if not isinstance(section, list):
            continue
        for entry in section:
            if not isinstance(entry, dict):
                logger.warning("news_city_tag_invalid_entry", country=country, entry=entry)
                continue
            parsed = _validate_city(country, entry)
            if parsed:
                result[country].append(parsed)
    return result


def clear_city_tags_cache() -> None:
    _load_city_tags_from_path.cache_clear()


def _get_city_tags(country: str, path: Optional[Path] = None) -> List[CityTag]:
    key = country.strip().lower()
    if key not in SUPPORTED_COUNTRIES:
        return []
    cfg_path = Path(path) if path else NEWS_CITY_TAGS_YML
    tags_by_country = _load_city_tags_from_path(str(cfg_path.resolve()))
    return list(tags_by_country.get(key, []))


def get_aliases(country: str, path: Optional[Path] = None) -> Dict[str, CityTag]:
    """
    Return {alias: CityTag} for a specific country.
    """
    mapping: Dict[str, CityTag] = {}
    for tag in _get_city_tags(country, path):
        for alias in tag.aliases:
            mapping[alias] = tag
    return mapping


def _normalize_text(value: str) -> str:
    normalized = _normalize_alias(value)
    return f" {normalized} " if normalized else ""


def match_city(
    text: Optional[str],
    countries: Optional[Sequence[str]] = None,
    path: Optional[Path] = None,
) -> Optional[CityMatch]:
    """
    Search for the first matching alias inside the provided text.

    Args:
        text: Article text (title/summary/etc.)
        countries: Optional subset, defaults to ('nl', 'tr')
        path: Optional override for tests
    """
    if not text:
        return None

    normalized_text = _normalize_text(text)
    if not normalized_text:
        return None

    target_countries: Iterable[str] = countries or SUPPORTED_COUNTRIES
    for country in target_countries:
        alias_map = get_aliases(country, path=path)
        for alias, tag in alias_map.items():
            if f" {alias} " in normalized_text:
                return CityMatch(
                    city_key=tag.city_key,
                    country=tag.country,
                    city_name=tag.city_name,
                    alias=alias,
                )
    return None

