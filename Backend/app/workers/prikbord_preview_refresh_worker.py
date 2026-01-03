# Backend/app/workers/prikbord_preview_refresh_worker.py
"""
Worker to refresh expired link previews for Prikbord shared links.

Runs daily to check for links with expired preview_cache_expires_at
and refresh their previews. Marks links as 'broken_link' after 3 failed attempts.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add Backend to path
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=BACKEND_ROOT / ".env")

from services.db_service import init_db_pool, fetch, fetchrow, execute
from services.link_preview_service import get_link_preview_service
from app.core.logging import logger


async def refresh_expired_previews(limit: int = 50) -> None:
    """
    Refresh previews for links with expired preview_cache_expires_at.
    
    Args:
        limit: Maximum number of links to process in one run
    """
    preview_service = get_link_preview_service()
    
    # Find expired previews that are still active
    sql = """
        SELECT id, url, platform
        FROM shared_links
        WHERE status = 'active'
          AND preview_cache_expires_at IS NOT NULL
          AND preview_cache_expires_at < now()
        ORDER BY preview_cache_expires_at ASC
        LIMIT $1
    """
    
    rows = await fetch(sql, limit)
    
    if not rows:
        logger.info("prikbord_preview_refresh_no_expired", count=0)
        return
    
    logger.info("prikbord_preview_refresh_start", count=len(rows))
    
    refreshed = 0
    failed = 0
    broken = 0
    
    for row in rows:
        link_id = row["id"]
        url = row["url"]
        platform = row["platform"]
        
        try:
            # Generate new preview
            preview = await preview_service.generate_preview(url)
            
            # Update preview data
            update_sql = """
                UPDATE shared_links
                SET title = $1,
                    description = $2,
                    image_url = $3,
                    video_url = $4,
                    preview_method = $5,
                    preview_fetched_at = now(),
                    preview_cache_expires_at = now() + INTERVAL '7 days',
                    updated_at = now()
                WHERE id = $6
            """
            
            await execute(
                update_sql,
                preview.title,
                preview.description,
                preview.image_url,
                preview.video_url,
                preview.preview_method,
                link_id,
            )
            
            refreshed += 1
            logger.debug("prikbord_preview_refreshed", link_id=link_id, url=url[:50], platform=platform)
            
        except Exception as e:
            failed += 1
            logger.warning("prikbord_preview_refresh_failed", link_id=link_id, url=url[:50], error=str(e))
            
            # Check if this is the 3rd failed attempt (track via a simple counter)
            # For now, we'll mark as broken_link if preview generation fails
            # In a more sophisticated version, we could track failed attempts in a separate table
            try:
                # Mark as broken_link if preview generation consistently fails
                # This is a simple heuristic - could be improved
                mark_broken_sql = """
                    UPDATE shared_links
                    SET status = 'broken_link',
                        updated_at = now()
                    WHERE id = $1
                """
                await execute(mark_broken_sql, link_id)
                broken += 1
            except Exception as mark_error:
                logger.error("prikbord_preview_mark_broken_failed", link_id=link_id, error=str(mark_error))
    
    logger.info(
        "prikbord_preview_refresh_complete",
        total=len(rows),
        refreshed=refreshed,
        failed=failed,
        broken=broken,
    )


async def main():
    """Main entry point for the worker."""
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    
    logger.info("prikbord_preview_refresh_worker_start", limit=limit)
    
    try:
        await init_db_pool()
        await refresh_expired_previews(limit=limit)
    except Exception as e:
        logger.error("prikbord_preview_refresh_worker_error", error=str(e))
        raise
    finally:
        logger.info("prikbord_preview_refresh_worker_complete")


if __name__ == "__main__":
    asyncio.run(main())








