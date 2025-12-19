from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

import yaml
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel

from app.core.client_id import get_client_id
from app.core.feature_flags import require_feature
from app.models.events_public import EventsListResponse
from services.db_service import fetch, execute
from services.event_categories_service import get_event_category_keys
from services.events_public_service import list_public_events

try:
    from app.workers.discovery_bot import load_cities_config
except ImportError:  # pragma: no cover - fallback for runtime environments without worker module

    def load_cities_config() -> Dict[str, Any]:
        config_path = Path(__file__).resolve().parents[3] / "Infra" / "config" / "cities.yml"
        with config_path.open("r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
        if not isinstance(data, dict):
            raise ValueError("cities.yml must contain a top-level object")
        return data


router = APIRouter(
    prefix="/events",
    tags=["events"],
)


@lru_cache(maxsize=1)
def _city_keys() -> Set[str]:
    cfg = load_cities_config()
    cities = (cfg or {}).get("cities") or {}
    keys: Set[str] = set()
    for raw_key in cities.keys():
        normalized = str(raw_key or "").strip().lower().replace(" ", "_")
        if normalized:
            keys.add(normalized)
    return keys


@lru_cache(maxsize=1)
def _category_keys() -> Set[str]:
    return set(get_event_category_keys())


def _normalize_city(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    candidate = value.strip().lower().replace(" ", "_")
    if not candidate:
        return None
    if candidate not in _city_keys():
        raise HTTPException(status_code=400, detail=f"Unknown city '{value}'.")
    return candidate


def _normalize_categories(values: Optional[Sequence[str]]) -> List[str]:
    if not values:
        return []
    allowed = _category_keys()
    normalized: List[str] = []
    seen: Set[str] = set()
    for raw in values:
        if raw is None:
            continue
        for fragment in raw.split(","):
            candidate = fragment.strip().lower().replace(" ", "_")
            if not candidate:
                continue
            if candidate not in allowed:
                raise HTTPException(status_code=400, detail=f"Unknown category '{candidate}'.")
            if candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
    return normalized


@router.get("", response_model=EventsListResponse)
@router.get("/", response_model=EventsListResponse, include_in_schema=False)
async def get_events(
    city: Optional[str] = Query(
        default=None,
        description="Filter by city key (e.g., rotterdam).",
    ),
    date_from: Optional[date] = Query(
        default=None,
        description="Inclusive start date (YYYY-MM-DD).",
    ),
    date_to: Optional[date] = Query(
        default=None,
        description="Inclusive end date (YYYY-MM-DD).",
    ),
    categories: Optional[List[str]] = Query(
        default=None,
        description="Optional repeated category keys (community,culture,...).",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> EventsListResponse:
    if date_from and date_to and date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to must be on or after date_from.")

    normalized_city = _normalize_city(city)
    normalized_categories = _normalize_categories(categories)

    items, total = await list_public_events(
        city=normalized_city,
        date_from=date_from,
        date_to=date_to,
        categories=normalized_categories or None,
        limit=limit,
        offset=offset,
    )
    return EventsListResponse(items=items, total=total, limit=limit, offset=offset)


class ReactionToggleRequest(BaseModel):
    reaction_type: str  # Emoji string (e.g., "🔥", "❤️", "👍", etc.)


@router.post("/{event_id}/reactions", response_model=dict)
async def toggle_event_reaction(
    event_id: int = Path(..., description="Event ID"),
    request: ReactionToggleRequest = ...,
    client_id: Optional[str] = Depends(get_client_id),
):
    """Toggle emoji reaction on event."""
    require_feature("check_ins_enabled")
    
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id required")
    
    # Basic validation: ensure reaction_type is a non-empty string
    if not request.reaction_type or not isinstance(request.reaction_type, str) or len(request.reaction_type.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="reaction_type must be a non-empty string (emoji)"
        )
    
    # Limit emoji length to prevent abuse (reasonable limit for emoji sequences)
    if len(request.reaction_type) > 10:
        raise HTTPException(
            status_code=400,
            detail="reaction_type too long (max 10 characters)"
        )
    
    user_id = None  # TODO: Extract from auth session
    
    # Check if event exists
    check_sql = "SELECT id FROM events_public WHERE id = $1"
    check_rows = await fetch(check_sql, event_id)
    if not check_rows:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if already reacted with this type
    if user_id:
        check_reaction_sql = """
            SELECT id FROM event_reactions 
            WHERE event_id = $1 AND user_id = $2 AND reaction_type = $3
        """
        existing = await fetch(check_reaction_sql, event_id, user_id, request.reaction_type)
    else:
        check_reaction_sql = """
            SELECT id FROM event_reactions 
            WHERE event_id = $1 AND client_id = $2 AND reaction_type = $3
        """
        existing = await fetch(check_reaction_sql, event_id, client_id, request.reaction_type)
    
    if existing:
        # Remove reaction
        if user_id:
            delete_sql = """
                DELETE FROM event_reactions 
                WHERE event_id = $1 AND user_id = $2 AND reaction_type = $3
            """
            await execute(delete_sql, event_id, user_id, request.reaction_type)
        else:
            delete_sql = """
                DELETE FROM event_reactions 
                WHERE event_id = $1 AND client_id = $2 AND reaction_type = $3
            """
            await execute(delete_sql, event_id, client_id, request.reaction_type)
        is_active = False
    else:
        # Add reaction
        if user_id:
            insert_sql = """
                INSERT INTO event_reactions (event_id, user_id, reaction_type) 
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """
            # #region agent log
            import json, time
            with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"timestamp": time.time() * 1000, "location": "events.py:201", "message": "Attempting INSERT event_reaction (user_id)", "data": {"event_id": event_id, "reaction_type": request.reaction_type, "user_id": str(user_id)}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
            # #endregion
            try:
                await execute(insert_sql, event_id, user_id, request.reaction_type)
                # #region agent log
                with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"timestamp": time.time() * 1000, "location": "events.py:208", "message": "INSERT event_reaction succeeded", "data": {"event_id": event_id, "reaction_type": request.reaction_type}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                # #endregion
            except Exception as e:
                # #region agent log
                with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"timestamp": time.time() * 1000, "location": "events.py:213", "message": "INSERT event_reaction FAILED", "data": {"event_id": event_id, "reaction_type": request.reaction_type, "error": str(e), "error_type": type(e).__name__}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                # #endregion
                raise
        else:
            insert_sql = """
                INSERT INTO event_reactions (event_id, client_id, reaction_type) 
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """
            # #region agent log
            import json, time
            with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"timestamp": time.time() * 1000, "location": "events.py:207", "message": "Attempting INSERT event_reaction", "data": {"event_id": event_id, "reaction_type": request.reaction_type, "client_id": client_id}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
            # #endregion
            try:
                await execute(insert_sql, event_id, client_id, request.reaction_type)
                # #region agent log
                with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"timestamp": time.time() * 1000, "location": "events.py:214", "message": "INSERT event_reaction succeeded", "data": {"event_id": event_id, "reaction_type": request.reaction_type}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                # #endregion
            except Exception as e:
                # #region agent log
                with open('/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"timestamp": time.time() * 1000, "location": "events.py:219", "message": "INSERT event_reaction FAILED", "data": {"event_id": event_id, "reaction_type": request.reaction_type, "error": str(e), "error_type": type(e).__name__}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                # #endregion
                raise
        is_active = True
    
    # Get updated count
    count_sql = """
        SELECT COUNT(*) as count 
        FROM event_reactions 
        WHERE event_id = $1 AND reaction_type = $2
    """
    count_rows = await fetch(count_sql, event_id, request.reaction_type)
    count = count_rows[0]["count"] if count_rows else 0
    
    return {
        "reaction_type": request.reaction_type,
        "is_active": is_active,
        "count": count
    }


@router.get("/{event_id}/reactions", response_model=dict)
async def get_event_reactions(
    event_id: int = Path(..., description="Event ID"),
    client_id: Optional[str] = Depends(get_client_id),
):
    """Get reaction counts and user reaction for an event."""
    require_feature("check_ins_enabled")
    
    # Check if event exists
    check_sql = "SELECT id FROM events_public WHERE id = $1"
    check_rows = await fetch(check_sql, event_id)
    if not check_rows:
        raise HTTPException(status_code=404, detail="Event not found")
    
    user_id = None  # TODO: Extract from auth session
    
    # Get reaction counts grouped by type
    counts_sql = """
        SELECT reaction_type, COUNT(*) as count
        FROM event_reactions
        WHERE event_id = $1
        GROUP BY reaction_type
        ORDER BY count DESC, reaction_type ASC
    """
    count_rows = await fetch(counts_sql, event_id)
    
    # Build reactions dict dynamically from database results
    reactions: Dict[str, int] = {}
    for row in count_rows:
        reaction_type = row["reaction_type"]
        reactions[reaction_type] = row["count"]
    
    # Get user's reaction if any
    user_reaction = None
    if user_id:
        user_reaction_sql = """
            SELECT reaction_type FROM event_reactions
            WHERE event_id = $1 AND user_id = $2
            LIMIT 1
        """
        user_reaction_rows = await fetch(user_reaction_sql, event_id, user_id)
        if user_reaction_rows:
            user_reaction = user_reaction_rows[0]["reaction_type"]
    elif client_id:
        user_reaction_sql = """
            SELECT reaction_type FROM event_reactions
            WHERE event_id = $1 AND client_id = $2
            LIMIT 1
        """
        user_reaction_rows = await fetch(user_reaction_sql, event_id, client_id)
        if user_reaction_rows:
            user_reaction = user_reaction_rows[0]["reaction_type"]
    
    return {
        "reactions": reactions,
        "user_reaction": user_reaction
    }

