from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from app.core.logging import get_logger

OTHER_CATEGORY_KEY = "other"
logger = get_logger()

_FALLBACK_CATEGORIES: List[Dict[str, str]] = [
    {"key": "club", "label": "Club"},
    {"key": "theater", "label": "Theater"},
    {"key": "concert", "label": "Concert"},
    {"key": "familie", "label": "Familie"},
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "Infra" / "config" / "event_categories.yml"


def _load_from_disk() -> List[Dict[str, str]]:
    if not CONFIG_PATH.exists():
        logger.warning("event_categories_config_missing", path=str(CONFIG_PATH))
        return []
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("event_categories_config_invalid", error=str(exc))
        return []

    categories = data.get("categories") if isinstance(data, dict) else data
    if not isinstance(categories, list):
        logger.warning("event_categories_config_invalid_structure")
        return []

    sanitized: List[Dict[str, str]] = []
    for entry in categories:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key") or "").strip().lower().replace(" ", "_")
        label = str(entry.get("label") or "").strip() or key.title()
        description = str(entry.get("description") or "").strip()
        if not key:
            continue
        sanitized.append(
            {
                "key": key,
                "label": label,
                "description": description,
            }
        )

    if not sanitized:
        logger.warning("event_categories_config_empty")
    return sanitized


@lru_cache(maxsize=1)
def get_event_categories() -> List[Dict[str, str]]:
    """
    Returns the configured event categories, falling back to the built-in defaults.
    """
    configured = _load_from_disk()
    if configured:
        return configured
    return _FALLBACK_CATEGORIES


def get_event_category_keys() -> List[str]:
    return [entry["key"] for entry in get_event_categories()]


def normalize_event_category_key(raw_value: Optional[str]) -> str:
    """
    Normalize arbitrary strings to canonical category keys, defaulting to 'other'.
    """
    if not raw_value:
        return OTHER_CATEGORY_KEY
    candidate = (
        raw_value.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )
    valid_keys = set(get_event_category_keys())
    return candidate if candidate in valid_keys else OTHER_CATEGORY_KEY


def get_event_category_map() -> Dict[str, Dict[str, str]]:
    """
    Returns a dict keyed by category key for quick lookups.
    """
    return {entry["key"]: entry for entry in get_event_categories()}


