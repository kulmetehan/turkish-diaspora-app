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

    # NL feed: no AI score dependency, uses source_key matching
    sql_nl, params_nl = build_feed_filter(FeedType.NL, thresholds)
    assert "source_key" in sql_nl
    assert "nl_sources" in params_nl
    assert isinstance(params_nl["nl_sources"], list)
    assert len(params_nl["nl_sources"]) > 0
    assert "relevance_nl" not in sql_nl  # No score threshold
    assert "published_at IS NOT NULL" in sql_nl

    # TR feed: no AI score dependency, uses source_key matching
    sql_tr, params_tr = build_feed_filter(FeedType.TR, thresholds)
    assert "source_key" in sql_tr
    assert "tr_sources" in params_tr
    assert isinstance(params_tr["tr_sources"], list)
    assert len(params_tr["tr_sources"]) > 0
    assert "relevance_tr" not in sql_tr  # No score threshold
    assert "published_at IS NOT NULL" in sql_tr


def test_build_feed_filter_with_categories():
    """Verify category parameter is applied to SQL for NL/TR feeds."""
    thresholds = _base_thresholds()
    
    # NL feed with category filter
    sql_nl, params_nl = build_feed_filter(
        FeedType.NL,
        thresholds,
        categories=["nl_national_sport"],
    )
    assert "nl_sources" in params_nl
    assert "nl_categories" in params_nl
    assert params_nl["nl_categories"] == ["nl_national_sport"]
    assert "category" in sql_nl.lower()
    
    # TR feed with category filter
    sql_tr, params_tr = build_feed_filter(
        FeedType.TR,
        thresholds,
        categories=["tr_national_sport"],
    )
    assert "tr_sources" in params_tr
    assert "tr_categories" in params_tr
    assert params_tr["tr_categories"] == ["tr_national_sport"]
    assert "category" in sql_tr.lower()
    
    # NL feed without category filter (should use all NL categories)
    sql_nl_default, params_nl_default = build_feed_filter(FeedType.NL, thresholds)
    assert "nl_sources" in params_nl_default
    assert "nl_categories" not in params_nl_default  # No category param when not specified
    assert "nl_national" in sql_nl_default  # Should include all NL categories


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


def test_nl_feed_requires_source_key_match():
    """NL feed now requires source_key to be in allowed list, no score threshold."""
    thresholds = _base_thresholds()
    nl_row = {
        **_base_row(),
        "language": "nl",
        "category": "nl_national",
        "relevance_nl": 0.0,  # Score doesn't matter anymore
        "source_key": "nos_headlines",
    }
    assert is_in_feed(FeedType.NL, nl_row, nl_row, thresholds)

    # Non-allowed source should not appear
    nl_row_bad = {
        **_base_row(),
        "language": "nl",
        "category": "nl_national",
        "source_key": "unknown_source",
    }
    # Note: is_in_feed still uses priority logic, but build_feed_filter uses source_key list
    # This test verifies the is_in_feed helper (used for in-memory checks)
    # The actual SQL filter uses _get_nl_source_keys() which includes all NL sources
    assert is_in_feed(FeedType.NL, nl_row_bad, nl_row_bad, thresholds) == False


def test_tr_feed_requires_source_key_match():
    """TR feed now requires source_key to be in allowed list, no score threshold."""
    thresholds = _base_thresholds()
    tr_row = {
        **_base_row(),
        "language": "tr",
        "category": "tr_national",
        "relevance_tr": 0.0,  # Score doesn't matter anymore
        "source_key": "haberturk_headlines",
    }
    assert is_in_feed(FeedType.TR, tr_row, tr_row, thresholds)


def test_nl_feed_source_whitelist():
    """Verify NL feed only includes NOS and NU.nl sources."""
    thresholds = _base_thresholds()
    sql, params = build_feed_filter(FeedType.NL, thresholds)
    
    # Check that nl_sources contains only NOS and NU.nl
    nl_sources = params["nl_sources"]
    assert "nos_headlines" in nl_sources or "https://feeds.nos.nl/nosnieuwsalgemeen" in nl_sources
    assert "nu_headlines" in nl_sources or "https://www.nu.nl/rss/algemeen" in nl_sources
    
    # AD Rotterdam should NOT be in the list
    assert not any("ad.nl" in s.lower() for s in nl_sources)


def test_tr_feed_source_whitelist():
    """Verify TR feed only includes Habertürk and TRT sources."""
    thresholds = _base_thresholds()
    sql, params = build_feed_filter(FeedType.TR, thresholds)
    
    # Check that tr_sources contains Habertürk and TRT
    tr_sources = params["tr_sources"]
    assert "haberturk_headlines" in tr_sources or "https://www.haberturk.com/rss/manset.xml" in tr_sources
    assert "trt_headlines" in tr_sources or "https://www.trthaber.com/rss/sondakika.rss" in tr_sources
    
    # AA.com.tr should NOT be in the list
    assert not any("aa.com.tr" in s.lower() for s in tr_sources)

