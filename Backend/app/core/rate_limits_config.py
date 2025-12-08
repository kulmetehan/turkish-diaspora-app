# Backend/app/core/rate_limits_config.py
"""
Rate limiting configuration per action type.

Defines limits and time windows for different actions in the system.
All limits are per key (client_id, user_id, or IP address).
"""

from typing import Dict, Tuple

# Rate limit configuration: (limit, window_seconds)
# limit: maximum number of actions allowed in the time window
# window_seconds: sliding window size in seconds
RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    "check_in": (10, 60),  # 10 check-ins per 60 seconds
    "reaction": (30, 60),  # 30 reactions per 60 seconds
    "note": (5, 300),  # 5 notes per 300 seconds (5 minutes)
    "poll_response": (10, 60),  # 10 poll responses per 60 seconds
    "account_creation": (3, 3600),  # 3 account creations per hour (future use)
}


def get_rate_limit(action: str) -> Tuple[int, int]:
    """
    Get rate limit configuration for an action.
    
    Args:
        action: Action name (e.g., 'check_in', 'reaction')
        
    Returns:
        Tuple of (limit, window_seconds)
        
    Raises:
        ValueError: If action is not configured
    """
    if action not in RATE_LIMITS:
        raise ValueError(f"Rate limit not configured for action: {action}")
    return RATE_LIMITS[action]






