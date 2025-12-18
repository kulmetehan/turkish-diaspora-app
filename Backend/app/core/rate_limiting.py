# Backend/app/core/rate_limiting.py
"""
Rate limiting service using sliding window algorithm.

Uses the rate_limits table to track requests per key (client_id, user_id, or IP)
with a sliding window approach.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.rate_limits_config import get_rate_limit
from services.db_service import fetch, execute
from app.core.logging import get_logger

logger = get_logger()


async def check_rate_limit(
    key_type: str,
    key_value: str,
    action: str,
    limit: Optional[int] = None,
    window_seconds: Optional[int] = None,
) -> bool:
    """
    Check if a rate limit would be exceeded for the given key and action.
    
    Uses sliding window: counts all records within the last window_seconds.
    
    Args:
        key_type: Type of key ('client_id', 'user_id', or 'ip')
        key_value: The actual key value (UUID string, IP address, etc.)
        action: Action name (e.g., 'check_in', 'reaction')
        limit: Optional custom limit (uses config if None)
        window_seconds: Optional custom window (uses config if None)
        
    Returns:
        True if under limit (allowed), False if over limit (blocked)
    """
    # Get default limits from config if not provided
    if limit is None or window_seconds is None:
        default_limit, default_window = get_rate_limit(action)
        limit = limit or default_limit
        window_seconds = window_seconds or default_window
    
    # Calculate window start time (sliding window)
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_seconds)
    
    # Count records in the sliding window
    # We need to count all records with window_start >= (now - window_seconds)
    # The table stores window_start per time bucket, so we sum counts for all buckets
    # in the window
    sql = """
        SELECT COALESCE(SUM(count), 0) as total_count
        FROM rate_limits
        WHERE key_type = $1
          AND key_value = $2
          AND action = $3
          AND window_start >= $4
    """
    
    rows = await fetch(sql, key_type, key_value, action, window_start)
    total_count = rows[0].get("total_count", 0) or 0 if rows else 0
    
    # Check if under limit
    return total_count < limit


async def increment_rate_limit(key_type: str, key_value: str, action: str) -> None:
    """
    Increment the rate limit counter for the given key and action.
    
    Uses time-bucketed windows. Each window is a fixed size (e.g., 1 minute).
    Multiple actions within the same window increment the same counter.
    
    Args:
        key_type: Type of key ('client_id', 'user_id', or 'ip')
        key_value: The actual key value
        action: Action name (e.g., 'check_in', 'reaction')
    """
    _, window_seconds = get_rate_limit(action)
    
    # Calculate window start time (bucket)
    # For a 60 second window, we bucket by minute: 00, 01, 02, etc.
    now = datetime.now(timezone.utc)
    
    # Calculate the bucket start time (rounded down to window boundary)
    # For 60s window: round down to nearest minute
    # For 300s window: round down to nearest 5 minutes
    bucket_seconds = window_seconds
    if window_seconds <= 60:
        bucket_seconds = 60  # 1 minute buckets
    elif window_seconds <= 300:
        bucket_seconds = 60  # Still use 1 minute buckets for 5min windows
    else:
        bucket_seconds = 300  # 5 minute buckets for longer windows
    
    # Round down to bucket boundary
    bucket_timestamp = int(now.timestamp())
    bucket_timestamp = (bucket_timestamp // bucket_seconds) * bucket_seconds
    window_start = datetime.fromtimestamp(bucket_timestamp, tz=timezone.utc)
    
    # Upsert: increment count if exists, create with count=1 if not
    sql = """
        INSERT INTO rate_limits (key_type, key_value, action, window_start, count, created_at)
        VALUES ($1, $2, $3, $4, 1, now())
        ON CONFLICT (key_type, key_value, action, window_start)
        DO UPDATE SET count = rate_limits.count + 1
    """
    
    try:
        await execute(sql, key_type, key_value, action, window_start)
    except Exception as e:
        logger.error(
            "failed_to_increment_rate_limit",
            error=str(e),
            key_type=key_type,
            action=action,
        )
        # Don't fail the request if rate limit tracking fails
        # Rate limiting is defensive, not critical path


async def check_and_increment_rate_limit(
    key_type: str,
    key_value: str,
    action: str,
    limit: Optional[int] = None,
    window_seconds: Optional[int] = None,
) -> bool:
    """
    Check rate limit and increment counter if allowed.
    
    This is a convenience function that combines check and increment.
    Returns True if allowed, False if blocked.
    
    Args:
        key_type: Type of key ('client_id', 'user_id', or 'ip')
        key_value: The actual key value
        action: Action name
        limit: Optional custom limit
        window_seconds: Optional custom window
        
    Returns:
        True if allowed, False if blocked
    """
    # Check first
    allowed = await check_rate_limit(key_type, key_value, action, limit, window_seconds)
    
    # Only increment if allowed
    if allowed:
        await increment_rate_limit(key_type, key_value, action)
    
    return allowed



















