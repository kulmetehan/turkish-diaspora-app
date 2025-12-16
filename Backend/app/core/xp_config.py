# Backend/app/core/xp_config.py
"""
XP amounts configuration per action type.

Defines how much XP is awarded for different activities in the system.
"""

from typing import Dict

# XP amounts per action type
XP_AMOUNTS: Dict[str, int] = {
    "check_in": 10,
    "reaction": 5,
    "note": 20,
    "poll_response": 15,
    "favorite": 5,
}

# Daily XP cap (default)
DAILY_XP_CAP = 200


def get_xp_amount(action: str) -> int:
    """
    Get XP amount for an action.
    
    Args:
        action: Action name (e.g., 'check_in', 'reaction')
        
    Returns:
        XP amount (0 if action not configured)
    """
    return XP_AMOUNTS.get(action, 0)

















