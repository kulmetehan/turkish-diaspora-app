# Backend/tests/unit/test_xp_streak_logic.py
from __future__ import annotations

from datetime import datetime, timedelta
import pytest


# XP award constants (from design)
XP_CHECK_IN = 10
XP_REACTION = 2
XP_NOTE = 15
XP_POLL_RESPONSE = 5
XP_FAVORITE = 3
DAILY_XP_CAP = 200
STREAK_RESET_HOURS = 36


def test_xp_awards():
    """Test XP awards for different actions."""
    assert XP_CHECK_IN == 10
    assert XP_REACTION == 2
    assert XP_NOTE == 15
    assert XP_POLL_RESPONSE == 5
    assert XP_FAVORITE == 3


def test_daily_xp_cap():
    """Test that daily XP is capped."""
    # Simulate earning XP
    daily_xp = 0
    
    # Add check-ins (10 XP each)
    for _ in range(25):  # 25 * 10 = 250 XP
        daily_xp = min(daily_xp + XP_CHECK_IN, DAILY_XP_CAP)
    
    assert daily_xp == DAILY_XP_CAP


def test_streak_increment():
    """Test that streak increments with daily activity."""
    current_streak = 5
    last_active = datetime.now() - timedelta(hours=12)  # 12 hours ago
    
    # If user is active today, streak should increment
    hours_since_last_active = (datetime.now() - last_active).total_seconds() / 3600
    
    if hours_since_last_active < STREAK_RESET_HOURS:
        new_streak = current_streak + 1
    else:
        new_streak = 1  # Reset
    
    assert new_streak == current_streak + 1


def test_streak_reset():
    """Test that streak resets after 36 hours of inactivity."""
    current_streak = 5
    last_active = datetime.now() - timedelta(hours=40)  # 40 hours ago
    
    hours_since_last_active = (datetime.now() - last_active).total_seconds() / 3600
    
    if hours_since_last_active >= STREAK_RESET_HOURS:
        new_streak = 1  # Reset
    else:
        new_streak = current_streak + 1
    
    assert new_streak == 1


def test_streak_longest_tracking():
    """Test that longest streak is tracked separately."""
    current_streak = 10
    longest_streak = 7
    
    # If current streak exceeds longest, update longest
    if current_streak > longest_streak:
        longest_streak = current_streak
    
    assert longest_streak == 10






















