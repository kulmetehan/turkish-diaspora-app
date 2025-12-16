# Backend/tests/fixtures/__init__.py
"""
Test fixtures for Identity & Activity Layer tests.

Factory functions for creating test data:
- make_location()
- make_user()
- make_check_in()
- make_poll_with_options()
- make_activity_stream_entry()
"""

from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4


def make_location(
    name: str = "Test Location",
    city_key: str = "rotterdam",
    category_key: str = "restaurant",
    lat: float = 51.9244,
    lng: float = 4.4777,
    state: str = "VERIFIED",
) -> Dict[str, Any]:
    """Factory function to create a test location dict."""
    return {
        "id": 1,
        "name": name,
        "city_key": city_key,
        "category_key": category_key,
        "lat": lat,
        "lng": lng,
        "state": state,
        "created_at": datetime.now(),
    }


def make_user(
    user_id: Optional[str] = None,
    display_name: str = "Test User",
    city_key: str = "rotterdam",
) -> Dict[str, Any]:
    """Factory function to create a test user dict."""
    return {
        "id": user_id or str(uuid4()),
        "display_name": display_name,
        "city_key": city_key,
        "created_at": datetime.now(),
    }


def make_check_in(
    location_id: int = 1,
    client_id: Optional[str] = None,
    user_id: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Factory function to create a test check-in dict."""
    return {
        "id": 1,
        "location_id": location_id,
        "client_id": client_id or str(uuid4()),
        "user_id": user_id,
        "created_at": created_at or datetime.now(),
        "processed_in_activity_stream": False,
    }


def make_poll_with_options(
    title: str = "Test Poll",
    question: str = "What is your favorite?",
    poll_type: str = "single_choice",
    num_options: int = 3,
) -> Dict[str, Any]:
    """Factory function to create a test poll with options."""
    poll = {
        "id": 1,
        "title": title,
        "question": question,
        "poll_type": poll_type,
        "status": "active",
        "starts_at": datetime.now(),
        "ends_at": None,
        "options": [],
    }
    
    for i in range(num_options):
        poll["options"].append({
            "id": i + 1,
            "option_text": f"Option {i + 1}",
            "display_order": i + 1,
        })
    
    return poll


def make_activity_stream_entry(
    activity_type: str = "check_in",
    location_id: int = 1,
    client_id: Optional[str] = None,
    user_id: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Factory function to create a test activity_stream entry dict."""
    return {
        "id": 1,
        "actor_type": "user" if user_id else "client",
        "actor_id": user_id,
        "client_id": client_id or str(uuid4()),
        "activity_type": activity_type,
        "location_id": location_id,
        "city_key": "rotterdam",
        "category_key": "restaurant",
        "payload": {},
        "created_at": created_at or datetime.now(),
    }



















