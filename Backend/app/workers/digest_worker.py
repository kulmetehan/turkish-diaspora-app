# Backend/app/workers/digest_worker.py
"""
Weekly Digest Email Worker

Sends weekly personalized email digests to users who have opted in.
Includes:
- Top trending locations
- New polls
- Activity summary
- Personal stats

Runs weekly (typically on Mondays) via scheduled cron job.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys
from uuid import UUID

# Path setup
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent
BACKEND_DIR = APP_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.db_service import init_db_pool, fetch, execute
from services.email_service import get_email_service
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    finish_worker_run,
)
import os

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="digest")


async def get_digest_opt_in_users() -> List[Dict[str, Any]]:
    """
    Get all users who have opted in for email digests.
    """
    sql = """
        SELECT DISTINCT
            u.id as user_id,
            u.email,
            COALESCE(up.display_name, split_part(u.email, '@', 1)) as display_name,
            COALESCE(up.city_key, 'rotterdam') as city_key,
            up.language_pref
        FROM auth.users u
        INNER JOIN privacy_settings ps ON ps.user_id = u.id
        LEFT JOIN user_profiles up ON up.id = u.id
        WHERE ps.allow_email_digest = true
          AND u.email_confirmed_at IS NOT NULL  -- Only confirmed emails
          AND u.deleted_at IS NULL  -- Not deleted
        ORDER BY u.created_at DESC
    """
    
    rows = await fetch(sql)
    return rows if rows else []


async def get_trending_locations_for_city(
    city_key: str,
    limit: int = 5,
    days: int = 7,
) -> List[Dict[str, Any]]:
    """
    Get top trending locations for a city in the last N days.
    """
    sql = """
        SELECT 
            tl.location_id,
            l.name,
            l.category,
            tl.score,
            tl.check_ins_count,
            tl.reactions_count,
            tl.notes_count
        FROM trending_locations tl
        INNER JOIN locations l ON l.id = tl.location_id
        WHERE tl.city_key = $1
          AND tl.window = '7d'
          AND l.state = 'VERIFIED'
        ORDER BY tl.score DESC
        LIMIT $2
    """
    
    rows = await fetch(sql, city_key, limit)
    return rows if rows else []


async def get_new_polls_for_user(
    user_id: UUID,
    days: int = 7,
) -> List[Dict[str, Any]]:
    """
    Get new polls created in the last N days that the user hasn't responded to yet.
    """
    sql = """
        SELECT 
            p.id,
            p.title,
            p.question,
            p.poll_type,
            p.is_sponsored,
            p.created_at,
            COUNT(po.id) as option_count
        FROM polls p
        INNER JOIN poll_options po ON po.poll_id = p.id
        WHERE p.starts_at <= now()
          AND (p.ends_at IS NULL OR p.ends_at >= now())
          AND p.created_at >= now() - INTERVAL '%s days'
          AND NOT EXISTS (
              SELECT 1 FROM poll_responses pr
              WHERE pr.poll_id = p.id AND pr.user_id = $1::uuid
          )
        GROUP BY p.id, p.title, p.question, p.poll_type, p.is_sponsored, p.created_at
        ORDER BY p.created_at DESC
        LIMIT 5
    """ % days
    
    rows = await fetch(sql, user_id)
    return rows if rows else []


async def get_user_activity_summary(
    user_id: UUID,
    days: int = 7,
) -> Dict[str, Any]:
    """
    Get user's activity summary for the last N days.
    """
    sql = """
        SELECT 
            COUNT(*) FILTER (WHERE activity_type = 'check_in') as check_ins,
            COUNT(*) FILTER (WHERE activity_type = 'reaction') as reactions,
            COUNT(*) FILTER (WHERE activity_type = 'note') as notes,
            COUNT(*) FILTER (WHERE activity_type = 'favorite') as favorites,
            COUNT(DISTINCT location_id) as unique_locations
        FROM activity_stream
        WHERE user_id = $1::uuid
          AND created_at >= now() - INTERVAL '%s days'
    """ % days
    
    rows = await fetch(sql, user_id)
    return rows[0] if rows else {}


async def get_user_xp_and_streak(
    user_id: UUID,
) -> Dict[str, Any]:
    """
    Get user's current XP and streak stats.
    """
    sql = """
        SELECT 
            total_xp,
            current_streak_days,
            longest_streak_days
        FROM user_streaks
        WHERE user_id = $1::uuid
    """
    
    rows = await fetch(sql, user_id)
    return rows[0] if rows else {}


async def generate_digest_content(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate personalized digest content for a user.
    """
    user_id = UUID(user["user_id"])
    city_key = user.get("city_key", "rotterdam")
    language = user.get("language_pref", "nl")
    
    # Get trending locations
    trending = await get_trending_locations_for_city(city_key, limit=5, days=7)
    
    # Get new polls
    new_polls = await get_new_polls_for_user(user_id, days=7)
    
    # Get activity summary
    activity = await get_user_activity_summary(user_id, days=7)
    
    # Get XP and streak
    gamification = await get_user_xp_and_streak(user_id)
    
    return {
        "user": user,
        "trending_locations": trending,
        "new_polls": new_polls,
        "activity": activity,
        "gamification": gamification,
        "language": language,
    }


async def send_digest_email(user: Dict[str, Any], content: Dict[str, Any]) -> bool:
    """
    Send weekly digest email to a user.
    """
    email_service = get_email_service()
    
    # Generate email subject based on language
    language = content.get("language", "nl")
    subjects = {
        "nl": f"Weekoverzicht Turkspot - {datetime.now(timezone.utc).strftime('%d %B')}",
        "tr": f"Turkspot Haftalık Özet - {datetime.now(timezone.utc).strftime('%d %B')}",
        "en": f"Turkspot Weekly Summary - {datetime.now(timezone.utc).strftime('%B %d')}",
    }
    subject = subjects.get(language, subjects["nl"])
    
    # Render email template
    context = {
        **content,
        "base_url": os.getenv("FRONTEND_URL", "https://turkspot.nl"),
        "unsubscribe_url": f"{os.getenv('FRONTEND_URL', 'https://turkspot.nl')}/#/account",
    }
    
    try:
        html_body, text_body = email_service.render_template("weekly_digest", context)
        
        # Send email
        success = await email_service.send_email(
            to_email=user["email"],
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
        
        if success:
            logger.info(
                "digest_email_sent",
                user_id=str(user["user_id"]),
                email=user["email"],
            )
        else:
            logger.warning(
                "digest_email_failed",
                user_id=str(user["user_id"]),
                email=user["email"],
            )
        
        return success
        
    except Exception as e:
        logger.error(
            "digest_email_error",
            user_id=str(user["user_id"]),
            email=user["email"],
            error=str(e),
            exc_info=True,
        )
        return False


async def run_digest_once(
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run one digest generation and sending cycle.
    
    Args:
        dry_run: If True, don't send emails, just log what would be sent
        limit: Optional limit on number of emails to send (for testing)
    """
    stats = {
        "users_processed": 0,
        "emails_sent": 0,
        "emails_failed": 0,
        "errors": [],
    }
    
    # Get opt-in users
    users = await get_digest_opt_in_users()
    
    if limit:
        users = users[:limit]
    
    logger.info(
        "digest_worker_started",
        total_users=len(users),
        dry_run=dry_run,
        limit=limit,
    )
    
    for user in users:
        try:
            stats["users_processed"] += 1
            
            # Generate content
            content = await generate_digest_content(user)
            
            if dry_run:
                logger.info(
                    "digest_dry_run",
                    user_id=str(user["user_id"]),
                    email=user["email"],
                    trending_count=len(content.get("trending_locations", [])),
                    polls_count=len(content.get("new_polls", [])),
                )
                stats["emails_sent"] += 1
            else:
                # Send email
                success = await send_digest_email(user, content)
                
                if success:
                    stats["emails_sent"] += 1
                else:
                    stats["emails_failed"] += 1
            
        except Exception as e:
            logger.error(
                "digest_user_error",
                user_id=str(user.get("user_id")),
                email=user.get("email"),
                error=str(e),
                exc_info=True,
            )
            stats["emails_failed"] += 1
            stats["errors"].append(str(e))
    
    logger.info(
        "digest_worker_completed",
        **stats,
    )
    
    return stats


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TDA Weekly Digest Email Worker")
    p.add_argument("--once", action="store_true", help="Run one cycle and exit")
    p.add_argument("--dry-run", action="store_true", help="Don't send emails, just log")
    p.add_argument("--limit", type=int, help="Limit number of emails to send (for testing)")
    p.add_argument("--worker-run-id", type=UUID, help="UUID of worker_runs record for progress tracking")
    return p.parse_args()


async def main_async() -> None:
    import os
    
    with with_run_id() as rid:
        logger.info("worker_started")
        await init_db_pool()
        
        args = _parse_args()
        
        # Start worker run tracking
        run_id = args.worker_run_id
        if run_id:
            await mark_worker_run_running(run_id)
        
        # Run digest
        stats = await run_digest_once(
            dry_run=args.dry_run,
            limit=args.limit,
        )
        
        # Finish worker run
        if run_id:
            await finish_worker_run(run_id, {
                "stats": stats,
            })
        
        logger.info("worker_completed", stats=stats)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

