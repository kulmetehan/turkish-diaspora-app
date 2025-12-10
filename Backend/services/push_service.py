# Backend/services/push_service.py
from __future__ import annotations

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import pywebpush
from pywebpush import webpush, WebPushException

from services.db_service import fetch, execute
from app.core.logging import get_logger

logger = get_logger()


class PushService:
    """
    Service for sending push notifications via Web Push API.
    """
    
    def __init__(self):
        self.vapid_private_key = os.getenv("VAPID_PRIVATE_KEY")
        self.vapid_public_key = os.getenv("VAPID_PUBLIC_KEY")
        self.vapid_email = os.getenv("VAPID_EMAIL", "noreply@turkishdiaspora.app")
        
        if not self.vapid_private_key or not self.vapid_public_key:
            logger.warning(
                "vapid_keys_missing",
                message="VAPID keys not configured. Push notifications will not work."
            )
    
    async def send_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send a push notification to all active devices for a user.
        
        Args:
            user_id: UUID of the user
            notification_type: Type of notification ('poll', 'trending', 'activity', 'system')
            title: Notification title
            body: Notification body
            data: Optional additional data payload
            
        Returns:
            Dict with delivery results
        """
        # Check user preferences
        prefs_sql = """
            SELECT enabled, poll_notifications, trending_notifications, activity_notifications
            FROM push_notification_preferences
            WHERE user_id = $1::uuid
        """
        prefs_rows = await fetch(prefs_sql, user_id)
        
        if not prefs_rows:
            # Default preferences if not set
            enabled = True
            poll_notifications = True
            trending_notifications = False
            activity_notifications = False
        else:
            prefs = prefs_rows[0]
            enabled = prefs.get("enabled", True)
            poll_notifications = prefs.get("poll_notifications", True)
            trending_notifications = prefs.get("trending_notifications", False)
            activity_notifications = prefs.get("activity_notifications", False)
        
        # Check if this notification type is enabled
        if not enabled:
            return {"sent": 0, "failed": 0, "skipped": 1, "reason": "notifications_disabled"}
        
        type_enabled = {
            "poll": poll_notifications,
            "trending": trending_notifications,
            "activity": activity_notifications,
            "system": True,  # System notifications always enabled if notifications are enabled
        }.get(notification_type, False)
        
        if not type_enabled:
            return {"sent": 0, "failed": 0, "skipped": 1, "reason": f"{notification_type}_notifications_disabled"}
        
        # Get active device tokens
        tokens_sql = """
            SELECT id, token, platform
            FROM device_tokens
            WHERE user_id = $1::uuid AND is_active = true
        """
        token_rows = await fetch(tokens_sql, user_id)
        
        if not token_rows:
            return {"sent": 0, "failed": 0, "skipped": 1, "reason": "no_active_tokens"}
        
        # Prepare notification payload
        payload = {
            "title": title,
            "body": body,
            "icon": "/icon-192x192.png",  # Default icon
            "badge": "/badge-72x72.png",
            "data": data or {},
        }
        
        sent_count = 0
        failed_count = 0
        errors = []
        
        # Send to each device
        for token_row in token_rows:
            device_token_id = token_row["id"]
            token_json = token_row["token"]
            platform = token_row["platform"]
            
            try:
                # Parse subscription from token
                subscription = json.loads(token_json)
                
                # Send notification
                if platform == "web":
                    await self._send_web_push(subscription, payload)
                else:
                    # Future: FCM for mobile
                    logger.warning(
                        "unsupported_platform",
                        platform=platform,
                        device_token_id=device_token_id
                    )
                    continue
                
                # Log success
                await self._log_notification(
                    user_id=user_id,
                    device_token_id=device_token_id,
                    notification_type=notification_type,
                    title=title,
                    body=body,
                    data=data,
                    delivered=True,
                )
                
                sent_count += 1
                
            except Exception as e:
                error_msg = str(e)
                logger.error(
                    "push_notification_failed",
                    user_id=user_id,
                    device_token_id=device_token_id,
                    error=error_msg,
                    exc_info=True,
                )
                
                # Log failure
                await self._log_notification(
                    user_id=user_id,
                    device_token_id=device_token_id,
                    notification_type=notification_type,
                    title=title,
                    body=body,
                    data=data,
                    delivered=False,
                    error_message=error_msg,
                )
                
                failed_count += 1
                errors.append(error_msg)
        
        return {
            "sent": sent_count,
            "failed": failed_count,
            "errors": errors[:5],  # Limit error messages
        }
    
    async def _send_web_push(
        self,
        subscription: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> None:
        """
        Send Web Push notification using pywebpush.
        """
        if not self.vapid_private_key or not self.vapid_public_key:
            raise ValueError("VAPID keys not configured")
        
        # Convert VAPID keys to proper format
        vapid_claims = {
            "sub": f"mailto:{self.vapid_email}",
        }
        
        try:
            webpush(
                subscription_info=subscription,
                data=json.dumps(payload),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=vapid_claims,
            )
        except WebPushException as e:
            # Handle specific Web Push errors
            if "410" in str(e) or "Gone" in str(e):
                # Subscription expired, mark as inactive
                logger.info("subscription_expired", subscription=str(subscription.get("endpoint", "")))
            raise
    
    async def _log_notification(
        self,
        user_id: str,
        device_token_id: int,
        notification_type: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]],
        delivered: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log notification to push_notification_log table.
        """
        sql = """
            INSERT INTO push_notification_log (
                user_id, device_token_id, notification_type,
                title, body, data, sent_at, delivered, error_message
            )
            VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb, now(), $7, $8)
        """
        
        await execute(
            sql,
            user_id,
            device_token_id,
            notification_type,
            title,
            body,
            json.dumps(data) if data else None,
            delivered,
            error_message,
        )


# Singleton instance
_push_service: Optional[PushService] = None


def get_push_service() -> PushService:
    """Get or create PushService singleton."""
    global _push_service
    if _push_service is None:
        _push_service = PushService()
    return _push_service








