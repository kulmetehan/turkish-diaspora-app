from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from app.models.ai_config import AIConfig

NL_CATEGORIES = {
    "nl_local",
    "nl_national",
    "nl_national_economie",
    "nl_national_sport",
    "nl_national_cultuur",
}
TR_CATEGORIES = {
    "tr_national",
    "tr_national_economie",
    "tr_national_sport",
    "tr_national_magazin",
}
GEO_CATEGORIES = {"geopolitiek", "international"}
LOCAL_TAG = "local"
ORIGIN_TAG = "origin"

NL_PRIORITY_SOURCE_KEYS = {
    "nos_headlines",
    "nos_economie",
    "nos_sport",
    "nos_magazin",
    "nu_headlines",
}
TR_PRIORITY_SOURCE_KEYS = {
    "haberturk_headlines",
    "haberturk_economie",
    "haberturk_sport",
    "haberturk_magazin",
    "trt_headlines",
}
# Note: We intentionally do NOT maintain hard allowlists (NL_ALLOWED_SOURCE_KEYS / TR_ALLOWED_SOURCE_KEYS)
# that block all other sources. Priority keys (NOS/NU, TRT/Habertürk) are treated more leniently
# (can bypass strict scoring), but any NL/TR source from news_sources.yml can appear if it passes
# the normal score + language + category filters. This keeps feeds close to underlying RSS streams.


class FeedType(str, Enum):
    DIASPORA = "diaspora"
    NL = "nl"
    TR = "tr"
    LOCAL = "local"
    ORIGIN = "origin"
    GEO = "geo"


@dataclass(frozen=True)
class FeedThresholds:
    news_diaspora_min_score: float
    news_nl_min_score: float
    news_tr_min_score: float
    news_local_min_score: float
    news_origin_min_score: float
    news_geo_min_score: float


def thresholds_from_config(cfg: AIConfig) -> FeedThresholds:
    return FeedThresholds(
        news_diaspora_min_score=cfg.news_diaspora_min_score,
        news_nl_min_score=cfg.news_nl_min_score,
        news_tr_min_score=cfg.news_tr_min_score,
        news_local_min_score=cfg.news_local_min_score,
        news_origin_min_score=cfg.news_origin_min_score,
        news_geo_min_score=cfg.news_geo_min_score,
    )


def is_in_feed(
    feed: FeedType,
    news_row: Mapping[str, Any],
    source_meta: Optional[Mapping[str, Any]],
    thresholds: FeedThresholds,
) -> bool:
    """Pure helper that determines if a news row belongs in a feed."""
    meta = source_meta or {}
    category = _normalize_category(meta.get("category") or news_row.get("category"))
    language = _normalize_language(meta.get("language") or news_row.get("language"))
    location_tag = _normalize_location_tag(news_row.get("location_tag"))
    source_key = _normalize_source_key(news_row.get("source_key"))
    scores = _extract_scores(news_row)

    if feed == FeedType.DIASPORA:
        return (
            scores["relevance_diaspora"] >= thresholds.news_diaspora_min_score
            and language in {"nl", "tr"}
            and (
                location_tag in {LOCAL_TAG, ORIGIN_TAG}
                or category in NL_CATEGORIES
            )
        )
    if feed == FeedType.NL:
        # Priority sources (NOS/NU) can bypass strict scoring - they just need language/category match
        if source_key in NL_PRIORITY_SOURCE_KEYS:
            return language == "nl" or category in NL_CATEGORIES
        # All other NL sources must pass normal score + language + category filters
        return (
            scores["relevance_nl"] >= thresholds.news_nl_min_score
            and language == "nl"
            and category in NL_CATEGORIES
        )
    if feed == FeedType.TR:
        # Priority sources (TRT/Habertürk) can bypass strict scoring - they just need language/category match
        if source_key in TR_PRIORITY_SOURCE_KEYS:
            return language == "tr" or category in TR_CATEGORIES
        # All other TR sources must pass normal score + language + category filters
        return (
            scores["relevance_tr"] >= thresholds.news_tr_min_score
            and (language == "tr" or category in TR_CATEGORIES)
        )
    if feed == FeedType.LOCAL:
        # LOCAL feeds surface all city-matched Google News items—no relevance gating.
        return location_tag == LOCAL_TAG and category in NL_CATEGORIES
    if feed == FeedType.ORIGIN:
        # ORIGIN feeds surface all origin-tagged items (language/category scoped) without relevance thresholds.
        return location_tag == ORIGIN_TAG and (
            category in TR_CATEGORIES or language == "tr"
        )
    if feed == FeedType.GEO:
        return (
            scores["relevance_geo"] >= thresholds.news_geo_min_score
            and (
                category in GEO_CATEGORIES
                or language in {"en", "fr", "de"}
            )
        )
    return False


def build_feed_filter(
    feed: FeedType,
    thresholds: FeedThresholds,
    categories: Optional[Sequence[str]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Build SQL WHERE fragment + params mirroring `is_in_feed` logic.
    Useful for future feed-specific queries.
    
    Args:
        feed: Feed type
        thresholds: AI thresholds (used for DIASPORA/GEO feeds)
        categories: Optional list of RSS category strings (e.g., ['nl_national_sport'])
    """
    if feed == FeedType.DIASPORA:
        return _build_conditions(
            score=("relevance_diaspora", "diaspora_score", thresholds.news_diaspora_min_score),
            language=("LOWER(COALESCE(language, '')) IN ('nl','tr')"),
            extra=f"(COALESCE(location_tag, '') IN ('local','origin') OR LOWER(COALESCE(category, '')) IN {_categories_sql(NL_CATEGORIES)})",
        )
    if feed == FeedType.NL:
        # Simple filter: no AI score dependency, just language/category/source matching
        # Supports both alias and URL-based source_key values
        nl_sources = _get_nl_source_keys()
        base_sql = (
            "published_at IS NOT NULL "
            "AND LOWER(COALESCE(language, '')) = 'nl' "
            "AND LOWER(COALESCE(source_key, '')) = ANY(%(nl_sources)s)"
        )
        
        if categories:
            # categories already contain RSS category strings like 'nl_national_sport'
            base_sql += " AND LOWER(COALESCE(category, '')) = ANY(%(nl_categories)s)"
            named_params = {
                "nl_sources": nl_sources,
                "nl_categories": [c.lower() for c in categories],
            }
        else:
            # Default: all NL categories
            base_sql += f" AND LOWER(COALESCE(category, '')) IN {_categories_sql(NL_CATEGORIES)}"
            named_params = {"nl_sources": nl_sources}
        
        return base_sql, named_params
    if feed == FeedType.TR:
        # Simple filter: no AI score dependency, just language/category/source matching
        # Supports both alias and URL-based source_key values
        tr_sources = _get_tr_source_keys()
        base_sql = (
            "published_at IS NOT NULL "
            "AND (LOWER(COALESCE(language, '')) = 'tr' "
            "     OR LOWER(COALESCE(category, '')) LIKE 'tr_%') "
            "AND LOWER(COALESCE(source_key, '')) = ANY(%(tr_sources)s)"
        )
        
        if categories:
            base_sql += " AND LOWER(COALESCE(category, '')) = ANY(%(tr_categories)s)"
            named_params = {
                "tr_sources": tr_sources,
                "tr_categories": [c.lower() for c in categories],
            }
        else:
            base_sql += f" AND LOWER(COALESCE(category, '')) IN {_categories_sql(TR_CATEGORIES)}"
            named_params = {"tr_sources": tr_sources}
        
        return base_sql, named_params
    if feed == FeedType.LOCAL:
        sql = (
            "COALESCE(location_tag, '') = 'local' "
            f"AND LOWER(COALESCE(category, '')) IN {_categories_sql(NL_CATEGORIES)}"
        )
        return sql, {}
    if feed == FeedType.ORIGIN:
        sql = (
            "COALESCE(location_tag, '') = 'origin' AND ("
            f"LOWER(COALESCE(category, '')) IN {_categories_sql(TR_CATEGORIES)} "
            "OR LOWER(COALESCE(language, '')) = 'tr'"
            ")"
        )
        return sql, {}
    if feed == FeedType.GEO:
        return _build_conditions(
            score=("relevance_geo", "geo_score", thresholds.news_geo_min_score),
            extra="(LOWER(COALESCE(category, '')) IN ('geopolitiek','international') OR LOWER(COALESCE(language, '')) IN ('en','fr','de'))",
        )
    return "FALSE", {}


def _build_conditions(
    *,
    score: Tuple[str, str, float],
    language: Optional[str] = None,
    extra: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    column, param_name, threshold = score
    conditions = [f"COALESCE({column}, 0) >= %({param_name})s"]
    params: Dict[str, Any] = {param_name: threshold}
    if language:
        conditions.append(language)
    if extra:
        conditions.append(extra)
    return " AND ".join(conditions), params


def _normalize_category(value: Any) -> str:
    return str(value).strip().lower() if isinstance(value, str) else ""


def _normalize_language(value: Any) -> str:
    return str(value).strip().lower() if isinstance(value, str) else ""


def _normalize_location_tag(value: Any) -> str:
    return str(value).strip().lower() if isinstance(value, str) else ""


def _normalize_source_key(value: Any) -> str:
    return str(value).strip().lower() if isinstance(value, str) else ""


def _extract_scores(news_row: Mapping[str, Any]) -> Dict[str, float]:
    return {
        "relevance_diaspora": float(news_row.get("relevance_diaspora") or 0.0),
        "relevance_nl": float(news_row.get("relevance_nl") or 0.0),
        "relevance_tr": float(news_row.get("relevance_tr") or 0.0),
        "relevance_geo": float(news_row.get("relevance_geo") or 0.0),
    }


def _categories_sql(categories: Sequence[str] | set[str]) -> str:
    values = ",".join(f"'{cat}'" for cat in sorted({c.lower() for c in categories}))
    return f"({values})"


def _lowered(values: Sequence[str] | set[str]) -> List[str]:
    return [value.lower() for value in sorted(values)]


def _get_nl_source_keys() -> List[str]:
    """
    Returns list of source_key values (both alias and URL forms) for NL sources.
    Includes NOS variants, NU.nl, and optionally AD Rotterdam.
    All values are lowercase for case-insensitive matching.
    """
    return _lowered([
        # NOS aliases
        "nos_headlines",
        "nos_economie",
        "nos_sport",
        "nos_magazin",
        # NOS URLs
        "https://feeds.nos.nl/nosnieuwsalgemeen",
        "https://feeds.nos.nl/nosnieuwseconomie",
        "https://feeds.nos.nl/nossportalgemeen",
        "https://feeds.nos.nl/nosnieuwscultuurenmedia",
        # NU.nl alias
        "nu_headlines",
        # NU.nl URL
        "https://www.nu.nl/rss/algemeen",
    ])


def _get_tr_source_keys() -> List[str]:
    """
    Returns list of source_key values (both alias and URL forms) for TR sources.
    Includes TRT and Habertürk variants only.
    All values are lowercase for case-insensitive matching.
    """
    return _lowered([
        # TRT alias
        "trt_headlines",
        # TRT URL
        "https://www.trthaber.com/rss/sondakika.rss",
        # Habertürk aliases
        "haberturk_headlines",
        "haberturk_economie",
        "haberturk_sport",
        "haberturk_magazin",
        # Habertürk URLs
        "https://www.haberturk.com/rss/manset.xml",
        "https://www.haberturk.com/rss/ekonomi.xml",
        "https://www.haberturk.com/rss/spor.xml",
        "https://www.haberturk.com/rss/magazin.xml",
    ])

