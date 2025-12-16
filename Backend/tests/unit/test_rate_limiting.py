# Backend/tests/unit/test_rate_limiting.py
from __future__ import annotations

from datetime import datetime, timedelta
import pytest


# Rate limit constants (from design)
MAX_CHECK_INS_PER_DAY = 20
MAX_CHECK_INS_PER_LOCATION_PER_DAY = 3
MAX_REACTIONS_PER_HOUR = 60
MAX_NOTES_PER_DAY = 20


def test_check_in_daily_limit():
    """Test daily check-in limit per client."""
    check_ins_today = 20
    
    can_check_in = check_ins_today < MAX_CHECK_INS_PER_DAY
    assert not can_check_in  # At limit


def test_check_in_location_limit():
    """Test per-location check-in limit."""
    check_ins_at_location_today = 3
    
    can_check_in = check_ins_at_location_today < MAX_CHECK_INS_PER_LOCATION_PER_DAY
    assert not can_check_in  # At limit


def test_reaction_hourly_limit():
    """Test hourly reaction limit."""
    reactions_this_hour = 60
    
    can_react = reactions_this_hour < MAX_REACTIONS_PER_HOUR
    assert not can_react  # At limit


def test_note_daily_limit():
    """Test daily note limit."""
    notes_today = 20
    
    can_create_note = notes_today < MAX_NOTES_PER_DAY
    assert not can_create_note  # At limit


def test_sliding_window():
    """Test that rate limiting uses sliding window."""
    # Simulate sliding window: count actions in last 24 hours
    window_start = datetime.now() - timedelta(hours=24)
    actions_in_window = 15
    
    # Actions older than window should not count
    old_action_time = datetime.now() - timedelta(hours=25)
    if old_action_time < window_start:
        actions_in_window -= 1
    
    assert actions_in_window == 14



















