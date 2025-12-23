# app/workers/content_curation_bot.py
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

# ---------------------------------------------------------------------------
# Pathing zodat 'app.*' en 'services.*' werken
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent
BACKEND_DIR = APP_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# --- Uniform logging ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.content_curation_service import ContentCurationService
from services.db_service import execute, fetch, fetchrow
from services.news_service import list_news_by_feed, FeedType
from services.events_public_service import list_public_events
from services.worker_runs_service import (
    finish_worker_run,
    mark_worker_run_running,
    start_worker_run,
    update_worker_run_progress,
)
from app.core.location_filters import get_verified_filter_sql

configure_logging(service_name="worker")
logger = get_logger().bind(worker="content_curation_bot")

# News categories mapping (UI category -> RSS category)
NEWS_CATEGORIES_NL = {
    "general": "nl_national",
    "sport": "nl_national_sport",
    "economie": "nl_national_economie",
    "cultuur": "nl_national_cultuur",
}
NEWS_CATEGORIES_TR = {
    "general": "tr_national",
    "sport": "tr_national_sport",
    "economie": "tr_national_economie",
    "magazin": "tr_national_magazin",  # Note: "cultuur" in UI maps to "magazin" for TR
}
NEWS_ITEMS_PER_CATEGORY = 5

# Location category labels (Dutch)
CATEGORY_LABELS = {
    "bakery": "bakkers",
    "restaurant": "restaurants",
    "supermarket": "supermarkten",
    "barber": "kappers",
    "butcher": "slagers",
    "mosque": "moskeeën",
    "travel_agency": "reisbureaus",
    "fast_food": "fastfoodzaken",
    "cafe": "cafés",
}


async def curate_news() -> Dict[str, Any]:
    """
    Haal laatste 5 items per categorie/taal, rank met AI, sla top 3 op.
    """
    logger.info("curate_news_started")
    
    # Initialize AI service
    curation_service = ContentCurationService()
    
    # Collect news items from all categories and languages
    all_news_items: List[Dict[str, Any]] = []
    
    # NL feed categories
    for ui_category, rss_category in NEWS_CATEGORIES_NL.items():
        try:
            items, _total = await list_news_by_feed(
                FeedType.NL,
                limit=NEWS_ITEMS_PER_CATEGORY,
                offset=0,
                categories=[rss_category],
            )
            
            # Convert NewsItem to dict for AI service
            for item in items:
                all_news_items.append({
                    "id": item.id,
                    "title": item.title,
                    "snippet": item.snippet,
                    "source": item.source,
                    "tags": item.tags,
                    "category": ui_category,
                    "language": "nl",
                    "published_at": item.published_at.isoformat() if hasattr(item.published_at, "isoformat") else str(item.published_at),
                    "url": item.url,
                    "image_url": item.image_url,
                })
        except Exception as e:
            logger.warning(
                "failed_to_fetch_news_batch",
                category=ui_category,
                language="nl",
                error=str(e),
            )
    
    # TR feed categories
    for ui_category, rss_category in NEWS_CATEGORIES_TR.items():
        try:
            items, _total = await list_news_by_feed(
                FeedType.TR,
                limit=NEWS_ITEMS_PER_CATEGORY,
                offset=0,
                categories=[rss_category],
            )
            
            # Convert NewsItem to dict for AI service
            for item in items:
                all_news_items.append({
                    "id": item.id,
                    "title": item.title,
                    "snippet": item.snippet,
                    "source": item.source,
                    "tags": item.tags,
                    "category": ui_category,
                    "language": "tr",
                    "published_at": item.published_at.isoformat() if hasattr(item.published_at, "isoformat") else str(item.published_at),
                    "url": item.url,
                    "image_url": item.image_url,
                })
        except Exception as e:
            logger.warning(
                "failed_to_fetch_news_batch",
                category=ui_category,
                language="tr",
                error=str(e),
            )
    
    if not all_news_items:
        logger.warning("no_news_items_found")
        return {"items_ranked": 0, "items_stored": 0, "ai_calls": 0}
    
    # Rank with AI
    logger.info("ranking_news_items", count=len(all_news_items))
    ranked_items = await curation_service.rank_news_items(all_news_items)
    
    # Get top 3
    top_3 = ranked_items[:3]
    
    # Map back to original items
    items_by_id = {item["id"]: item for item in all_news_items}
    ranked_data = []
    for ranked in top_3:
        original = items_by_id.get(ranked.news_id)
        if original:
            ranked_data.append({
                **original,
                "relevance_score": ranked.relevance_score,
                "reason": ranked.reason,
            })
    
    # Store in database
    expires_at = datetime.now(timezone.utc) + timedelta(hours=6)
    metadata = {
        "total_ranked": len(ranked_items),
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "model_used": curation_service.model,
    }
    
    await execute(
        """
        INSERT INTO feed_curated_content (content_type, ranked_items, metadata, expires_at)
        VALUES ($1, $2::jsonb, $3::jsonb, $4)
        """,
        "news",
        json.dumps(ranked_data),
        json.dumps(metadata),
        expires_at,
    )
    
    logger.info(
        "curate_news_finished",
        items_ranked=len(ranked_items),
        items_stored=len(ranked_data),
    )
    
    return {
        "items_ranked": len(ranked_items),
        "items_stored": len(ranked_data),
        "ai_calls": (len(all_news_items) + 19) // 20,  # Batch size 20
    }


async def curate_events() -> Dict[str, Any]:
    """
    Haal alle aankomende events op, rank met AI, sla top 3 op.
    """
    logger.info("curate_events_started")
    
    # Initialize AI service
    curation_service = ContentCurationService()
    
    # Fetch all upcoming events
    try:
        events, _total = await list_public_events(
            city=None,
            date_from=None,
            date_to=None,
            categories=None,
            limit=1000,  # Get many events
            offset=0,
        )
    except Exception as e:
        logger.error("failed_to_fetch_events", error=str(e))
        return {"items_ranked": 0, "items_stored": 0, "ai_calls": 0}
    
    if not events:
        logger.warning("no_events_found")
        return {"items_ranked": 0, "items_stored": 0, "ai_calls": 0}
    
    # Convert EventItem to dict for AI service
    events_dict = []
    for event in events:
        events_dict.append({
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "location_text": event.location_text,
            "category_key": event.category_key,
            "city_key": event.city_key,
        })
    
    # Rank with AI
    logger.info("ranking_events", count=len(events_dict))
    ranked_items = await curation_service.rank_events(events_dict)
    
    # Get top 3
    top_3 = ranked_items[:3]
    
    # Map back to original events
    events_by_id = {event.id: event for event in events}
    ranked_data = []
    for ranked in top_3:
        original = events_by_id.get(ranked.event_id)
        if original:
            ranked_data.append({
                "id": original.id,
                "title": original.title,
                "description": original.description,
                "start_time_utc": original.start_time_utc.isoformat(),
                "end_time_utc": original.end_time_utc.isoformat() if original.end_time_utc else None,
                "city_key": original.city_key,
                "category_key": original.category_key,
                "location_text": original.location_text,
                "url": original.url,
                "source_key": original.source_key,
                "relevance_score": ranked.relevance_score,
                "reason": ranked.reason,
            })
    
    # Store in database
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    metadata = {
        "total_ranked": len(ranked_items),
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "model_used": curation_service.model,
    }
    
    await execute(
        """
        INSERT INTO feed_curated_content (content_type, ranked_items, metadata, expires_at)
        VALUES ($1, $2::jsonb, $3::jsonb, $4)
        """,
        "events",
        json.dumps(ranked_data),
        json.dumps(metadata),
        expires_at,
    )
    
    logger.info(
        "curate_events_finished",
        items_ranked=len(ranked_items),
        items_stored=len(ranked_data),
    )
    
    return {
        "items_ranked": len(ranked_items),
        "items_stored": len(ranked_data),
        "ai_calls": (len(events_dict) + 19) // 20,  # Batch size 20
    }


async def curate_location_stats() -> Dict[str, Any]:
    """
    Haal location counts op, maak random selectie van 2-3 categorieën, genereer formatted text.
    """
    logger.info("curate_location_stats_started")
    
    # Get total count using verified filter
    verified_filter_sql, verified_params = get_verified_filter_sql(bbox=None, alias="l")
    
    total_row = await fetchrow(
        f"""
        SELECT COUNT(*)::int AS total
        FROM locations l
        WHERE {verified_filter_sql}
        """,
        *verified_params,
    )
    total = int(total_row["total"]) if total_row else 0
    
    # Get counts per category
    category_counts = await fetch(
        f"""
        SELECT 
            l.category,
            COUNT(*)::int AS count
        FROM locations l
        WHERE {verified_filter_sql}
          AND l.category IS NOT NULL
        GROUP BY l.category
        HAVING COUNT(*) > 0
        ORDER BY COUNT(*) DESC
        """,
        *verified_params,
    )
    
    # Convert to list of dicts
    categories_with_counts = []
    for row in category_counts:
        category = row.get("category")
        count = int(row.get("count", 0))
        if category and count > 0:
            categories_with_counts.append({
                "category": category,
                "label": CATEGORY_LABELS.get(category, category),
                "count": count,
            })
    
    # Random selectie van 2-3 categorieën
    if len(categories_with_counts) > 0:
        num_to_select = min(random.randint(2, 3), len(categories_with_counts))
        selected = random.sample(categories_with_counts, num_to_select)
    else:
        selected = []
    
    # Genereer formatted text
    if selected:
        total_str = f"{total:,}".replace(",", ".")  # Dutch number formatting
        parts = [f"{total_str} Turkse locaties in Nederland"]
        category_parts = []
        for cat in selected:
            count_str = f"{cat['count']:,}".replace(",", ".")
            category_parts.append(f"{count_str} {cat['label']}")
        
        if len(category_parts) == 1:
            formatted_text = f"{parts[0]}. Waarvan {category_parts[0]}."
        elif len(category_parts) == 2:
            formatted_text = f"{parts[0]}. Waarvan {category_parts[0]} en {category_parts[1]}."
        else:
            formatted_text = f"{parts[0]}. Waarvan {', '.join(category_parts[:-1])} en {category_parts[-1]}."
    else:
        total_str = f"{total:,}".replace(",", ".")
        formatted_text = f"{total_str} Turkse locaties in Nederland"
    
    # Store in database
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    metadata = {
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    
    ranked_data = {
        "total": total,
        "categories": selected,
        "formatted_text": formatted_text,
    }
    
    await execute(
        """
        INSERT INTO feed_curated_content (content_type, ranked_items, metadata, expires_at)
        VALUES ($1, $2::jsonb, $3::jsonb, $4)
        """,
        "location_stats",
        json.dumps(ranked_data),
        json.dumps(metadata),
        expires_at,
    )
    
    logger.info(
        "curate_location_stats_finished",
        total=total,
        categories_selected=len(selected),
    )
    
    return {
        "total": total,
        "categories_selected": len(selected),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ContentCurationBot — AI-curated content for feed page dashboard cards"
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["news", "events_locations"],
        required=True,
        help="Type of curation to run: 'news' or 'events_locations'",
    )
    parser.add_argument(
        "--worker-run-id",
        type=str,
        help="Optional worker run UUID for orchestration integration.",
    )
    return parser.parse_args()


async def run_curation(
    curation_type: str,
    worker_run_id: Optional[UUID],
) -> int:
    run_id = worker_run_id
    if run_id is None:
        run_id = await start_worker_run(bot="content_curation", city=None, category=None)
    
    await mark_worker_run_running(run_id)
    await update_worker_run_progress(run_id, 5)
    
    counters: Dict[str, Any] = {}
    progress = 5
    
    try:
        if curation_type == "news":
            await update_worker_run_progress(run_id, 30)
            result = await curate_news()
            counters = result
            progress = 100
        elif curation_type == "events_locations":
            await update_worker_run_progress(run_id, 30)
            events_result = await curate_events()
            await update_worker_run_progress(run_id, 60)
            locations_result = await curate_location_stats()
            counters = {
                "events": events_result,
                "locations": locations_result,
            }
            progress = 100
        else:
            raise ValueError(f"Unknown curation type: {curation_type}")
        
        await finish_worker_run(run_id, "finished", progress, counters, None)
        logger.info(
            "content_curation_bot_finished",
            type=curation_type,
            counters=counters,
        )
        return 0
    except Exception as exc:
        logger.error("content_curation_bot_failed", type=curation_type, error=str(exc))
        await finish_worker_run(run_id, "failed", progress, counters or None, str(exc))
        return 1


async def main_async() -> int:
    args = parse_args()
    
    # Parse worker_run_id if provided
    worker_run_id = None
    if args.worker_run_id:
        try:
            worker_run_id = UUID(args.worker_run_id)
        except ValueError:
            logger.warning("invalid_worker_run_id", value=args.worker_run_id)
    
    with with_run_id():
        return await run_curation(args.type, worker_run_id)


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()








