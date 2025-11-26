"""
News sources registry loader.

Parses configs/news_sources.yml into strongly-typed NewsSource objects with
structlog-backed validation and caching.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

from app.core.logging import get_logger
from app.models.news_city_config import (
    NewsCity,
    get_city_google_news_query,
    get_default_cities,
)

logger = get_logger()

THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent  # Backend/app
BACKEND_DIR = APP_DIR.parent       # Backend
REPO_ROOT = BACKEND_DIR.parent     # repo root
NEWS_SOURCES_YML = REPO_ROOT / "configs" / "news_sources.yml"

ALLOWED_NEWS_CATEGORIES: Sequence[str] = (
    "nl_local",
    "nl_national",
    "nl_national_economie",
    "nl_national_sport",
    "nl_national_cultuur",
    "tr_national",
    "tr_national_economie",
    "tr_national_sport",
    "tr_national_magazin",
    "international",
    "geopolitiek",
)


@dataclass(frozen=True)
class NewsSource:
    """Single RSS/news feed definition."""

    key: str
    name: str
    url: str
    language: str
    category: str
    license: Optional[str]
    redistribution_allowed: Optional[bool]
    robots_policy: Optional[str]
    raw: Dict[str, object]

    def _defaults(self) -> Dict[str, Any]:
        defaults = self.raw.get("_defaults")
        return defaults if isinstance(defaults, dict) else {}

    @property
    def region(self) -> Optional[str]:
        value = self.raw.get("region")
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return None

    @property
    def refresh_minutes(self) -> int:
        raw_value = self.raw.get("refresh_minutes")
        if raw_value is not None:
            try:
                return max(1, int(raw_value))
            except Exception:
                logger.warning(
                    "news_source_invalid_refresh_minutes",
                    source=self.name,
                    value=raw_value,
                )
        defaults = self._defaults()
        default_refresh = defaults.get("refresh_minutes")
        if default_refresh is not None:
            try:
                return max(1, int(default_refresh))
            except Exception:
                logger.warning(
                    "news_source_invalid_default_refresh_minutes",
                    source=self.name,
                    value=default_refresh,
                )
        return 30


def load_news_sources_config(path: Optional[Path] = None) -> Dict[str, object]:
    """
    Load raw YAML config.

    Returns empty dict if file is missing or invalid to keep workers running.
    """
    cfg_path = Path(path) if path else NEWS_SOURCES_YML
    try:
        text = cfg_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("news_sources_config_not_found", path=str(cfg_path))
        return {}
    except OSError as exc:
        logger.error("news_sources_config_read_error", path=str(cfg_path), error=str(exc))
        return {}

    try:
        data = yaml.safe_load(text) or {}
    except Exception as exc:
        logger.error("news_sources_config_parse_error", path=str(cfg_path), error=str(exc))
        return {}

    if not isinstance(data, dict):
        logger.error(
            "news_sources_config_invalid_root",
            path=str(cfg_path),
            root_type=type(data).__name__,
        )
        return {}

    return data


def _normalize_license(value: object) -> Optional[str]:
    if isinstance(value, str):
        value = value.strip()
        if value:
            return value
    return None


def _normalize_redistribution_flag(value: object) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def _normalize_robots_policy(value: object) -> Optional[str]:
    if isinstance(value, str):
        value = value.strip()
        if value:
            return value
    return None


def _validate_source(raw: Dict[str, object]) -> Optional[NewsSource]:
    """Validate raw dict and convert to NewsSource, logging issues."""
    required_keys = ("name", "url", "language", "category")
    missing = [k for k in required_keys if not raw.get(k)]
    if missing:
        logger.warning(
            "news_source_invalid_missing_fields",
            missing=missing,
            raw=raw,
        )
        return None

    category = str(raw.get("category"))
    if category not in ALLOWED_NEWS_CATEGORIES:
        logger.warning(
            "news_source_invalid_category",
            category=category,
            allowed=list(ALLOWED_NEWS_CATEGORIES),
            raw=raw,
        )
        return None

    url = raw.get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        logger.warning("news_source_invalid_url", url=url, raw=raw)
        return None

    name = str(raw.get("name")).strip()
    language = str(raw.get("language")).strip()
    if not name or not language:
        logger.warning(
            "news_source_invalid_empty_field",
            name=name,
            language=language,
            raw=raw,
        )
        return None

    key_raw = raw.get("key")
    if isinstance(key_raw, str) and key_raw.strip():
        source_key = key_raw.strip()
    else:
        source_key = url

    license_value = _normalize_license(raw.get("license"))
    redistribution_flag = _normalize_redistribution_flag(raw.get("redistribution_allowed"))
    robots_policy = _normalize_robots_policy(raw.get("robots_policy"))

    missing_legal: List[str] = []
    if license_value is None:
        missing_legal.append("license")
    if redistribution_flag is None:
        missing_legal.append("redistribution_allowed")
    if robots_policy is None:
        missing_legal.append("robots_policy")
    if missing_legal:
        logger.warning(
            "news_source_missing_legal_metadata",
            source=name,
            missing=missing_legal,
            raw=raw,
        )
    if raw.get("redistribution_allowed") is not None and redistribution_flag is None:
        logger.warning(
            "news_source_invalid_redistribution_flag",
            source=name,
            value=raw.get("redistribution_allowed"),
        )

    return NewsSource(
        key=source_key,
        name=name,
        url=url,
        language=language,
        category=category,
        license=license_value,
        redistribution_allowed=redistribution_flag,
        robots_policy=robots_policy,
        raw=raw,
    )


@lru_cache(maxsize=8)
def _load_sources_from_path(path_str: str) -> List[NewsSource]:
    cfg_path = Path(path_str)
    cfg = load_news_sources_config(cfg_path)
    raw_sources = cfg.get("sources", [])
    defaults = cfg.get("defaults") or {}
    defaults_dict = defaults if isinstance(defaults, dict) else {}

    if not isinstance(raw_sources, list):
        logger.error(
            "news_sources_invalid_sources_type",
            actual_type=type(raw_sources).__name__,
            path=str(cfg_path),
        )
        return []

    result: List[NewsSource] = []
    for idx, raw in enumerate(raw_sources):
        if not isinstance(raw, dict):
            logger.warning(
                "news_source_invalid_entry_type",
                index=idx,
                value_type=type(raw).__name__,
            )
            continue
        enriched_raw: Dict[str, object] = dict(raw)
        enriched_raw["_defaults"] = defaults_dict
        parsed = _validate_source(enriched_raw)
        if parsed:
            result.append(parsed)

    city_config_path = cfg_path.parent / "news_cities_template.yml"
    city_sources = _load_city_feed_sources(city_config_path)
    all_sources = [*result, *city_sources]

    logger.info(
        "news_sources_loaded",
        path=str(cfg_path),
        total=len(all_sources),
    )
    return all_sources


def get_all_news_sources(path: Optional[Path] = None) -> List[NewsSource]:
    """
    Public accessor for all valid news sources.

    Accepts optional path (useful for tests). Results are cached per-path.
    """
    cfg_path = Path(path) if path else NEWS_SOURCES_YML
    sources = _load_sources_from_path(str(cfg_path.resolve()))
    return list(sources)


def clear_news_sources_cache() -> None:
    """Reset LRU cache (useful for tests)."""
    _load_sources_from_path.cache_clear()


def _load_city_feed_sources(city_config_path: Path) -> List[NewsSource]:
    config = get_default_cities(path=city_config_path)
    dynamic_sources: List[NewsSource] = []
    for city_entry in config["nl"]:
        parsed = _build_city_source(city_entry, category="nl_local")
        if parsed:
            dynamic_sources.append(parsed)
    for city_entry in config["tr"]:
        parsed = _build_city_source(city_entry, category="tr_national")
        if parsed:
            dynamic_sources.append(parsed)
    return dynamic_sources


def _build_city_source(entry: NewsCity, *, category: str) -> Optional[NewsSource]:
    query = get_city_google_news_query(entry.city_key)
    url = _build_google_news_url(query, language=entry.language, country=entry.country)
    raw: Dict[str, object] = {
        "key": f"google_news_{entry.city_key}",
        "name": f"Google News – {entry.name}",
        "url": url,
        "language": entry.language,
        "category": category,
        "region": entry.name,
        "license": "google-news",
        "redistribution_allowed": True,
        "robots_policy": "follow",
    }
    parsed = _validate_source(raw)
    return parsed


def _build_google_news_url(query: str, *, language: str, country: str) -> str:
    from urllib.parse import quote_plus

    encoded = quote_plus(query)
    lang = language.lower()
    country_upper = country.upper()
    return (
        "https://news.google.com/rss/search?"
        f"q={encoded}&hl={lang}&gl={country_upper}&ceid={country_upper}:{lang}"
    )

