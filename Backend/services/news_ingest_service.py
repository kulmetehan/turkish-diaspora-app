from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import feedparser
import httpx

from app.core.logging import get_logger
from app.models.news_normalized import NormalizedNewsItem
from app.models.news_sources import NewsSource, get_all_news_sources
from services.db_service import execute, fetchrow
from services.rss_normalization import normalize_feed_entries
from services.news_legal_sanitizer import SanitizedNewsItem, sanitize_ingested_entry

logger = get_logger()

DEFAULT_NEWS_INGEST_TIMEOUT_S = int(os.getenv("NEWS_INGEST_TIMEOUT_S", "15"))
DEFAULT_NEWS_INGEST_MAX_CONCURRENCY = int(os.getenv("NEWS_INGEST_MAX_CONCURRENCY", "5"))
_BLOCKING_X_ROBOTS_TOKENS = {"noai", "noindex", "none", "nosnippet", "noarchive"}


def make_source_key(source: NewsSource) -> str:
    """Generate normalized source_key (lowercase) for consistent matching with feed rules."""
    raw_key = source.key or source.url
    return raw_key.strip().lower() if raw_key else ""


def _jsonify_entry(entry: Any) -> Any:
    try:
        return json.loads(json.dumps(entry, default=str))
    except Exception:
        return str(entry)


class NewsIngestService:
    def __init__(
        self,
        *,
        timeout_s: int = DEFAULT_NEWS_INGEST_TIMEOUT_S,
        max_concurrency: int = DEFAULT_NEWS_INGEST_MAX_CONCURRENCY,
    ) -> None:
        self.timeout_s = timeout_s
        self.max_concurrency = max_concurrency
        self._client: Optional[httpx.AsyncClient] = None
        self._sem = asyncio.Semaphore(max(1, max_concurrency))

    async def __aenter__(self) -> "NewsIngestService":
        self._client = httpx.AsyncClient(
            timeout=self.timeout_s,
            headers={"User-Agent": "tda-news-ingest/1.0"},
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client:
            await self._client.aclose()

    async def _should_fetch_now(self, source: NewsSource) -> bool:
        source_key = make_source_key(source)
        row = await fetchrow(
            """
            SELECT next_refresh_at
            FROM news_source_state
            WHERE source_key = $1
            """,
            source_key,
        )
        if not row:
            return True
        next_refresh_at = row.get("next_refresh_at")
        if not next_refresh_at:
            return True
        return next_refresh_at <= datetime.now(timezone.utc)

    async def _mark_source_success(self, source: NewsSource, inserted: int) -> None:
        source_key = make_source_key(source)
        now = datetime.now(timezone.utc)
        refresh_minutes = source.refresh_minutes
        next_refresh = now + timedelta(minutes=refresh_minutes)
        await execute(
            """
            INSERT INTO news_source_state (
                source_key, source_name, source_url, category, language, region,
                refresh_minutes, last_fetched_at, next_refresh_at,
                consecutive_failures, last_error, created_at, updated_at
            )
            VALUES (
                $1,$2,$3,$4,$5,$6,
                $7,$8,$9,
                0,NULL,NOW(),NOW()
            )
            ON CONFLICT (source_key) DO UPDATE
            SET source_name = EXCLUDED.source_name,
                source_url = EXCLUDED.source_url,
                category = EXCLUDED.category,
                language = EXCLUDED.language,
                region = EXCLUDED.region,
                refresh_minutes = EXCLUDED.refresh_minutes,
                last_fetched_at = EXCLUDED.last_fetched_at,
                next_refresh_at = EXCLUDED.next_refresh_at,
                consecutive_failures = 0,
                last_error = NULL,
                updated_at = NOW();
            """,
            source_key,
            source.name,
            source.url,
            source.category,
            source.language,
            source.region,
            refresh_minutes,
            now,
            next_refresh,
        )
        logger.info(
            "news_ingest_source_success",
            source=source.name,
            inserted=inserted,
        )

    async def _mark_source_failure(self, source: NewsSource, error_message: str) -> None:
        source_key = make_source_key(source)
        now = datetime.now(timezone.utc)
        row = await fetchrow(
            """
            SELECT consecutive_failures, refresh_minutes
            FROM news_source_state
            WHERE source_key = $1
            """,
            source_key,
        )
        if row:
            failures = int(row.get("consecutive_failures") or 0) + 1
            base_refresh = int(row.get("refresh_minutes") or source.refresh_minutes)
        else:
            failures = 1
            base_refresh = source.refresh_minutes
        backoff_factor = min(4, failures)
        next_refresh = now + timedelta(minutes=base_refresh * backoff_factor)
        await execute(
            """
            INSERT INTO news_source_state (
                source_key, source_name, source_url, category, language, region,
                refresh_minutes, last_fetched_at, next_refresh_at,
                consecutive_failures, last_error, created_at, updated_at
            )
            VALUES (
                $1,$2,$3,$4,$5,$6,
                $7,NULL,$8,
                $9,$10,NOW(),NOW()
            )
            ON CONFLICT (source_key) DO UPDATE
            SET refresh_minutes = EXCLUDED.refresh_minutes,
                next_refresh_at = EXCLUDED.next_refresh_at,
                consecutive_failures = EXCLUDED.consecutive_failures,
                last_error = EXCLUDED.last_error,
                updated_at = NOW();
            """,
            source_key,
            source.name,
            source.url,
            source.category,
            source.language,
            source.region,
            base_refresh,
            next_refresh,
            failures,
            error_message[:500],
        )

    async def _fetch_feed(self, source: NewsSource) -> Optional[bytes]:
        if not self._client:
            raise RuntimeError("NewsIngestService client not initialized")
        try:
            async with self._sem:
                response = await self._client.get(source.url)
            response.raise_for_status()
            return response.content
        except Exception as exc:
            logger.warning(
                "news_ingest_feed_failed",
                source=source.name,
                url=source.url,
                error=str(exc),
            )
            await self._mark_source_failure(source, str(exc))
            return None

    def _legal_metadata(self, source: NewsSource) -> Dict[str, Any]:
        return {
            "license": source.license,
            "redistribution_allowed": source.redistribution_allowed,
            "robots_policy": source.robots_policy,
        }

    async def _head_with_fallback(self, url: str) -> Optional[httpx.Response]:
        if not self._client:
            raise RuntimeError("NewsIngestService client not initialized")
        try:
            async with self._sem:
                response = await self._client.head(url, follow_redirects=True)
            response.raise_for_status()
            return response
        except Exception:
            try:
                async with self._sem:
                    response = await self._client.get(
                        url,
                        follow_redirects=True,
                        headers={"Range": "bytes=0-1024"},
                    )
                response.raise_for_status()
                return response
            except Exception as exc:
                logger.warning("news_ingest_head_request_failed", url=url, error=str(exc))
        return None

    async def _check_x_robots_tag(self, source: NewsSource) -> Optional[str]:
        response = await self._head_with_fallback(source.url)
        if not response:
            return None
        header = response.headers.get("X-Robots-Tag")
        if not header:
            return None
        tokens = {token.strip().lower() for token in header.split(",") if token.strip()}
        if tokens & _BLOCKING_X_ROBOTS_TOKENS:
            return "x_robots_tag_block"
        return None

    async def _fetch_robots_txt(self, parsed_feed_url) -> Optional[str]:
        if not self._client:
            raise RuntimeError("NewsIngestService client not initialized")
        robots_url = f"{parsed_feed_url.scheme}://{parsed_feed_url.netloc}/robots.txt"
        try:
            async with self._sem:
                response = await self._client.get(robots_url, timeout=self.timeout_s, follow_redirects=True)
            if response.status_code >= 400:
                return None
            return response.text
        except Exception as exc:
            logger.debug("news_ingest_robots_fetch_failed", url=robots_url, error=str(exc))
            return None

    @staticmethod
    def _is_disallowed_by_robots(robots_text: str, feed_path: str) -> bool:
        if not robots_text:
            return False
        feed_path = feed_path or "/"
        current_agent_applies = False
        for raw_line in robots_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            lower = line.lower()
            if lower.startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip().lower()
                current_agent_applies = agent in {"*", "tda-news-ingest", "tda-news-ingest/1.0"}
                continue
            if not current_agent_applies:
                continue
            if lower.startswith("disallow:"):
                value = line.split(":", 1)[1].strip()
                if not value:
                    continue
                if value == "/":
                    return True
                if feed_path.startswith(value):
                    return True
        return False

    async def _check_robots_policy(self, source: NewsSource) -> Optional[str]:
        policy = (source.robots_policy or "").strip().lower()
        if policy in {"", "ignore", "none"}:
            return None
        parsed = urlparse(source.url)
        robots_text = await self._fetch_robots_txt(parsed)
        if not robots_text:
            return None
        if self._is_disallowed_by_robots(robots_text, parsed.path or "/"):
            return "robots_txt_block"
        return None

    async def _enforce_legal_gate(self, source: NewsSource) -> Optional[str]:
        if source.redistribution_allowed is False:
            return "redistribution_not_allowed"
        xrobots_reason = await self._check_x_robots_tag(source)
        if xrobots_reason:
            return xrobots_reason
        robots_reason = await self._check_robots_policy(source)
        if robots_reason:
            return robots_reason
        return None

    def _sanitized_item_to_row(
        self,
        source: NewsSource,
        item: SanitizedNewsItem,
    ) -> Dict[str, Any]:
        source_key = make_source_key(source)
        published_at = item.published_at
        hash_input = f"{source_key}|{item.url}|{published_at.isoformat()}".encode("utf-8", "ignore")
        ingest_hash = hashlib.sha1(hash_input).hexdigest()

        return {
            "source_key": source_key,
            "source_name": source.name,
            "source_url": source.url,
            "category": source.category,
            "language": source.language,
            "region": source.region,
            "title": item.title,
            "summary": item.snippet,
            "content": None,
            "author": None,
            "link": item.url,
            "image_url": item.image_url,
            "published_at": published_at,
            "raw_entry": _jsonify_entry(item.raw_metadata),
            "ingest_hash": ingest_hash,
        }

    async def _persist_items(self, items: List[Dict[str, Any]]) -> int:
        inserted = 0
        for item in items:
            try:
                raw_entry_json = json.dumps(item["raw_entry"], ensure_ascii=False)
                result = await execute(
                    """
                    INSERT INTO raw_ingested_news (
                        source_key, source_name, source_url,
                        category, language, region,
                        title, summary, content, author,
                        link, image_url, published_at,
                        ingest_hash, raw_entry
                    ) VALUES (
                        $1,$2,$3,
                        $4,$5,$6,
                        $7,$8,$9,$10,
                        $11,$12,$13,
                        $14,$15
                    )
                    ON CONFLICT (source_key, ingest_hash) DO NOTHING;
                    """,
                    item["source_key"],
                    item["source_name"],
                    item["source_url"],
                    item["category"],
                    item["language"],
                    item["region"],
                    item["title"],
                    item.get("summary"),
                    item.get("content"),
                    item.get("author"),
                    item["link"],
                    item.get("image_url"),
                    item["published_at"],
                    item["ingest_hash"],
                    raw_entry_json,
                )
                if result and "INSERT" in result.upper():
                    inserted += 1
            except Exception as exc:
                logger.error(
                    "news_ingest_persist_error",
                    source_key=item.get("source_key"),
                    link=item.get("link"),
                    error=str(exc),
                )
        return inserted

    async def ingest_source(self, source: NewsSource) -> Dict[str, Any]:
        source_key = make_source_key(source)
        if not await self._should_fetch_now(source):
            return {"source_key": source_key, "skipped": True, "inserted": 0, "failed_items": 0}

        legal_meta = self._legal_metadata(source)
        legal_reason = await self._enforce_legal_gate(source)
        if legal_reason:
            logger.warning(
                "news_ingest_legal_validation_failed",
                source=source.name,
                source_key=source_key,
                reason=legal_reason,
                legal=legal_meta,
                legal_checks_passed=False,
            )
            logger.warning(
                "news_ingest_legal_skip",
                source=source.name,
                source_key=source_key,
                reason=legal_reason,
                legal=legal_meta,
            )
            await self._mark_source_failure(source, legal_reason)
            return {"source_key": source_key, "skipped": True, "inserted": 0, "failed_items": 0}
        else:
            logger.info(
                "news_ingest_legal_validation_passed",
                source=source.name,
                source_key=source_key,
                legal=legal_meta,
                legal_checks_passed=True,
            )

        raw_feed = await self._fetch_feed(source)
        if raw_feed is None:
            return {"source_key": source_key, "skipped": False, "inserted": 0, "failed_items": 0}

        parsed = feedparser.parse(raw_feed)
        normalized_items, norm_errors = normalize_feed_entries(parsed, source)

        for err in norm_errors:
            entry_raw = err.entry_raw or {}
            err_url = entry_raw.get("link") or entry_raw.get("id") or source.url
            logger.warning(
                "news_ingest_normalization_error",
                source=source.name,
                url=err_url,
                error=str(err),
            )

        sanitized_items: List[SanitizedNewsItem] = []
        for item in normalized_items:
            sanitized = sanitize_ingested_entry(item.raw_metadata, item, legal_meta)
            sanitized_items.append(sanitized)
            logger.info(
                "news_ingest_sanitized_item",
                source=source.name,
                url=sanitized.url,
            )
            logger.info(
                "news_ingest_legal_sanitized",
                source=source.name,
                url=sanitized.url,
                legal_checks_passed=True,
                legal=legal_meta,
            )

        deduped_items: List[SanitizedNewsItem] = []
        for sanitized in sanitized_items:
            if await self._is_recent_duplicate(sanitized.url):
                logger.info(
                    "news_ingest_duplicate_skipped",
                    source=source.name,
                    url=sanitized.url,
                )
                continue
            deduped_items.append(sanitized)

        rows = [self._sanitized_item_to_row(source, item) for item in deduped_items]

        inserted = await self._persist_items(rows)
        await self._mark_source_success(source, inserted)

        return {
            "source_key": source_key,
            "skipped": False,
            "inserted": inserted,
            "failed_items": len(norm_errors),
        }

    async def _is_recent_duplicate(self, link: str) -> bool:
        if not link:
            return False
        row = await fetchrow(
            """
            SELECT 1
            FROM raw_ingested_news
            WHERE link = $1
              AND published_at >= NOW() - INTERVAL '24 hours'
            LIMIT 1
            """,
            link,
        )
        return bool(row)


async def ingest_all_sources(limit: Optional[int] = None) -> Dict[str, Any]:
    sources = get_all_news_sources()
    if limit is not None:
        sources = sources[:limit]

    if not sources:
        logger.info("news_ingest_no_sources_configured")
        return {
            "total_sources": 0,
            "total_inserted": 0,
            "total_failed_items": 0,
            "total_skipped": 0,
            "failed_feeds": 0,
            "degraded": False,
        }

    async with NewsIngestService() as service:
        results = await asyncio.gather(*(service.ingest_source(src) for src in sources))

    total_inserted = sum(r.get("inserted", 0) for r in results)
    total_failed_items = sum(r.get("failed_items", 0) for r in results)
    total_skipped = sum(1 for r in results if r.get("skipped"))
    failed_feeds = sum(
        1
        for r in results
        if not r.get("skipped") and r.get("inserted", 0) == 0 and r.get("failed_items", 0) > 0
    )
    degraded = False
    if sources and failed_feeds / len(sources) > 0.5:
        degraded = True

    logger.info(
        "news_ingest_summary",
        total_sources=len(sources),
        total_inserted=total_inserted,
        total_failed_items=total_failed_items,
        total_skipped=total_skipped,
        failed_feeds=failed_feeds,
        degraded=degraded,
    )

    return {
        "total_sources": len(sources),
        "total_inserted": total_inserted,
        "total_failed_items": total_failed_items,
        "total_skipped": total_skipped,
        "failed_feeds": failed_feeds,
        "degraded": degraded,
    }

