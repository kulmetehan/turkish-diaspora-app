# Backend/app/workers/push_notifications.py
"""
Push Notifications Worker

Sends push notifications for polls, trending locations, and activity updates.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

# Pathing
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent
BACKEND_DIR = APP_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id
from services.db_service import init_db_pool, fetch
from services.push_service import get_push_service
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    finish_worker_run,
)

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="push_notifications")


async def send_poll_notifications() -> Dict[str, Any]:
    """
    Send notifications for new polls.
    """
    # Get recent polls (last hour)
    sql = """
        SELECT id, question, created_at
        FROM polls
        WHERE created_at >= NOW() - INTERVAL '1 hour'
            AND created_at <= NOW()
    """
    polls = await fetch(sql)
    
    if not polls:
        return {"sent": 0, "failed": 0, "skipped": 1, "reason": "no_new_polls"}
    
    # Get users with poll notifications enabled
    users_sql = """
        SELECT DISTINCT user_id
        FROM push_notification_preferences
        WHERE enabled = true AND poll_notifications = true
    """
    users = await fetch(users_sql)
    
    push_service = get_push_service()
    total_sent = 0
    total_failed = 0
    
    for poll in polls:
        for user_row in users:
            user_id = user_row["user_id"]
            result = await push_service.send_notification(
                user_id=str(user_id),
                notification_type="poll",
                title="New Poll Available",
                body=poll["question"][:100],  # Truncate if too long
                data={"poll_id": poll["id"], "type": "poll"},
            )
            total_sent += result.get("sent", 0)
            total_failed += result.get("failed", 0)
    
    return {"sent": total_sent, "failed": total_failed, "polls": len(polls)}


async def send_trending_notifications() -> Dict[str, Any]:
    """
    Send notifications when user's favorite locations become trending.
    """
    # Get trending locations from last hour
    trending_sql = """
        SELECT DISTINCT location_id
        FROM trending_locations
        WHERE created_at >= NOW() - INTERVAL '1 hour'
    """
    trending = await fetch(trending_sql)
    
    if not trending:
        return {"sent": 0, "failed": 0, "skipped": 1, "reason": "no_trending_locations"}
    
    trending_location_ids = [row["location_id"] for row in trending]
    
    # Get users who have these locations as favorites and trending notifications enabled
    users_sql = """
        SELECT DISTINCT f.user_id, f.location_id, l.name as location_name
        FROM favorites f
        INNER JOIN locations l ON l.id = f.location_id
        INNER JOIN push_notification_preferences p ON p.user_id = f.user_id
        WHERE f.location_id = ANY($1::bigint[])
            AND p.enabled = true
            AND p.trending_notifications = true
    """
    users = await fetch(users_sql, trending_location_ids)
    
    push_service = get_push_service()
    total_sent = 0
    total_failed = 0
    
    for user_row in users:
        user_id = user_row["user_id"]
        location_name = user_row["location_name"]
        result = await push_service.send_notification(
            user_id=str(user_id),
            notification_type="trending",
            title="Location is Trending!",
            body=f"{location_name} is now trending",
            data={"location_id": user_row["location_id"], "type": "trending"},
        )
        total_sent += result.get("sent", 0)
        total_failed += result.get("failed", 0)
    
    return {"sent": total_sent, "failed": total_failed, "users_notified": len(users)}


async def send_activity_notifications() -> Dict[str, Any]:
    """
    Send notifications for activity on user's content.
    """
    # Get recent activity (last hour) on user's notes/reactions
    # This is a simplified version - in production, would track which users' content was interacted with
    activity_sql = """
        SELECT DISTINCT n.user_id, a.activity_type, l.name as location_name
        FROM activity_stream a
        INNER JOIN location_notes n ON n.location_id = a.location_id
        INNER JOIN locations l ON l.id = a.location_id
        INNER JOIN push_notification_preferences p ON p.user_id = n.user_id
        WHERE a.created_at >= NOW() - INTERVAL '1 hour'
            AND a.activity_type IN ('reaction', 'note')
            AND p.enabled = true
            AND p.activity_notifications = true
        LIMIT 100
    """
    activities = await fetch(activity_sql)
    
    if not activities:
        return {"sent": 0, "failed": 0, "skipped": 1, "reason": "no_recent_activity"}
    
    push_service = get_push_service()
    total_sent = 0
    total_failed = 0
    
    for activity in activities:
        user_id = activity["user_id"]
        activity_type = activity["activity_type"]
        location_name = activity["location_name"]
        
        title_map = {
            "reaction": "New Reaction",
            "note": "New Note",
        }
        
        result = await push_service.send_notification(
            user_id=str(user_id),
            notification_type="activity",
            title=title_map.get(activity_type, "New Activity"),
            body=f"Activity on {location_name}",
            data={"activity_type": activity_type, "location_name": location_name},
        )
        total_sent += result.get("sent", 0)
        total_failed += result.get("failed", 0)
    
    return {"sent": total_sent, "failed": total_failed, "activities": len(activities)}


@with_run_id
async def run(notification_type: str = "all", dry_run: bool = False) -> None:
    """
    Main worker function.
    
    Args:
        notification_type: Type of notifications to send ('poll', 'trending', 'activity', 'all')
        dry_run: If True, don't actually send notifications
    """
    await init_db_pool()
    
    run_id = await start_worker_run(
        worker_name="push_notifications",
        dry_run=dry_run,
    )
    
    await mark_worker_run_running(run_id)
    
    try:
        if dry_run:
            logger.info("dry_run_mode", message="Dry run mode - no notifications will be sent")
            return
        
        results = {}
        
        if notification_type in ("poll", "all"):
            results["poll"] = await send_poll_notifications()
        
        if notification_type in ("trending", "all"):
            results["trending"] = await send_trending_notifications()
        
        if notification_type in ("activity", "all"):
            results["activity"] = await send_activity_notifications()
        
        total_sent = sum(r.get("sent", 0) for r in results.values())
        total_failed = sum(r.get("failed", 0) for r in results.values())
        
        logger.info(
            "notifications_sent",
            total_sent=total_sent,
            total_failed=total_failed,
            results=results,
        )
        
        await finish_worker_run(
            run_id=run_id,
            status="completed",
            counters={
                "sent": total_sent,
                "failed": total_failed,
            },
        )
        
    except Exception as e:
        logger.error("worker_failed", error=str(e), exc_info=True)
        await finish_worker_run(
            run_id=run_id,
            status="failed",
            error_message=str(e),
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Push Notifications Worker")
    parser.add_argument(
        "--type",
        type=str,
        default="all",
        choices=["poll", "trending", "activity", "all"],
        help="Type of notifications to send",
    )
    parser.add_argument("--dry-run", type=int, default=0, help="Dry run mode (1=yes, 0=no)")
    
    args = parser.parse_args()
    
    asyncio.run(run(notification_type=args.type, dry_run=bool(args.dry_run)))


if __name__ == "__main__":
    main()













