import pytest
from datetime import date

from services import metrics_service
from services.news_feed_rules import FeedThresholds, FeedType
from app.models.metrics import NewsErrorMetrics, NewsLabelCount, NewsPerDayItem


@pytest.mark.asyncio
async def test_news_ingest_daily_series(monkeypatch):
    sample_rows = [
        {"day": date(2025, 1, 1), "count": 3},
        {"day": date(2025, 1, 2), "count": 5},
    ]

    async def fake_fetch(sql, cutoff):
        assert "date_trunc('day'" in sql
        return sample_rows

    monkeypatch.setattr(metrics_service, "fetch", fake_fetch)

    result = await metrics_service._news_ingest_daily_series(days=7)
    assert [item.count for item in result] == [3, 5]
    assert [item.date for item in result] == [date(2025, 1, 1), date(2025, 1, 2)]


@pytest.mark.asyncio
async def test_news_ingest_by_source(monkeypatch):
    async def fake_fetch(sql, cutoff):
        assert "source_key" in sql
        return [
            {"label": "Source A", "count": 4},
            {"label": "Source B", "count": 2},
        ]

    monkeypatch.setattr(metrics_service, "fetch", fake_fetch)

    result = await metrics_service._news_ingest_by_source(window_hours=12)
    assert len(result) == 2
    assert result[0].label == "Source A"
    assert result[0].count == 4


@pytest.mark.asyncio
async def test_news_error_metrics(monkeypatch):
    async def fake_fetchrow(sql, cutoff):
        if "raw_ingested_news" in sql:
            return {"error_ai_count": 2, "pending_count": 1}
        if "ai_logs" in sql:
            return {"count": 3}
        return {}

    monkeypatch.setattr(metrics_service, "fetchrow", fake_fetchrow)

    result = await metrics_service._news_error_metrics(window_hours=6)
    assert result.ingest_errors_last_24h == 2
    assert result.pending_items_last_24h == 1
    assert result.classify_errors_last_24h == 3


@pytest.mark.asyncio
async def test_news_feed_distribution(monkeypatch):
    sample_rows = [
        {
            "source_key": "src_a",
            "category": "nl_local",
            "language": "nl",
            "location_tag": "local",
            "relevance_diaspora": 0.9,
            "relevance_nl": 0.9,
            "relevance_tr": 0.2,
            "relevance_geo": 0.1,
        },
        {
            "source_key": "src_b",
            "category": "tr_national",
            "language": "tr",
            "location_tag": "origin",
            "relevance_diaspora": 0.4,
            "relevance_nl": 0.1,
            "relevance_tr": 0.95,
            "relevance_geo": 0.3,
        },
    ]

    async def fake_fetch(sql, *args):
        if "FROM raw_ingested_news" in sql:
            return sample_rows
        raise AssertionError("Unexpected query")

    async def fake_meta(source_keys):
        return {
            "src_a": {"category": "nl_local", "language": "nl", "region": None, "source_name": "A"},
            "src_b": {"category": "tr_national", "language": "tr", "region": None, "source_name": "B"},
        }

    async def fake_thresholds():
        return FeedThresholds(
            news_diaspora_min_score=0.0,
            news_nl_min_score=0.0,
            news_tr_min_score=0.0,
            news_local_min_score=0.0,
            news_origin_min_score=0.0,
            news_geo_min_score=0.0,
        )

    monkeypatch.setattr(metrics_service, "fetch", fake_fetch)
    monkeypatch.setattr(metrics_service, "_load_news_source_meta", fake_meta)
    monkeypatch.setattr(metrics_service, "_load_news_feed_thresholds", fake_thresholds)

    result = await metrics_service._news_feed_distribution(window_hours=24)
    counts = {item.label: item.count for item in result}

    assert counts[FeedType.DIASPORA.value] >= 1
    assert counts[FeedType.NL.value] >= 1
    assert counts[FeedType.TR.value] >= 1
    # All feed keys should be present, even if zero
    for feed in FeedType:
        assert feed.value in counts


@pytest.mark.asyncio
async def test_generate_news_metrics_snapshot(monkeypatch):
    sample_daily = [NewsPerDayItem(date=date(2025, 1, 3), count=7)]
    sample_by_source = [NewsLabelCount(label="Source A", count=5)]
    sample_by_feed = [NewsLabelCount(label=FeedType.DIASPORA.value, count=4)]
    sample_errors = NewsErrorMetrics(
        ingest_errors_last_24h=1,
        classify_errors_last_24h=2,
        pending_items_last_24h=3,
    )

    async def fake_daily(days):
        assert days == 7
        return sample_daily

    async def fake_by_source(window_hours):
        assert window_hours == 24
        return sample_by_source

    async def fake_by_feed(window_hours):
        assert window_hours == 24
        return sample_by_feed

    async def fake_errors(window_hours):
        assert window_hours == 24
        return sample_errors

    monkeypatch.setattr(metrics_service, "_news_ingest_daily_series", fake_daily)
    monkeypatch.setattr(metrics_service, "_news_ingest_by_source", fake_by_source)
    monkeypatch.setattr(metrics_service, "_news_feed_distribution", fake_by_feed)
    monkeypatch.setattr(metrics_service, "_news_error_metrics", fake_errors)

    snapshot = await metrics_service.generate_news_metrics_snapshot()
    assert snapshot.items_per_day_last_7d == sample_daily
    assert snapshot.items_by_source_last_24h == sample_by_source
    assert snapshot.items_by_feed_last_24h == sample_by_feed
    assert snapshot.errors == sample_errors

