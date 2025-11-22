from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, List, Optional, Mapping
from uuid import UUID

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.db_service import execute, fetch
from services.news_classification_service import NewsClassificationResult, NewsClassificationService
from services.news_location_tagging import derive_location_tag
from services.ai_config_service import get_ai_config, initialize_ai_config
from services.news_feed_rules import FeedType, FeedThresholds, is_in_feed, thresholds_from_config
from services.worker_runs_service import (
    finish_worker_run,
    mark_worker_run_running,
    start_worker_run,
    update_worker_run_progress,
)

configure_logging(service_name="worker")
logger = get_logger().bind(worker="news_classify_bot")
CLASSIFIED_BY = "news_classify_bot"


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NewsClassifyBot — classify pending news rows with AI.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of rows to classify.")
    parser.add_argument("--model", type=str, default=None, help="Optional OpenAI model override.")
    parser.add_argument(
        "--worker-run-id",
        type=_parse_worker_run_id,
        default=None,
        help="Existing worker_runs UUID (optional).",
    )
    return parser.parse_args()


async def _load_feed_thresholds() -> FeedThresholds:
    config = await get_ai_config()
    if not config:
        config = await initialize_ai_config()
    return thresholds_from_config(config)


def _evaluate_feeds_for_row(
    *,
    row: Mapping[str, Any],
    result: NewsClassificationResult,
    location_tag: str,
    thresholds: FeedThresholds,
) -> Dict[str, bool]:
    enriched = dict(row)
    enriched.update(
        {
            "relevance_diaspora": result.relevance_diaspora,
            "relevance_nl": result.relevance_nl,
            "relevance_tr": result.relevance_tr,
            "relevance_geo": result.relevance_geo,
            "language": (result.language or row.get("language")),
            "location_tag": location_tag,
        }
    )
    source_meta = {
        "category": row.get("category"),
        "region": row.get("region"),
        "language": enriched.get("language"),
    }
    return {
        feed.value: is_in_feed(feed, enriched, source_meta, thresholds)
        for feed in FeedType
    }


async def _fetch_pending_news(limit: int) -> List[Dict[str, Any]]:
    rows = await fetch(
        """
        SELECT
            id,
            title,
            summary,
            content,
            source_key,
            language,
            category,
            region,
            raw_entry
        FROM raw_ingested_news
        WHERE processing_state = 'pending'
        ORDER BY fetched_at ASC
        LIMIT $1
        """,
        max(0, int(limit)),
    )
    return [dict(r) for r in rows]


async def _mark_classification_success(
    row_id: int,
    result: NewsClassificationResult,
    location_tag: str,
    location_context: Dict[str, Any],
) -> None:
    topics_json = json.dumps(result.topics or [], ensure_ascii=False)
    detected_language = (result.language or "").strip()
    location_mentions_json = json.dumps(
        [mention.model_dump() for mention in (result.location_mentions or [])],
        ensure_ascii=False,
    )
    location_context_json = json.dumps(location_context or {}, ensure_ascii=False)
    await execute(
        """
        UPDATE raw_ingested_news
        SET
            relevance_diaspora = $2,
            relevance_nl = $3,
            relevance_tr = $4,
            relevance_geo = $5,
            location_mentions = CAST($6 AS JSONB),
            topics = CAST($7 AS JSONB),
            location_tag = $8,
            location_context = CAST($9 AS JSONB),
            language = COALESCE(NULLIF($10, ''), language),
            classified_at = NOW(),
            classified_by = $11,
            processing_state = 'classified',
            processing_errors = NULL
        WHERE id = $1
        """,
        int(row_id),
        float(result.relevance_diaspora),
        float(result.relevance_nl),
        float(result.relevance_tr),
        float(result.relevance_geo),
        location_mentions_json,
        topics_json,
        location_tag,
        location_context_json,
        detected_language or None,
        CLASSIFIED_BY,
    )


async def _mark_classification_error(row_id: int, error_meta: Dict[str, Any]) -> None:
    payload = {
        "reason": error_meta.get("error", "classification_failed"),
        "meta": error_meta,
    }
    await execute(
        """
        UPDATE raw_ingested_news
        SET
            processing_state = 'error_ai',
            processing_errors = CAST($2 AS JSONB),
            classified_at = NOW(),
            classified_by = $3
        WHERE id = $1
        """,
        int(row_id),
        json.dumps(payload, ensure_ascii=False),
        CLASSIFIED_BY,
    )


def _extract_summary(row: Dict[str, Any]) -> Optional[str]:
    summary = row.get("summary")
    if summary:
        return summary
    raw_entry = row.get("raw_entry") or {}
    if isinstance(raw_entry, dict):
        return raw_entry.get("summary") or raw_entry.get("description")
    return None


def _extract_content(row: Dict[str, Any]) -> Optional[str]:
    content = row.get("content")
    if content:
        return content
    raw_entry = row.get("raw_entry") or {}
    if isinstance(raw_entry, dict):
        value = raw_entry.get("content")
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, dict):
                return first.get("value")
        if isinstance(value, dict):
            return value.get("value")
    return None


async def process_pending_news(
    *,
    limit: int,
    model: Optional[str],
    worker_run_id: Optional[UUID],
    service: Optional[NewsClassificationService] = None,
) -> Dict[str, int]:
    rows = await _fetch_pending_news(limit)
    total = len(rows)
    counters = {"total": total, "classified": 0, "errors": 0}
    if not rows:
        return counters

    classifier = service or NewsClassificationService(model=model)

    thresholds = await _load_feed_thresholds()

    for idx, row in enumerate(rows, start=1):
        if worker_run_id and total > 0:
            percent = min(99, int(idx * 100 / total))
            await update_worker_run_progress(worker_run_id, percent)

        summary = _extract_summary(row)
        content = _extract_content(row)

        try:
            result, meta = classifier.classify_news_item(
                news_id=int(row["id"]),
                title=row.get("title") or "Untitled",
                summary=summary,
                content=content,
                source_key=row.get("source_key") or "unknown",
                language_hint=row.get("language"),
            )
        except Exception as exc:  # pragma: no cover - defensive catch
            logger.error("news_classify_call_failed", news_id=row.get("id"), error=str(exc))
            result = None
            meta = {"error": str(exc), "ok": False}

        if result is not None:
            location_tag, location_context = derive_location_tag(
                title=row.get("title") or "Untitled",
                summary=summary,
                content=content,
                ai_mentions=result.location_mentions,
            )
            feed_hits = _evaluate_feeds_for_row(
                row=row,
                result=result,
                location_tag=location_tag,
                thresholds=thresholds,
            )
            logger.debug(
                "news_feed_threshold_preview",
                news_id=row.get("id"),
                feeds=[ft for ft, ok in feed_hits.items() if ok],
            )
            await _mark_classification_success(int(row["id"]), result, location_tag, location_context)
            counters["classified"] += 1
        else:
            counters["errors"] += 1
            await _mark_classification_error(int(row["id"]), meta or {"error": "unknown"})

    return counters


async def run_classify(limit: int, model: Optional[str], worker_run_id: Optional[UUID]) -> int:
    run_id = worker_run_id
    if run_id is None:
        run_id = await start_worker_run(bot="news_classify", city=None, category=None)

    await mark_worker_run_running(run_id)
    await update_worker_run_progress(run_id, 5)

    counters: Dict[str, int] = {}
    progress = 5
    try:
        counters = await process_pending_news(limit=limit, model=model, worker_run_id=run_id)
        progress = 100
        await finish_worker_run(run_id, "finished", progress, counters, None)
        logger.info(
            "news_classify_bot_finished",
            total=counters.get("total"),
            classified=counters.get("classified"),
            errors=counters.get("errors"),
        )
        return 0
    except Exception as exc:
        logger.error("news_classify_bot_failed", error=str(exc))
        await finish_worker_run(run_id, "failed", progress, counters or None, str(exc))
        return 1


async def main_async() -> int:
    args = parse_args()
    with with_run_id():
        return await run_classify(limit=args.limit, model=args.model, worker_run_id=args.worker_run_id)


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()


