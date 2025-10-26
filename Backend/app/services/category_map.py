from __future__ import annotations

from typing import Dict, List


# Canonical category map with friendly labels and known matches
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


# Precompute a lookup from normalized raw values -> canonical key
_MATCH_LOOKUP: Dict[str, str] = {}
for key, cfg in CATEGORY_MAP.items():
    # canonical key itself should also match
    _MATCH_LOOKUP[_slugify(key)] = key
    for alias in (cfg.get("match") or []):
        _MATCH_LOOKUP[_slugify(str(alias))] = key


def normalize_category(raw: str) -> dict:
    """
    Input: raw category from DB (locations.category).
    Output dict:
      {
        "category_raw": <original>,
        "category_key": <canonical key or fallback>,
        "category_label": <nice label or fallback>,
      }
    """
    original = raw if isinstance(raw, str) else ("" if raw is None else str(raw))
    needle = _slugify(original)

    key = _MATCH_LOOKUP.get(needle)

    if key is not None:
        label = str(CATEGORY_MAP.get(key, {}).get("label") or _titlecase_label(key))
        return {
            "category_raw": original,
            "category_key": key,
            "category_label": label,
        }

    # Fallback: derive from raw
    fallback_key = _slugify(original)
    fallback_label = _titlecase_label(original)
    return {
        "category_raw": original,
        "category_key": fallback_key,
        "category_label": fallback_label,
    }


