from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Load categories.yml
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent  # Backend/app
BACKEND_DIR = APP_DIR.parent  # Backend
REPO_ROOT = BACKEND_DIR.parent  # root
CATEGORIES_YML = REPO_ROOT / "Infra" / "config" / "categories.yml"

# Legacy fallback map (used if YAML unavailable)
CATEGORY_MAP: Dict[str, Dict[str, List[str] | str]] = {
    "supermarket": {
        "label": "Supermarkt",
        "match": [
            "supermarket",
            "bakkal/supermarket",
            "bakkal",
            "turkse supermarkt",
            "grocery",
            "grocery_store",
            "grocery store",
        ],
    },
    "barber": {
        "label": "Barber",
        "match": [
            "barber",
            "barbershop",
            "kapper",
            "haarmode",
            "hair salon",
            "hairdresser",
        ],
    },
    "bakery": {
        "label": "Bakkerij",
        "match": [
            "bakery",
            "bakkerij",
        ],
    },
    "fast_food": {
        "label": "Fastfood",
        "match": [
            "fast_food",
            "fast food",
            "snackbar",
            "dönerzaak",
            "doner",
            "kebab",
            "shoarma",
        ],
    },
    "travel_agency": {
        "label": "Reisbureau",
        "match": [
            "travel_agency",
            "travel agency",
            "reisbureau",
            "turkish travel agency",
        ],
    },
    "mosque": {
        "label": "Moskee",
        "match": [
            "mosque",
            "moskee",
            "camii",
        ],
    },
}

# Cached YAML data
_YAML_CATEGORIES: Optional[Dict[str, Any]] = None
_YAML_LOOKUP: Optional[Dict[str, str]] = None  # alias -> canonical key
_YAML_LABELS: Optional[Dict[str, str]] = None  # canonical key -> label


def _load_categories_config() -> Dict[str, Any]:
    """Load categories from YAML file, with fallback to empty dict."""
    if not CATEGORIES_YML.exists():
        return {}
    try:
        with open(CATEGORIES_YML, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("categories", {})
    except Exception:
        return {}


def _build_yaml_lookup() -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Build lookup maps from YAML:
    - alias_lookup: normalized alias -> canonical key
    - label_lookup: canonical key -> label
    """
    categories = _load_categories_config()
    alias_lookup: Dict[str, str] = {}
    label_lookup: Dict[str, str] = {}
    
    for canonical_key, cat_def in categories.items():
        if not isinstance(cat_def, dict):
            continue
        
        # Store label
        label = cat_def.get("label") or _titlecase_label(canonical_key)
        label_lookup[canonical_key] = str(label)
        
        # Canonical key itself maps to itself
        alias_lookup[_slugify(canonical_key)] = canonical_key
        
        # All aliases map to canonical key
        aliases = cat_def.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                if alias:
                    alias_lookup[_slugify(str(alias))] = canonical_key
        
        # Google types can also be aliases (optional)
        google_types = cat_def.get("google_types", [])
        if isinstance(google_types, list):
            for gt in google_types:
                if gt:
                    alias_lookup[_slugify(str(gt))] = canonical_key
    
    return alias_lookup, label_lookup


def _get_yaml_data() -> Tuple[Dict[str, str], Dict[str, str]]:
    """Get cached or build YAML lookup data."""
    global _YAML_LOOKUP, _YAML_LABELS
    if _YAML_LOOKUP is None or _YAML_LABELS is None:
        _YAML_LOOKUP, _YAML_LABELS = _build_yaml_lookup()
    return _YAML_LOOKUP, _YAML_LABELS


def clear_category_map_cache() -> None:
    """Clear cached YAML lookup data (useful after YAML changes)."""
    global _YAML_LOOKUP, _YAML_LABELS
    _YAML_LOOKUP = None
    _YAML_LABELS = None


def _slugify(value: str) -> str:
    """
    Minimal slugify for category keys:
    - lowercase
    - trim
    - replace "/" and whitespace with "_"
    - collapse repeating underscores
    - keep ascii letters/digits/underscore only
    """
    s = (value or "").strip().lower()
    # normalize separators
    s = s.replace("/", "_").replace(" ", "_")
    # collapse repeats
    while "__" in s:
        s = s.replace("__", "_")
    # keep only [a-z0-9_]
    out = []
    for ch in s:
        if ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == "_":
            out.append(ch)
    return "".join(out).strip("_") or "other"


def _titlecase_label(value: str) -> str:
    """
    Human label from raw string:
    - split on "/" and "_"
    - join with single space
    - capitalize first letter of each token
    """
    s = (value or "").strip()
    if not s:
        return "Overig"
    parts: List[str] = []
    # first replace separators with space, then split
    tmp = s.replace("/", " ").replace("_", " ")
    for token in tmp.split():
        if not token:
            continue
        parts.append(token[:1].upper() + token[1:].lower())
    return " ".join(parts) if parts else "Overig"


# Legacy lookup (used if YAML unavailable)
_LEGACY_MATCH_LOOKUP: Dict[str, str] = {}
for key, cfg in CATEGORY_MAP.items():
    # canonical key itself should also match
    _LEGACY_MATCH_LOOKUP[_slugify(key)] = key
    for alias in (cfg.get("match") or []):
        _LEGACY_MATCH_LOOKUP[_slugify(str(alias))] = key


def normalize_category(raw: str) -> dict:
    """
    Input: raw category from DB (locations.category) or AI output.
    Output dict:
      {
        "category_raw": <original>,
        "category_key": <canonical key or None if unmappable>,
        "category_label": <nice label or fallback>,
      }
    
    Uses categories.yml as primary source, falls back to legacy CATEGORY_MAP if YAML unavailable.
    """
    original = raw if isinstance(raw, str) else ("" if raw is None else str(raw))
    if not original or not original.strip():
        return {
            "category_raw": original,
            "category_key": None,
            "category_label": "Overig",
        }
    
    needle = _slugify(original)
    
    # Try YAML first
    yaml_lookup, yaml_labels = _get_yaml_data()
    if yaml_lookup:
        canonical_key = yaml_lookup.get(needle)
        if canonical_key:
            label = yaml_labels.get(canonical_key, _titlecase_label(canonical_key))
            return {
                "category_raw": original,
                "category_key": canonical_key,
                "category_label": str(label),
            }
    
    # Fallback to legacy map
    legacy_key = _LEGACY_MATCH_LOOKUP.get(needle)
    if legacy_key:
        label = str(CATEGORY_MAP.get(legacy_key, {}).get("label") or _titlecase_label(legacy_key))
        return {
            "category_raw": original,
            "category_key": legacy_key,
            "category_label": label,
        }
    
    # Unmappable: return None for key so caller can fall back to "other"
    fallback_key = _slugify(original)
    fallback_label = _titlecase_label(original)
    return {
        "category_raw": original,
        "category_key": None,  # Signal unmappable
        "category_label": fallback_label,
    }


