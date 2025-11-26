from __future__ import annotations

from datetime import datetime

from app.models.ai_config import AIConfig
from services.news_feed_rules import (
    FeedThresholds,
    FeedType,
    build_feed_filter,
    is_in_feed,
    thresholds_from_config,
)


def _base_thresholds() -> FeedThresholds:
    return FeedThresholds(
        news_diaspora_min_score=0.75,
        news_nl_min_score=0.75,
        news_tr_min_score=0.75,
        news_local_min_score=0.70,
        news_origin_min_score=0.70,
        news_geo_min_score=0.80,
    )


def _base_row() -> dict:
    return {
        "language": "nl",
        "category": "nl_local",
        "region": "rotterdam",
        "location_tag": "local",
        "relevance_diaspora": 0.9,
        "relevance_nl": 0.9,
        "relevance_tr": 0.3,
        "relevance_geo": 0.4,
    }


def test_is_in_feed_respects_thresholds():
    row = _base_row()
    thresholds = _base_thresholds()
    assert is_in_feed(FeedType.DIASPORA, row, row, thresholds)

    row["relevance_diaspora"] = thresholds.news_diaspora_min_score - 0.05
    assert not is_in_feed(FeedType.DIASPORA, row, row, thresholds)


def test_feed_specific_rules_cover_local_and_origin():
    thresholds = _base_thresholds()
    row = _base_row()
    row["relevance_nl"] = 0.05

    assert is_in_feed(FeedType.LOCAL, row, row, thresholds)

    origin_row = dict(row)
    origin_row.update(
        {
            "language": "tr",
            "category": "tr_national",
            "location_tag": "origin",
            "relevance_tr": 0.0,
        }
    )
    # Category/language alone should qualify origin even if score is low.
    assert is_in_feed(FeedType.ORIGIN, origin_row, origin_row, thresholds)


def test_local_origin_ignore_relevance_thresholds():
    thresholds = _base_thresholds()
    row = _base_row()
    row["relevance_nl"] = 0.0
    assert is_in_feed(FeedType.LOCAL, row, row, thresholds)

    origin_row = {
        "language": "tr",
        "category": "culture",  # not TR category, but language matches
        "location_tag": "origin",
        "relevance_tr": 0.0,
    }
    assert is_in_feed(FeedType.ORIGIN, origin_row, origin_row, thresholds)
    non_tr_row = dict(origin_row)
    non_tr_row["language"] = "en"
    non_tr_row["category"] = "tr_national"
    assert is_in_feed(FeedType.ORIGIN, non_tr_row, non_tr_row, thresholds)


def test_custom_threshold_overrides_change_membership():
    row = _base_row()
    row["language"] = "en"
    row["category"] = "geopolitiek"
    row["relevance_geo"] = 0.45
    thresholds = _base_thresholds()
    assert not is_in_feed(FeedType.GEO, row, row, thresholds)

    relaxed = FeedThresholds(
        news_diaspora_min_score=thresholds.news_diaspora_min_score,
        news_nl_min_score=thresholds.news_nl_min_score,
        news_tr_min_score=thresholds.news_tr_min_score,
        news_local_min_score=thresholds.news_local_min_score,
        news_origin_min_score=thresholds.news_origin_min_score,
        news_geo_min_score=0.40,
    )
    assert is_in_feed(FeedType.GEO, row, row, relaxed)


def test_build_feed_filter_embeds_threshold_param_names():
    thresholds = _base_thresholds()
    sql, params = build_feed_filter(FeedType.DIASPORA, thresholds)
    assert "relevance_diaspora" in sql
    assert params["diaspora_score"] == thresholds.news_diaspora_min_score

    sql_origin, params_origin = build_feed_filter(FeedType.ORIGIN, thresholds)
    assert params_origin == {}
    assert "relevance_tr" not in sql_origin
    assert "COALESCE(location_tag" in sql_origin

    sql_nl, params_nl = build_feed_filter(FeedType.NL, thresholds)
    assert "source_key" in sql_nl
    assert "nl_priority" in params_nl
    assert params_nl["nl_priority"]
    # Note: nl_allowed is no longer used - we relaxed the allowlist

    sql_tr, params_tr = build_feed_filter(FeedType.TR, thresholds)
    assert "source_key" in sql_tr
    assert "tr_priority" in params_tr
    assert params_tr["tr_priority"]
    # Note: tr_allowed is no longer used - we relaxed the allowlist


def test_thresholds_from_config_maps_all_fields():
    cfg = AIConfig(
        id=1,
        classify_min_conf=0.8,
        verify_min_conf=0.8,
        task_verifier_min_conf=0.8,
        auto_promote_conf=0.9,
        news_diaspora_min_score=0.81,
        news_nl_min_score=0.76,
        news_tr_min_score=0.78,
        news_local_min_score=0.69,
        news_origin_min_score=0.71,
        news_geo_min_score=0.82,
        monitor_low_conf_days=3,
        monitor_medium_conf_days=7,
        monitor_high_conf_days=14,
        monitor_verified_few_reviews_days=30,
        monitor_verified_medium_reviews_days=60,
        monitor_verified_many_reviews_days=90,
        updated_at=datetime.utcnow(),
        updated_by="tester@example.com",
    )
    thresholds = thresholds_from_config(cfg)
    assert thresholds.news_diaspora_min_score == 0.81
    assert thresholds.news_geo_min_score == 0.82


def test_priority_sources_bypass_thresholds_for_nl_tr():
    thresholds = _base_thresholds()
    nl_row = {
        **_base_row(),
        "language": "nl",
        "category": "nl_national",
        "relevance_nl": 0.1,
        "source_key": "nos_headlines",
    }
    assert is_in_feed(FeedType.NL, nl_row, nl_row, thresholds)

    tr_row = {
        **_base_row(),
        "language": "tr",
        "category": "tr_national",
        "relevance_tr": 0.1,
        "source_key": "haberturk_headlines",
    }
    assert is_in_feed(FeedType.TR, tr_row, tr_row, thresholds)


def test_nl_feed_allows_all_sources_with_score():
    """NL feed now allows all sources that pass score + language + category filters."""
    thresholds = _base_thresholds()
    row = {
        **_base_row(),
        "source_key": "ad_rotterdam",
        "relevance_nl": 0.99,
        "language": "nl",
        "category": "nl_national",
    }
    # Non-priority sources can appear if they pass normal filters
    assert is_in_feed(FeedType.NL, row, row, thresholds)


def test_tr_feed_allows_all_sources_with_score():
    """TR feed now allows all sources that pass score + language + category filters."""
    thresholds = _base_thresholds()
    row = {
        **_base_row(),
        "language": "tr",
        "category": "tr_national",
        "relevance_tr": 0.99,
        "source_key": "anadolu_ajansi",
    }
    # Non-priority sources can appear if they pass normal filters
    assert is_in_feed(FeedType.TR, row, row, thresholds)

