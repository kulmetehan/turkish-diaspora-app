# Backend/app/workers/news_spotify_scraper_worker.py
"""
Spotify Viral 50 Scraper Worker

Fetches tracks from Spotify Viral 50 playlists and caches them for the news feed.
Runs daily to keep tracks up-to-date.
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
from services.news_trending_spotify_scraper import fetch_spotify_tracks_scraper
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    finish_worker_run,
)

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="news_spotify_scraper")


async def scrape_and_cache_spotify_tracks(
    countries: list[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Scrape Spotify tracks for specified countries and cache them.
    
    Args:
        countries: List of country codes (e.g., ["nl", "tr"]). Defaults to ["nl"]
        limit: Maximum number of tracks per country
        
    Returns:
        Dictionary with scraping statistics
    """
    if countries is None:
        countries = ["nl"]  # Default to Netherlands
    
    stats = {
        "countries_processed": 0,
        "total_tracks_found": 0,
        "countries_with_tracks": 0,
        "countries_failed": 0,
        "results": {},
    }
    
    for country in countries:
        try:
            logger.info("scraping_spotify_tracks", country=country, limit=limit)
            
            result = await fetch_spotify_tracks_scraper(
                limit=limit,
                country=country,
            )
            
            tracks_count = len(result.tracks)
            stats["total_tracks_found"] += tracks_count
            stats["countries_processed"] += 1
            
            if tracks_count > 0:
                stats["countries_with_tracks"] += 1
                logger.info(
                    "spotify_tracks_scraped",
                    country=country,
                    tracks_count=tracks_count,
                )
            else:
                stats["countries_failed"] += 1
                logger.warning(
                    "spotify_tracks_scrape_failed",
                    country=country,
                    unavailable_reason=result.unavailable_reason,
                )
            
            stats["results"][country] = {
                "tracks_count": tracks_count,
                "unavailable_reason": result.unavailable_reason,
            }
            
        except Exception as exc:
            stats["countries_failed"] += 1
            logger.error(
                "spotify_tracks_scrape_error",
                country=country,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            stats["results"][country] = {
                "tracks_count": 0,
                "error": str(exc),
            }
    
    return stats


async def run_once() -> Dict[str, Any]:
    """Run one iteration of Spotify tracks scraping."""
    run_id = None
    try:
        run_id = await start_worker_run("news_spotify_scraper")
        await mark_worker_run_running(run_id)
    except Exception as e:
        logger.warning("failed_to_start_worker_run", error=str(e))
    
    with with_run_id():
        # Scrape Spotify tracks for supported countries
        countries = ["nl", "tr"]  # Netherlands and Turkey
        
        stats = await scrape_and_cache_spotify_tracks(
            countries=countries,
            limit=20,
        )
        
        logger.info(
            "spotify_scraper_complete",
            countries_processed=stats["countries_processed"],
            total_tracks=stats["total_tracks_found"],
            countries_with_tracks=stats["countries_with_tracks"],
            countries_failed=stats["countries_failed"],
        )
    
    if run_id:
        try:
            # Calculate progress percentage based on success rate
            progress = 100 if stats["countries_failed"] == 0 else int((stats["countries_with_tracks"] / stats["countries_processed"]) * 100) if stats["countries_processed"] > 0 else 0
            await finish_worker_run(
                run_id,
                "finished" if stats["countries_failed"] == 0 else "failed",
                progress,
                counters=stats,
            )
        except Exception as e:
            logger.warning("failed_to_finish_worker_run", error=str(e))
    
    return stats


async def run_forever(interval_seconds: int = 86400) -> None:  # 24 hours default
    """Run worker continuously."""
    await init_db_pool()
    
    logger.info("news_spotify_scraper_worker_started", interval_seconds=interval_seconds)
    
    while True:
        try:
            await run_once()
        except Exception as e:
            logger.error("news_spotify_scraper_worker_error", error=str(e), exc_info=True)
        
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spotify Viral 50 Scraper Worker")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=86400, help="Interval in seconds (default: 86400 = 24 hours)")
    
    args = parser.parse_args()
    
    if args.once:
        asyncio.run(run_once())
    else:
        asyncio.run(run_forever(interval_seconds=args.interval))

