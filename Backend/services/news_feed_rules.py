from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Tuple

from app.models.ai_config import AIConfig

NL_CATEGORIES = {"nl_local", "nl_national"}
TR_CATEGORIES = {"tr_national"}
GEO_CATEGORIES = {"geopolitiek", "international"}
LOCAL_TAG = "local"
ORIGIN_TAG = "origin"


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
        return (
            scores["relevance_nl"] >= thresholds.news_nl_min_score
            and language == "nl"
            and category in NL_CATEGORIES
        )
    if feed == FeedType.TR:
        return (
            scores["relevance_tr"] >= thresholds.news_tr_min_score
            and (language == "tr" or category in TR_CATEGORIES)
        )
    if feed == FeedType.LOCAL:
        return (
            location_tag == LOCAL_TAG
            and scores["relevance_nl"] >= thresholds.news_local_min_score
            and category in NL_CATEGORIES
        )
    if feed == FeedType.ORIGIN:
        return location_tag == ORIGIN_TAG and (
            scores["relevance_tr"] >= thresholds.news_origin_min_score
            or category in TR_CATEGORIES
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


def build_feed_filter(feed: FeedType, thresholds: FeedThresholds) -> Tuple[str, Dict[str, Any]]:
    """
    Build SQL WHERE fragment + params mirroring `is_in_feed` logic.
    Useful for future feed-specific queries.
    """
    if feed == FeedType.DIASPORA:
        return _build_conditions(
            score=("relevance_diaspora", "diaspora_score", thresholds.news_diaspora_min_score),
            language=("LOWER(COALESCE(language, '')) IN ('nl','tr')"),
            extra="(COALESCE(location_tag, '') IN ('local','origin') OR LOWER(COALESCE(category, '')) IN ('nl_local','nl_national'))",
        )
    if feed == FeedType.NL:
        return _build_conditions(
            score=("relevance_nl", "nl_score", thresholds.news_nl_min_score),
            language=("LOWER(COALESCE(language, '')) = 'nl'"),
            extra="LOWER(COALESCE(category, '')) IN ('nl_local','nl_national')",
        )
    if feed == FeedType.TR:
        return _build_conditions(
            score=("relevance_tr", "tr_score", thresholds.news_tr_min_score),
            extra="(LOWER(COALESCE(language, '')) = 'tr' OR LOWER(COALESCE(category, '')) IN ('tr_national'))",
        )
    if feed == FeedType.LOCAL:
        return _build_conditions(
            score=("relevance_nl", "local_score", thresholds.news_local_min_score),
            extra="COALESCE(location_tag, '') = 'local' AND LOWER(COALESCE(category, '')) IN ('nl_local','nl_national')",
        )
    if feed == FeedType.ORIGIN:
        sql = (
            "COALESCE(location_tag, '') = 'origin' AND "
            "("
            "COALESCE(relevance_tr, 0) >= %(origin_score)s OR "
            "LOWER(COALESCE(category, '')) IN ('tr_national')"
            ")"
        )
        return sql, {"origin_score": thresholds.news_origin_min_score}
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


def _extract_scores(news_row: Mapping[str, Any]) -> Dict[str, float]:
    return {
        "relevance_diaspora": float(news_row.get("relevance_diaspora") or 0.0),
        "relevance_nl": float(news_row.get("relevance_nl") or 0.0),
        "relevance_tr": float(news_row.get("relevance_tr") or 0.0),
        "relevance_geo": float(news_row.get("relevance_geo") or 0.0),
    }

