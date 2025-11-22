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

    assert is_in_feed(FeedType.LOCAL, row, row, thresholds)

    origin_row = dict(row)
    origin_row.update(
        {
            "language": "tr",
            "category": "tr_national",
            "location_tag": "origin",
            "relevance_tr": thresholds.news_origin_min_score - 0.05,
        }
    )
    # Category alone should qualify origin even if score is slightly under threshold
    assert is_in_feed(FeedType.ORIGIN, origin_row, origin_row, thresholds)


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
    assert "origin_score" in params_origin
    assert "LOWER(COALESCE(category, '')) IN ('tr_national')" in sql_origin


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

