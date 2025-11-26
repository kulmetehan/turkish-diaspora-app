from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import yaml

from app.core.logging import get_logger

logger = get_logger()

THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent
BACKEND_DIR = APP_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
NEWS_CITY_CONFIG_PATH = REPO_ROOT / "configs" / "news_cities_template.yml"


@dataclass(frozen=True)
class NewsCity:
    city_key: str
    name: str
    country: str
    province: Optional[str]
    parent_key: Optional[str]
    population: Optional[int]
    lat: Optional[float]
    lng: Optional[float]
    metadata: Mapping[str, Any]

    @property
    def country_code(self) -> str:
        return self.country.strip().lower()

    @property
    def language(self) -> str:
        return "nl" if self.country_code == "nl" else "tr"

    @property
    def legacy_key(self) -> str:
        raw = str(self.metadata.get("legacy_key") or "").strip().lower()
        if raw:
            return raw
        parts = self.city_key.split("-", 1)
        return parts[1] if len(parts) > 1 else self.city_key

    @property
    def google_news_query(self) -> str:
        """
        Preferred Google News query string for this city.
        Falls back to a country-specific default when metadata is absent.
        """
        custom = str(self.metadata.get("google_news_query") or "").strip()
        if custom:
            return custom
        return _default_google_news_query(self)


class _CatalogState:
    __slots__ = ["mtime", "catalog", "index", "alias_index", "defaults", "all_cities"]

    def __init__(
        self,
        *,
        mtime: float,
        catalog: Dict[str, List[NewsCity]],
        index: Dict[str, NewsCity],
        alias_index: Dict[str, NewsCity],
        defaults: Dict[str, List[str]],
        all_cities: List[NewsCity],
    ) -> None:
        self.mtime = mtime
        self.catalog = catalog
        self.index = index
        self.alias_index = alias_index
        self.defaults = defaults
        self.all_cities = all_cities


_CITY_CACHE: Dict[Path, _CatalogState] = {}


def get_city_config(path: Optional[Path] = None) -> Dict[str, List[NewsCity]]:
    state = _load_city_catalog(path)
    return {country: list(cities) for country, cities in state.catalog.items()}


def list_news_cities(country: Optional[str] = None, *, path: Optional[Path] = None) -> List[NewsCity]:
    state = _load_city_catalog(path)
    if not country:
        return list(state.all_cities)
    normalized = country.strip().lower()
    return list(state.catalog.get(normalized, []))


def get_default_cities(path: Optional[Path] = None) -> Dict[str, List[NewsCity]]:
    state = _load_city_catalog(path)
    result: Dict[str, List[NewsCity]] = {}
    for country, keys in state.defaults.items():
        entries = [state.index[key] for key in keys if key in state.index]
        # Fallback: if no defaults found, use first 2 cities per country
        if not entries:
            entries = state.catalog.get(country, [])[:2]
        result[country] = entries
    # Ensure nl and tr always have defaults (even if empty lists)
    if "nl" not in result:
        result["nl"] = state.catalog.get("nl", [])[:2]
    if "tr" not in result:
        result["tr"] = state.catalog.get("tr", [])[:2]
    return result


def get_default_city_keys(path: Optional[Path] = None) -> Dict[str, List[str]]:
    state = _load_city_catalog(path)
    result: Dict[str, List[str]] = {}
    for country, keys in state.defaults.items():
        # Filter out keys that don't exist in index
        valid_keys = [key for key in keys if key in state.index]
        result[country] = valid_keys
        # Fallback: if no valid defaults, use first 2 city keys per country
        if not valid_keys:
            fallback_cities = state.catalog.get(country, [])[:2]
            result[country] = [city.city_key for city in fallback_cities]
    # Ensure nl and tr always have keys (even if empty lists)
    if "nl" not in result:
        nl_cities = state.catalog.get("nl", [])[:2]
        result["nl"] = [city.city_key for city in nl_cities]
    if "tr" not in result:
        tr_cities = state.catalog.get("tr", [])[:2]
        result["tr"] = [city.city_key for city in tr_cities]
    return result


def get_city_by_key(city_key: str, *, path: Optional[Path] = None) -> Optional[NewsCity]:
    if not city_key:
        return None
    state = _load_city_catalog(path)
    normalized = city_key.strip().lower()
    return state.alias_index.get(normalized)


def get_city_google_news_query(city_key: str, *, path: Optional[Path] = None) -> str:
    """
    Resolve the Google News query string for a city slug, preferring metadata overrides.
    """
    city = get_city_by_key(city_key, path=path)
    if city:
        return city.google_news_query
    # Fallback to city_key when the entry is unknown.
    return city_key.strip().lower()


def search_news_cities(
    country: Optional[str],
    query: str,
    *,
    limit: int = 10,
    path: Optional[Path] = None,
) -> List[NewsCity]:
    state = _load_city_catalog(path)
    normalized_query = query.strip().lower()
    if not normalized_query:
        return []
    pools: List[NewsCity]
    if country:
        pools = list(state.catalog.get(country.strip().lower(), []))
    else:
        pools = state.all_cities
    matches: List[NewsCity] = []
    for city in pools:
        haystacks = [
            city.name.lower(),
            city.city_key.lower(),
        ]
        if city.province:
            haystacks.append(city.province.lower())
        metadata_name = str(city.metadata.get("display_name") or "").strip().lower()
        if metadata_name:
            haystacks.append(metadata_name)
        legacy = city.legacy_key
        if legacy:
            haystacks.append(legacy)
        if any(normalized_query in value for value in haystacks if value):
            matches.append(city)
        if len(matches) >= limit:
            break
    matches.sort(key=lambda c: (c.country_code, c.name.lower()))
    return matches[:limit]


def clear_news_city_cache() -> None:
    _CITY_CACHE.clear()


def _resolve_path(path: Optional[Path]) -> Path:
    if path is not None:
        return Path(path)
    return NEWS_CITY_CONFIG_PATH


def _load_city_catalog(path: Optional[Path]) -> _CatalogState:
    cfg_path = _resolve_path(path)
    try:
        stat = cfg_path.stat()
    except FileNotFoundError:
        logger.info("news_city_config_missing", path=str(cfg_path))
        return _CITY_CACHE.setdefault(
            cfg_path,
            _CatalogState(
                mtime=0.0,
                catalog={"nl": [], "tr": []},
                index={},
                alias_index={},
                defaults={"nl": [], "tr": []},
                all_cities=[],
            ),
        )

    cached = _CITY_CACHE.get(cfg_path)
    if cached and cached.mtime == stat.st_mtime:
        return cached

    try:
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.warning("news_city_config_parse_error", path=str(cfg_path), error=str(exc))
        return _CITY_CACHE.setdefault(
            cfg_path,
            _CatalogState(
                mtime=stat.st_mtime,
                catalog={"nl": [], "tr": []},
                index={},
                alias_index={},
                defaults={"nl": [], "tr": []},
                all_cities=[],
            ),
        )

    entries = raw.get("cities") or []
    defaults_raw = raw.get("defaults") or {}

    catalog, index, alias_index, all_cities = _coerce_city_entries(entries)
    defaults = _normalize_defaults(defaults_raw, index)

    state = _CatalogState(
        mtime=stat.st_mtime,
        catalog=catalog,
        index=index,
        alias_index=alias_index,
        defaults=defaults,
        all_cities=all_cities,
    )
    _CITY_CACHE[cfg_path] = state
    return state


def _coerce_city_entries(entries) -> Tuple[Dict[str, List[NewsCity]], Dict[str, NewsCity], Dict[str, NewsCity], List[NewsCity]]:
    catalog: Dict[str, List[NewsCity]] = {}
    index: Dict[str, NewsCity] = {}
    alias_index: Dict[str, NewsCity] = {}

    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        city_key = str(entry.get("city_key") or "").strip().lower()
        name = str(entry.get("name") or "").strip()
        country = str(entry.get("country") or "").strip().lower()
        if not city_key or not name or not country:
            logger.warning("news_city_entry_missing_fields", entry=entry)
            continue
        province = _coerce_optional_str(entry.get("province"))
        parent_key = _coerce_optional_str(entry.get("parent_key"))
        population = _coerce_optional_int(entry.get("population"))
        lat = _coerce_optional_float(entry.get("lat"))
        lng = _coerce_optional_float(entry.get("lng"))
        raw_metadata = entry.get("metadata")
        metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}

        city = NewsCity(
            city_key=city_key,
            name=name,
            country=country,
            province=province,
            parent_key=parent_key.lower() if parent_key else None,
            population=population,
            lat=lat,
            lng=lng,
            metadata=metadata,
        )
        catalog.setdefault(country, []).append(city)
        index[city.city_key] = city
        alias_index.setdefault(city.city_key, city)
        legacy = city.legacy_key
        if legacy and legacy not in alias_index:
            alias_index[legacy] = city

    for cities in catalog.values():
        cities.sort(key=lambda c: c.name.lower())
    if "nl" not in catalog:
        catalog["nl"] = []
    if "tr" not in catalog:
        catalog["tr"] = []
    all_cities = sorted(
        (city for cities in catalog.values() for city in cities),
        key=lambda c: (c.country_code, c.name.lower()),
    )
    return catalog, index, alias_index, all_cities


def _normalize_defaults(raw_defaults: Any, index: Dict[str, NewsCity]) -> Dict[str, List[str]]:
    defaults: Dict[str, List[str]] = {}
    if not isinstance(raw_defaults, dict):
        return defaults
    for country, values in raw_defaults.items():
        if not isinstance(values, list):
            continue
        normalized_country = str(country).strip().lower()
        keys: List[str] = []
        for value in values:
            key = str(value or "").strip().lower()
            if key and key in index:
                keys.append(key)
        defaults[normalized_country] = keys
    if "nl" not in defaults:
        defaults["nl"] = []
    if "tr" not in defaults:
        defaults["tr"] = []
    return defaults


def _coerce_optional_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _coerce_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _default_google_news_query(city: NewsCity) -> str:
    country = city.country_code
    if country == "nl":
        suffix = "Nederland"
    elif country == "tr":
        suffix = "Türkiye"
    else:
        suffix = city.country.strip() or city.country_code.upper()
    return f"{city.name} {suffix}".strip()

