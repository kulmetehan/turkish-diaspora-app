# Backend/app/models/event_categories.py
"""
Event-specific categories, separate from location categories.
"""

from enum import Enum


class EventCategory(str, Enum):
    """Event-specific categories, separate from location categories."""
    club = "club"
    theater = "theater"
    concert = "concert"
    familie = "familie"

