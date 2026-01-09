# Backend/api/routers/push.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID
import json
import asyncpg

from app.deps.auth import get_current_user, User
from services.db_service import fetch, execute
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/push", tags=["push"])


class DeviceTokenRegister(BaseModel):
    token: str  # JSON string of Web Push subscription
    platform: str = "web"
    user_agent: Optional[str] = None


class PushPreferencesResponse(BaseModel):
    enabled: bool
    poll_notifications: bool
    trending_notifications: bool
    activity_notifications: bool
    chat_notifications: bool


class PushPreferencesUpdate(BaseModel):
    enabled: Optional[bool] = None
    poll_notifications: Optional[bool] = None
    trending_notifications: Optional[bool] = None
    activity_notifications: Optional[bool] = None
    chat_notifications: Optional[bool] = None


@router.post("/register")
async def register_device_token(
    registration: DeviceTokenRegister,
    user: User = Depends(get_current_user),
):
    """
    Register a device token for push notifications.
    Token should be a JSON string containing the Web Push subscription object.
    """
    try:
        # Validate token is valid JSON
        token_json = json.loads(registration.token)
        
        # Store or update device token
        sql = """
            INSERT INTO device_tokens (user_id, token, platform, user_agent, last_used_at, is_active)
            VALUES ($1::uuid, $2, $3, $4, now(), true)
            ON CONFLICT (user_id, token) 
            DO UPDATE SET 
                last_used_at = now(),
                is_active = true,
                user_agent = EXCLUDED.user_agent
            RETURNING id
        """
        
        result = await fetch(
            sql,
            user.user_id,
            registration.token,
            registration.platform,
            registration.user_agent,
        )
        
        logger.info(
            "device_token_registered",
            user_id=str(user.user_id),
            platform=registration.platform,
        )
        
        return {"ok": True, "message": "Device token registered successfully"}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid token format (must be valid JSON)")
    except Exception as e:
        logger.error(
            "device_token_registration_failed",
            user_id=str(user.user_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to register device token: {str(e)}")


@router.delete("/unregister")
async def unregister_device_token(
    token: str,
    user: User = Depends(get_current_user),
):
    """
    Unregister a device token (mark as inactive).
    """
    try:
        sql = """
            UPDATE device_tokens
            SET is_active = false
            WHERE user_id = $1::uuid AND token = $2
            RETURNING id
        """
        
        result = await fetch(sql, user.user_id, token)
        
        if not result:
            raise HTTPException(status_code=404, detail="Device token not found")
        
        logger.info(
            "device_token_unregistered",
            user_id=str(user.user_id),
        )
        
        return {"ok": True, "message": "Device token unregistered successfully"}
        
    except Exception as e:
        logger.error(
            "device_token_unregistration_failed",
            user_id=str(user.user_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to unregister device token: {str(e)}")


@router.get("/preferences", response_model=PushPreferencesResponse)
async def get_push_preferences(
    user: User = Depends(get_current_user),
):
    """
    Get push notification preferences for the current user.
    """
    sql = """
        SELECT enabled, poll_notifications, trending_notifications, activity_notifications, chat_notifications
        FROM push_notification_preferences
        WHERE user_id = $1::uuid
    """
    
    try:
        rows = await fetch(sql, user.user_id)
    except asyncpg.exceptions.UndefinedColumnError as e:
        if "chat_notifications" in str(e):
            # Column doesn't exist yet - return defaults and log warning
            logger.warning(
                "chat_notifications_column_missing",
                user_id=str(user.user_id),
                error=str(e),
                message="chat_notifications column missing - please run migration 033a_fix_chat_notifications_column.sql",
            )
            # Try query without chat_notifications
            sql_fallback = """
                SELECT enabled, poll_notifications, trending_notifications, activity_notifications
                FROM push_notification_preferences
                WHERE user_id = $1::uuid
            """
            rows = await fetch(sql_fallback, user.user_id)
            if not rows:
                return PushPreferencesResponse(
                    enabled=True,
                    poll_notifications=True,
                    trending_notifications=False,
                    activity_notifications=False,
                    chat_notifications=True,  # Default value
                )
            row = rows[0]
            return PushPreferencesResponse(
                enabled=row.get("enabled", True),
                poll_notifications=row.get("poll_notifications", True),
                trending_notifications=row.get("trending_notifications", False),
                activity_notifications=row.get("activity_notifications", False),
                chat_notifications=True,  # Default value when column missing
            )
        else:
            # Re-raise if it's a different column error
            raise
    
    if not rows:
        # Return defaults if no preferences exist
        return PushPreferencesResponse(
            enabled=True,
            poll_notifications=True,
            trending_notifications=False,
            activity_notifications=False,
            chat_notifications=True,
        )
    
    row = rows[0]
    return PushPreferencesResponse(
        enabled=row.get("enabled", True),
        poll_notifications=row.get("poll_notifications", True),
        trending_notifications=row.get("trending_notifications", False),
        activity_notifications=row.get("activity_notifications", False),
        chat_notifications=row.get("chat_notifications", True),
    )


@router.put("/preferences", response_model=PushPreferencesResponse)
async def update_push_preferences(
    preferences: PushPreferencesUpdate,
    user: User = Depends(get_current_user),
):
    """
    Update push notification preferences for the current user.
    """
    # Check if preferences exist
    check_sql = "SELECT user_id FROM push_notification_preferences WHERE user_id = $1::uuid"
    existing = await fetch(check_sql, user.user_id)
    
    updates = []
    values = []
    param_num = 1
    
    if preferences.enabled is not None:
        updates.append(f"enabled = ${param_num}")
        values.append(preferences.enabled)
        param_num += 1
    
    if preferences.poll_notifications is not None:
        updates.append(f"poll_notifications = ${param_num}")
        values.append(preferences.poll_notifications)
        param_num += 1
    
    if preferences.trending_notifications is not None:
        updates.append(f"trending_notifications = ${param_num}")
        values.append(preferences.trending_notifications)
        param_num += 1
    
    if preferences.activity_notifications is not None:
        updates.append(f"activity_notifications = ${param_num}")
        values.append(preferences.activity_notifications)
        param_num += 1
    
    if preferences.chat_notifications is not None:
        updates.append(f"chat_notifications = ${param_num}")
        values.append(preferences.chat_notifications)
        param_num += 1
    
    if not updates:
        # No changes, return current preferences
        return await get_push_preferences(user)
    
    if existing:
        # Update existing preferences
        updates_str = ", ".join(updates)
        values.append(user.user_id)
        
        update_sql = f"""
            UPDATE push_notification_preferences
            SET {updates_str}, updated_at = now()
            WHERE user_id = ${param_num}
            RETURNING enabled, poll_notifications, trending_notifications, activity_notifications, chat_notifications
        """
        try:
            result = await fetch(update_sql, *values)
        except asyncpg.exceptions.UndefinedColumnError as e:
            if "chat_notifications" in str(e):
                # Column doesn't exist - try without chat_notifications in RETURNING
                logger.warning(
                    "chat_notifications_column_missing_on_update",
                    user_id=str(user.user_id),
                    error=str(e),
                    message="chat_notifications column missing - skipping update for this field",
                )
                # Remove chat_notifications from updates if it was included
                if "chat_notifications" in updates_str:
                    # Rebuild updates without chat_notifications
                    updates_without_chat = [u for u in updates if "chat_notifications" not in u]
                    if not updates_without_chat:
                        # Only chat_notifications was being updated, return current preferences
                        return await get_push_preferences(user)
                    updates_str = ", ".join(updates_without_chat)
                    # Rebuild values without chat_notifications value
                    chat_idx = None
                    for i, u in enumerate(updates):
                        if "chat_notifications" in u:
                            chat_idx = i
                            break
                    if chat_idx is not None:
                        values = values[:chat_idx] + values[chat_idx+1:]
                        param_num -= 1
                    values.append(user.user_id)
                    update_sql = f"""
                        UPDATE push_notification_preferences
                        SET {updates_str}, updated_at = now()
                        WHERE user_id = ${param_num}
                        RETURNING enabled, poll_notifications, trending_notifications, activity_notifications
                    """
                else:
                    # chat_notifications wasn't in updates, just fix RETURNING clause
                    update_sql = f"""
                        UPDATE push_notification_preferences
                        SET {updates_str}, updated_at = now()
                        WHERE user_id = ${param_num}
                        RETURNING enabled, poll_notifications, trending_notifications, activity_notifications
                    """
                result = await fetch(update_sql, *values)
            else:
                raise
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update preferences")
        
        row = result[0]
        return PushPreferencesResponse(
            enabled=row.get("enabled", True),
            poll_notifications=row.get("poll_notifications", True),
            trending_notifications=row.get("trending_notifications", False),
            activity_notifications=row.get("activity_notifications", False),
            chat_notifications=row.get("chat_notifications", True),
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update preferences")
        
        row = result[0]
        return PushPreferencesResponse(
            enabled=row.get("enabled", True),
            poll_notifications=row.get("poll_notifications", True),
            trending_notifications=row.get("trending_notifications", False),
            activity_notifications=row.get("activity_notifications", False),
            chat_notifications=row.get("chat_notifications", True),
        )
    else:
        # Insert new preferences
        enabled = preferences.enabled if preferences.enabled is not None else True
        poll_notifications = preferences.poll_notifications if preferences.poll_notifications is not None else True
        trending_notifications = preferences.trending_notifications if preferences.trending_notifications is not None else False
        activity_notifications = preferences.activity_notifications if preferences.activity_notifications is not None else False
        chat_notifications = preferences.chat_notifications if preferences.chat_notifications is not None else True
        
        insert_sql = """
            INSERT INTO push_notification_preferences (
                user_id, enabled, poll_notifications, trending_notifications, activity_notifications, chat_notifications, updated_at
            )
            VALUES ($1::uuid, $2, $3, $4, $5, $6, now())
            RETURNING enabled, poll_notifications, trending_notifications, activity_notifications, chat_notifications
        """
        try:
            result = await fetch(
                insert_sql,
                user.user_id,
                enabled,
                poll_notifications,
                trending_notifications,
                activity_notifications,
                chat_notifications,
            )
        except asyncpg.exceptions.UndefinedColumnError as e:
            if "chat_notifications" in str(e):
                # Column doesn't exist - insert without chat_notifications
                logger.warning(
                    "chat_notifications_column_missing_on_insert",
                    user_id=str(user.user_id),
                    error=str(e),
                    message="chat_notifications column missing - inserting without this field",
                )
                insert_sql = """
                    INSERT INTO push_notification_preferences (
                        user_id, enabled, poll_notifications, trending_notifications, activity_notifications, updated_at
                    )
                    VALUES ($1::uuid, $2, $3, $4, $5, now())
                    RETURNING enabled, poll_notifications, trending_notifications, activity_notifications
                """
                result = await fetch(
                    insert_sql,
                    user.user_id,
                    enabled,
                    poll_notifications,
                    trending_notifications,
                    activity_notifications,
                )
            else:
                raise
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create preferences")
        
        row = result[0]
        return PushPreferencesResponse(
            enabled=row.get("enabled", True),
            poll_notifications=row.get("poll_notifications", True),
            trending_notifications=row.get("trending_notifications", False),
            activity_notifications=row.get("activity_notifications", False),
            chat_notifications=row.get("chat_notifications", True),
        )


@router.post("/send")
async def send_notification(
    user_id: str,
    notification_type: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
):
    """
    Send a push notification to a user (internal/admin endpoint).
    """
    from services.push_service import get_push_service
    
    push_service = get_push_service()
    result = await push_service.send_notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        data=data,
    )
    
    return result

