# Backend/app/workers/news_trending_scraper_worker.py
"""
X Trending Topics Scraper Worker

Fetches trending topics from trends24.in and caches them for the news feed.
Runs hourly to keep trending topics up-to-date.

This worker replaces the X API integration (which requires paid tier access)
with a scraper that uses trends24.in as the data source.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
from typing import Dict, Any

# Path setup
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent
BACKEND_DIR = APP_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.db_service import init_db_pool
from services.news_trending_x_scraper import fetch_trending_topics_scraper
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    finish_worker_run,
)

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="news_trending_scraper")


async def scrape_and_cache_trending_topics(
    countries: list[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Scrape trending topics for specified countries and cache them.
    
    Args:
        countries: List of country codes (e.g., ["nl", "tr"]). Defaults to ["nl"]
        limit: Maximum number of topics per country
        
    Returns:
        Dictionary with scraping statistics
    """
    if countries is None:
        countries = ["nl"]  # Default to Netherlands
    
    stats = {
        "countries_processed": 0,
        "total_topics_found": 0,
        "countries_with_topics": 0,
        "countries_failed": 0,
        "results": {},
    }
    
    for country in countries:
        try:
            logger.info("scraping_trending_topics", country=country, limit=limit)
            
            result = await fetch_trending_topics_scraper(
                limit=limit,
                country=country,
            )
            
            topics_count = len(result.topics)
            stats["total_topics_found"] += topics_count
            stats["countries_processed"] += 1
            
            if topics_count > 0:
                stats["countries_with_topics"] += 1
                logger.info(
                    "trending_topics_scraped",
                    country=country,
                    topics_count=topics_count,
                )
            else:
                stats["countries_failed"] += 1
                logger.warning(
                    "trending_topics_scrape_failed",
                    country=country,
                    unavailable_reason=result.unavailable_reason,
                )
            
            stats["results"][country] = {
                "topics_count": topics_count,
                "unavailable_reason": result.unavailable_reason,
            }
            
        except Exception as exc:
            stats["countries_failed"] += 1
            logger.error(
                "trending_topics_scrape_error",
                country=country,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            stats["results"][country] = {
                "topics_count": 0,
                "error": str(exc),
            }
    
    return stats


async def run_once() -> Dict[str, Any]:
    """Run one iteration of trending topics scraping."""
    run_id = None
    try:
        run_id = await start_worker_run("news_trending_scraper")
        await mark_worker_run_running(run_id)
    except Exception as e:
        logger.warning("failed_to_start_worker_run", error=str(e))
    
    with with_run_id():
        # Scrape trending topics for supported countries
        # Add more countries as needed
        countries = ["nl", "tr"]  # Netherlands and Turkey
        
        stats = await scrape_and_cache_trending_topics(
            countries=countries,
            limit=20,
        )
        
        logger.info(
            "trending_scraper_complete",
            countries_processed=stats["countries_processed"],
            total_topics=stats["total_topics_found"],
            countries_with_topics=stats["countries_with_topics"],
            countries_failed=stats["countries_failed"],
        )
    
    if run_id:
        try:
            await finish_worker_run(run_id, "completed", stats)
        except Exception as e:
            logger.warning("failed_to_finish_worker_run", error=str(e))
    
    return stats


async def run_forever(interval_seconds: int = 3600) -> None:  # 1 hour default
    """Run worker continuously."""
    await init_db_pool()
    
    logger.info("news_trending_scraper_worker_started", interval_seconds=interval_seconds)
    
    while True:
        try:
            await run_once()
        except Exception as e:
            logger.error("news_trending_scraper_worker_error", error=str(e), exc_info=True)
        
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="X Trending Topics Scraper Worker")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=3600, help="Interval in seconds (default: 3600 = 1 hour)")
    
    args = parser.parse_args()
    
    if args.once:
        asyncio.run(run_once())
    else:
        asyncio.run(run_forever(interval_seconds=args.interval))
