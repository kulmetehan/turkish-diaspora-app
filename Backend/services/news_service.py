from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from app.models.news_city_config import get_city_by_key
from app.models.news_public import NewsItem
from app.core.logging import get_logger
from services.ai_config_service import get_ai_config, initialize_ai_config
from services.db_service import fetch, fetchrow
from services.news_feed_rules import (
    FeedThresholds,
    FeedType,
    build_feed_filter,
    thresholds_from_config,
)

_PARAM_REGEX = re.compile(r"%\((?P<name>\w+)\)s")
_SCORE_COLUMN_BY_FEED: Dict[FeedType, str] = {
    FeedType.DIASPORA: "relevance_diaspora",
    FeedType.NL: "relevance_nl",
    FeedType.TR: "relevance_tr",
    FeedType.LOCAL: "relevance_nl",
    FeedType.ORIGIN: "relevance_tr",
    FeedType.GEO: "relevance_geo",
}
TRENDING_WINDOW_HOURS = 48
_SNIPPET_MAX_LEN = 280
logger = get_logger().bind(module="news_service")
ALLOWED_NEWS_THEMES: Tuple[str, ...] = (
    "politics",
    "economy",
    "culture",
    "religion",
    "sports",
    "security",
)


async def _load_feed_thresholds() -> FeedThresholds:
    config = await get_ai_config()
    if not config:
        config = await initialize_ai_config()
    return thresholds_from_config(config)


def _convert_named_params(
    sql_template: str,
    named_params: Mapping[str, Any],
    start_index: int = 1,
) -> Tuple[str, List[Any], int]:
    """Convert %(name)s placeholders to asyncpg-style $N placeholders."""
    placeholder_map: Dict[str, int] = {}
    ordered_values: List[Any] = []
    next_index = start_index

    def _replacer(match: re.Match[str]) -> str:
        nonlocal next_index
        name = match.group("name")
        if name not in named_params:
            raise KeyError(f"Missing parameter '{name}' for SQL template.")
        if name not in placeholder_map:
            placeholder_map[name] = next_index
            ordered_values.append(named_params[name])
            next_index += 1
        return f"${placeholder_map[name]}"

    converted_sql = _PARAM_REGEX.sub(_replacer, sql_template)
    return converted_sql, ordered_values, next_index


def _trim_text(value: str, max_len: int = _SNIPPET_MAX_LEN) -> str:
    text = value.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _derive_snippet(summary: Any, content: Any, title: str) -> str:
    for candidate in (summary, content, title):
        if isinstance(candidate, str) and candidate.strip():
            return _trim_text(candidate)
    return ""


def _build_tags(location_tag: Any, topics: Any) -> List[str]:
    tags: List[str] = []
    if isinstance(location_tag, str):
        normalized = location_tag.strip().lower()
        if normalized:
            tags.append(normalized)

    if isinstance(topics, Sequence) and not isinstance(topics, (str, bytes)):
        for topic in topics:
            if isinstance(topic, str):
                cleaned = topic.strip()
                if cleaned:
                    tags.append(cleaned)

    deduped: List[str] = []
    seen: set[str] = set()
    for tag in tags:
        tag_l = tag.lower()
        if tag_l in seen:
            continue
        seen.add(tag_l)
        deduped.append(tag)
    return deduped


def _row_to_news_item(row: Mapping[str, Any]) -> NewsItem:
    return NewsItem(
        id=int(row["id"]),
        title=str(row.get("title") or "Untitled"),
        snippet=_derive_snippet(row.get("summary"), row.get("content"), row.get("title") or "Untitled"),
        source=str(row.get("source_name") or "Unknown"),
        published_at=row["published_at"],
        url=str(row.get("link")),
        image_url=row.get("image_url"),
        tags=_build_tags(row.get("location_tag"), row.get("topics")),
    )


def _score_column_for_feed(feed: FeedType) -> str:
    column = _SCORE_COLUMN_BY_FEED.get(feed)
    if not column:
        raise ValueError(f"No score column configured for feed '{feed.value}'.")
    return column


def normalize_theme_filters(values: Sequence[str] | None) -> List[str]:
    """Normalize requested themes and ensure they belong to the allowlist."""

    normalized: List[str] = []
    seen: set[str] = set()

    if not values:
        return normalized

    for raw_value in values:
        if not isinstance(raw_value, str):
            continue
        parts = raw_value.split(",")
        for part in parts:
            candidate = part.strip().lower()
            if not candidate:
                continue
            if candidate not in ALLOWED_NEWS_THEMES:
                allowed = ", ".join(ALLOWED_NEWS_THEMES)
                raise ValueError(f"Invalid theme '{candidate}'. Allowed values: {allowed}.")
            if candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)

    return normalized


def _normalize_city_filters(values: Sequence[str] | None) -> List[str]:
    if not values:
        return []
    normalized: List[str] = []
    seen: set[str] = set()
    for raw_value in values:
        if not isinstance(raw_value, str):
            continue
        candidate = raw_value.strip().lower()
        if not candidate:
            continue
        resolved = _resolve_city_filter(candidate)
        if resolved in seen:
            continue
        seen.add(resolved)
        normalized.append(resolved)
        if len(normalized) == 2:
            break
    return normalized


def _resolve_city_filter(city_key: str) -> str:
    city = get_city_by_key(city_key)
    if city:
        return city.legacy_key or city.city_key
    return city_key


async def list_news_by_feed(
    feed: FeedType,
    *,
    limit: int,
    offset: int,
    themes: Sequence[str] | None = None,
    cities_nl: Sequence[str] | None = None,
    cities_tr: Sequence[str] | None = None,
) -> Tuple[List[NewsItem], int]:
    normalized_themes = normalize_theme_filters(themes)
    thresholds = await _load_feed_thresholds()
    feed_sql_template, named_params = build_feed_filter(feed, thresholds)
    feed_sql, feed_args, next_index = _convert_named_params(feed_sql_template, named_params)

    where_clause = f"processing_state = 'classified' AND published_at IS NOT NULL AND ({feed_sql})"
    score_column = _score_column_for_feed(feed)
    order_clause = "relevance_score DESC, published_at DESC"
    if feed in (FeedType.NL, FeedType.TR):
        order_clause = "published_at DESC, relevance_score DESC"

    where_params: List[Any] = [*feed_args]
    if normalized_themes:
        theme_placeholder = f"${next_index}"
        next_index += 1
        where_clause += f"""
            AND EXISTS (
                SELECT 1
                FROM unnest({theme_placeholder}::text[]) AS theme(value)
                WHERE COALESCE(topics, '[]'::jsonb) ? theme.value
            )
        """
        where_params.append(normalized_themes)

    if feed == FeedType.LOCAL:
        normalized_cities = _normalize_city_filters(cities_nl)
        if normalized_cities:
            city_placeholder = f"${next_index}"
            next_index += 1
            where_clause += f"""
                AND EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(COALESCE(location_context -> 'matches', '[]'::jsonb)) AS match
                    WHERE LOWER(match->>'city_key') = ANY({city_placeholder})
                )
            """
            where_params.append(normalized_cities)
    elif feed == FeedType.ORIGIN:
        normalized_cities = _normalize_city_filters(cities_tr)
        if normalized_cities:
            city_placeholder = f"${next_index}"
            next_index += 1
            where_clause += f"""
                AND EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(COALESCE(location_context -> 'matches', '[]'::jsonb)) AS match
                    WHERE LOWER(match->>'city_key') = ANY({city_placeholder})
                )
            """
            where_params.append(normalized_cities)

    limit_placeholder = f"${next_index}"
    offset_placeholder = f"${next_index + 1}"
    query_params: List[Any] = [*where_params, limit, offset]

    query = f"""
        SELECT
            id,
            title,
            summary,
            content,
            source_name,
            link,
            image_url,
            published_at,
            topics,
            location_tag,
            COALESCE({score_column}, 0) AS relevance_score
        FROM raw_ingested_news
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
    """

    rows = await fetch(query, *query_params)
    items = [_row_to_news_item(dict(row)) for row in rows]

    count_query = f"SELECT COUNT(*) AS total FROM raw_ingested_news WHERE {where_clause}"
    count_row = await fetchrow(count_query, *where_params)
    total = int(dict(count_row or {"total": 0}).get("total", 0))
    
    # Log empty feeds for debugging
    if total == 0:
        city_keys = []
        if feed == FeedType.LOCAL and cities_nl:
            city_keys = list(cities_nl)
        elif feed == FeedType.ORIGIN and cities_tr:
            city_keys = list(cities_tr)
        logger.info(
            "news_feed_empty",
            feed=feed.value,
            themes=normalized_themes if normalized_themes else None,
            cities=city_keys if city_keys else None,
        )
    
    return items, total


async def list_trending_news(
    *,
    limit: int,
    offset: int,
    window_hours: int = TRENDING_WINDOW_HOURS,
) -> Tuple[List[NewsItem], int]:
    thresholds = await _load_feed_thresholds()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    params = [
        cutoff,
        float(thresholds.news_diaspora_min_score),
        float(thresholds.news_geo_min_score),
        float(window_hours),
        limit,
        offset,
    ]
    query = """
        WITH ranked AS (
            SELECT
                id,
                title,
                summary,
                content,
                source_name,
                link,
                image_url,
                published_at,
                topics,
                location_tag,
                COALESCE(relevance_diaspora, 0) AS diaspora_score,
                COALESCE(relevance_geo, 0) AS geo_score,
                COUNT(*) OVER (PARTITION BY source_key) AS source_freq,
                EXTRACT(EPOCH FROM (NOW() - published_at)) / 3600.0 AS hours_since
            FROM raw_ingested_news
            WHERE processing_state = 'classified'
              AND published_at IS NOT NULL
              AND published_at >= $1
              AND (
                COALESCE(relevance_diaspora, 0) >= $2
                OR COALESCE(relevance_geo, 0) >= $3
              )
        )
        SELECT
            id,
            title,
            summary,
            content,
            source_name,
            link,
            image_url,
            published_at,
            topics,
            location_tag,
            (GREATEST(diaspora_score, geo_score)
                * GREATEST(0.0, 1.0 - (hours_since / NULLIF($4, 0)))
                * (1.0 + LEAST(LOG(1 + source_freq), 0.5))
            ) AS trending_score,
            hours_since,
            source_freq
        FROM ranked
        ORDER BY trending_score DESC, published_at DESC
        LIMIT $5 OFFSET $6
    """
    rows = await fetch(query, *params)
    items = [_row_to_news_item(dict(row)) for row in rows]
    top_samples = [
        {
            "id": int(row["id"]),
            "score": float(row.get("trending_score") or 0.0),
            "hours_since": float(row.get("hours_since") or 0.0),
        }
        for row in rows[:3]
    ]

    count_query = """
        SELECT COUNT(*) AS total
        FROM raw_ingested_news
        WHERE processing_state = 'classified'
          AND published_at IS NOT NULL
          AND published_at >= $1
          AND (
            COALESCE(relevance_diaspora, 0) >= $2
            OR COALESCE(relevance_geo, 0) >= $3
          )
    """
    count_row = await fetchrow(count_query, cutoff, params[1], params[2])
    total = int(dict(count_row or {"total": 0}).get("total", 0))

    logger.info(
        "news_trending_query",
        window_hours=window_hours,
        limit=limit,
        offset=offset,
        result_count=len(items),
        total=total,
        top_samples=top_samples,
    )
    return items, total


async def search_news(
    *,
    query: str,
    limit: int,
    offset: int,
) -> Tuple[List[NewsItem], int]:
    normalized = (query or "").strip()
    if len(normalized) < 2:
        return [], 0

    search_sql = """
        WITH q AS (
            SELECT websearch_to_tsquery('simple', $1) AS tsq
        )
        SELECT
            id,
            title,
            summary,
            content,
            source_name,
            link,
            image_url,
            published_at,
            topics,
            location_tag,
            (
                ts_rank(news_search_tsv, q.tsq) * 0.7
                + COALESCE(relevance_diaspora, 0) * 0.3
            ) AS search_score
        FROM raw_ingested_news, q
        WHERE
            processing_state = 'classified'
            AND published_at IS NOT NULL
            AND news_search_tsv @@ q.tsq
        ORDER BY search_score DESC, published_at DESC
        LIMIT $2 OFFSET $3
    """
    rows = await fetch(search_sql, normalized, limit, offset)
    items = [_row_to_news_item(dict(row)) for row in rows]

    count_sql = """
        WITH q AS (
            SELECT websearch_to_tsquery('simple', $1) AS tsq
        )
        SELECT COUNT(*) AS total
        FROM raw_ingested_news, q
        WHERE
            processing_state = 'classified'
            AND published_at IS NOT NULL
            AND news_search_tsv @@ q.tsq
    """
    count_row = await fetchrow(count_sql, normalized)
    total = int(dict(count_row or {"total": 0}).get("total", 0))
    return items, total


