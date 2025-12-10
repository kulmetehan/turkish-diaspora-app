from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from typing import Dict, List, Optional, Sequence
from uuid import UUID

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from app.models.news_extraction import ExtractedNewsItem
from app.models.news_pages_raw import NewsPageRaw
from app.models.news_sources import NewsSource, get_all_news_sources
from services.db_service import execute
from services.news_extraction_service import NewsExtractionService
from services.news_pages_raw_service import (
    fetch_pending_news_pages,
    update_news_page_processing_state,
)
from services.worker_runs_service import (
    finish_worker_run,
    mark_worker_run_running,
    start_worker_run,
    update_worker_run_progress,
)

configure_logging(service_name="worker")
logger = get_logger().bind(worker="news_ai_extractor_bot")

DEFAULT_LIMIT = 20
DEFAULT_CHUNK_SIZE = 16000


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:  # pragma: no cover
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NewsAIExtractorBot — turn HTML pages into raw_ingested_news rows via OpenAI."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum number of pending pages to process (default: 20).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Max characters per HTML chunk sent to OpenAI (default: 16000).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Optional OpenAI model override.",
    )
    parser.add_argument(
        "--worker-run-id",
        type=_parse_worker_run_id,
        default=None,
        help="Existing worker_runs UUID (optional).",
    )
    return parser.parse_args()


def _chunk_html(body: str, chunk_size: int) -> List[str]:
    """Split HTML into chunks for processing."""
    text = body.strip()
    if not text:
        return []
    if chunk_size <= 0 or len(text) <= chunk_size:
        return [text]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _get_source_by_key_cached(
    source_key: str,
    cache: Dict[str, NewsSource],
) -> Optional[NewsSource]:
    """Get news source by key with caching."""
    if source_key in cache:
        return cache[source_key]
    all_sources = get_all_news_sources()
    for source in all_sources:
        if source.key == source_key:
            cache[source_key] = source
            return source
    return None


def _compute_ingest_hash(
    *,
    source_key: str,
    url: str,
    published_at,
) -> str:
    """Compute ingest hash for deduplication."""
    parts = [
        source_key.strip().lower(),
        url.strip().lower(),
        published_at.isoformat() if hasattr(published_at, "isoformat") else str(published_at),
    ]
    joined = "|".join(parts)
    return hashlib.sha1(joined.encode("utf-8", "ignore")).hexdigest()


def _dedupe_articles(articles: Sequence[ExtractedNewsItem]) -> List[ExtractedNewsItem]:
    """Deduplicate articles by URL and published_at."""
    seen: Dict[tuple, ExtractedNewsItem] = {}
    for article in articles:
        key = (
            article.url.strip().lower(),
            article.published_at.isoformat(),
        )
        seen[key] = article
    return list(seen.values())


async def _persist_article(
    *,
    source: NewsSource,
    article: ExtractedNewsItem,
    source_page_id: int,
    source_page_url: str,
    chunk_count: int,
) -> bool:
    """
    Persist extracted article to raw_ingested_news.
    
    Returns True if inserted, False if duplicate.
    """
    source_key = source.key
    ingest_hash = _compute_ingest_hash(
        source_key=source_key,
        url=article.url,
        published_at=article.published_at,
    )

    raw_entry = {
        "extracted_via": "news_ai_extractor_bot",
        "source_page_id": source_page_id,
        "source_page_url": source_page_url,
        "chunk_count": chunk_count,
        "extracted_article": article.model_dump(mode="json"),
    }
    raw_entry_json = json.dumps(raw_entry, ensure_ascii=False)

    try:
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
            ON CONFLICT (source_key, ingest_hash) DO NOTHING
            RETURNING id;
            """,
            source_key,
            source.name,
            source.url,
            source.category,
            source.language,
            source.region,
            article.title,
            article.snippet,
            None,  # content
            None,  # author
            article.url,
            article.image_url,
            article.published_at,
            ingest_hash,
            raw_entry_json,
        )
        if result and "INSERT" in result.upper():
            return True
        return False
    except Exception as exc:
        logger.error(
            "news_ai_extractor_persist_error",
            source_key=source_key,
            url=article.url,
            error=str(exc),
        )
        return False


async def _process_page(
    page: NewsPageRaw,
    *,
    chunk_size: int,
    extraction_service: NewsExtractionService,
    source_cache: Dict[str, NewsSource],
    counters: Dict[str, int],
) -> None:
    """Process a single news page for AI extraction."""
    source = _get_source_by_key_cached(page.news_source_key, source_cache)
    if source is None:
        await update_news_page_processing_state(
            page.id,
            state="error_extract",
            errors={"reason": "missing_source", "source_key": page.news_source_key},
        )
        counters["pages_failed"] += 1
        logger.error(
            "news_ai_extractor_missing_source",
            page_id=page.id,
            news_source_key=page.news_source_key,
        )
        return

    chunks = _chunk_html(page.response_body, chunk_size)
    if not chunks:
        await update_news_page_processing_state(
            page.id,
            state="error_extract",
            errors={"reason": "empty_body"},
        )
        counters["pages_failed"] += 1
        return

    extracted_articles: List[ExtractedNewsItem] = []
    for idx, chunk in enumerate(chunks):
        try:
            payload, _meta = extraction_service.extract_news_from_html(
                html=chunk,
                source_key=source.key,
                page_url=page.page_url,
            )
        except Exception as exc:
            await update_news_page_processing_state(
                page.id,
                state="error_extract",
                errors={"reason": "openai_error", "error": str(exc), "chunk": idx},
            )
            counters["pages_failed"] += 1
            logger.warning(
                "news_ai_extractor_chunk_failed",
                page_id=page.id,
                chunk_index=idx,
                error=str(exc),
            )
            return
        extracted_articles.extend(payload.articles)

    deduped = _dedupe_articles(extracted_articles)
    counters["articles_extracted_total"] += len(deduped)
    new_articles = 0

    for article in deduped:
        inserted = await _persist_article(
            source=source,
            article=article,
            source_page_id=page.id,
            source_page_url=page.page_url,
            chunk_count=len(chunks),
        )
        if inserted:
            new_articles += 1
            counters["articles_created_new"] += 1
        else:
            counters["articles_skipped_existing"] += 1

    await update_news_page_processing_state(page.id, state="extracted", errors=None)
    counters["pages_processed"] += 1
    logger.info(
        "news_ai_extractor_page_complete",
        page_id=page.id,
        new_articles=new_articles,
        total_articles=len(deduped),
    )


async def run_extractor(
    *,
    limit: int,
    chunk_size: int,
    model: Optional[str],
    worker_run_id: Optional[UUID],
) -> int:
    """Run the news AI extractor bot."""
    run_id = worker_run_id or await start_worker_run(
        bot="news_ai_extractor", city=None, category=None
    )
    await mark_worker_run_running(run_id)
    progress = 5
    await update_worker_run_progress(run_id, progress)

    counters: Dict[str, int] = {
        "pages_fetched": 0,
        "pages_processed": 0,
        "pages_failed": 0,
        "articles_extracted_total": 0,
        "articles_created_new": 0,
        "articles_skipped_existing": 0,
    }

    try:
        pages = await fetch_pending_news_pages(limit=max(1, limit))
        counters["pages_fetched"] = len(pages)
        if not pages:
            await finish_worker_run(run_id, "finished", 100, counters, None)
            logger.info("news_ai_extractor_no_pending_pages")
            return 0

        extraction_service = NewsExtractionService(model=model)
        source_cache: Dict[str, NewsSource] = {}
        for idx, page in enumerate(pages, start=1):
            progress = 5 + int(idx * 95 / max(len(pages), 1))
            await update_worker_run_progress(run_id, min(progress, 99))
            await _process_page(
                page,
                chunk_size=chunk_size,
                extraction_service=extraction_service,
                source_cache=source_cache,
                counters=counters,
            )

        await finish_worker_run(run_id, "finished", 100, counters, None)
        return 0
    except Exception as exc:
        logger.error("news_ai_extractor_failed", error=str(exc))
        await finish_worker_run(run_id, "failed", progress, counters or None, str(exc))
        return 1


async def main_async() -> int:
    args = parse_args()
    with with_run_id():
        return await run_extractor(
            limit=args.limit,
            chunk_size=max(1, args.chunk_size),
            model=args.model,
            worker_run_id=args.worker_run_id,
        )


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

