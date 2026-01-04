# Backend/api/routers/leaderboards.py
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Literal
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

from services.db_service import fetch

router = APIRouter(prefix="/leaderboards", tags=["leaderboards"])


class LeaderboardUser(BaseModel):
    """User entry in a leaderboard card."""
    user_id: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[str] = None
    primary_role: Optional[str] = None  # Primary role for image display
    context: Optional[str] = None  # Additional context (e.g., "Söz over Restaurant X")


class LeaderboardCard(BaseModel):
    """A leaderboard card with category and users."""
    category: str
    title: str
    description: Optional[str] = None  # Description explaining what this category means
    users: List[LeaderboardUser]


class OneCikanlarResponse(BaseModel):
    """Response model for Öne Çıkanlar leaderboards."""
    period: str
    city_key: Optional[str] = None
    cards: List[LeaderboardCard]


def _get_period_bounds(period: str) -> tuple[datetime, datetime]:
    """
    Calculate period_start and period_end based on period string.
    
    Args:
        period: One of 'today', 'week', 'month'
    
    Returns:
        Tuple of (period_start, period_end)
    """
    now = datetime.now(timezone.utc)
    
    if period == "today":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = now
    elif period == "week":
        # Start of current week (Monday)
        days_since_monday = now.weekday()
        period_start = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        period_end = now
    elif period == "month":
        # Start of current month
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = now
    else:
        raise ValueError(f"Invalid period: {period}")
    
    return period_start, period_end


def _get_category_title(category: str) -> str:
    """Get display title for a leaderboard category."""
    titles = {
        "soz_hafta": "Bu Haftanın Sözü",
        "mahalle_gururu": "Mahallenin Gururu",
        "sessiz_guç": "Sessiz Güç",
        "diaspora_nabzı": "Diaspora Nabzı",
    }
    return titles.get(category, category)


def _get_category_description(category: str) -> Optional[str]:
    """Get description explaining what this leaderboard category means."""
    descriptions = {
        "soz_hafta": "De beste Söz van deze week",
        "mahalle_gururu": "Lokaal actief in de buurt",
        "sessiz_guç": "Veel gelezen, weinig gepost",
        "diaspora_nabzı": "Actief bijdragen aan polls",
    }
    return descriptions.get(category)


def _normalize_user_name(user_name: Optional[str], user_id: Optional[str]) -> Optional[str]:
    """
    Normalize user_name: if it equals user_id (UUID), treat it as None.
    This fixes cases where display_name was incorrectly set to user_id.
    Returns None if no valid name is available.
    """
    if not user_name or not user_id:
        return None
    
    # If display_name equals user_id, treat it as if no username was set
    if user_name.strip() == str(user_id):
        return None
    
    return user_name.strip() if user_name.strip() else None


@router.get("/öne-çıkanlar", response_model=OneCikanlarResponse)
async def get_one_cikanlar(
    period: Literal["today", "week", "month"] = Query(
        default="week",
        description="Time period for leaderboard (today, week, month)"
    ),
    city_key: Optional[str] = Query(
        default=None,
        description="City key filter (e.g., rotterdam, amsterdam). If not provided, returns global leaderboard."
    ),
):
    """
    Get Öne Çıkanlar (Featured Users) leaderboards.
    
    Returns leaderboard cards for different categories:
    - soz_hafta: Best Söz this week
    - mahalle_gururu: Local active (neighborhood pride)
    - sessiz_guç: Silent power (many reads, few posts)
    - diaspora_nabzı: Poll contribution (diaspora pulse)
    
    Each card contains up to 5 users ranked by score (score not exposed).
    """
    try:
        period_start, period_end = _get_period_bounds(period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Query leaderboard entries for the period with user roles joined
    # Optimized: filter by rank early and use efficient index
    # Include JOINs for context data (locations, notes, polls)
    sql = """
        SELECT 
            le.id,
            le.user_id,
            le.category,
            le.rank,
            le.context_data,
            up.display_name,
            up.avatar_url,
            ur.primary_role,
            ur.secondary_role,
            -- Context data from JOINs
            l.name as location_name,
            ln.content as note_content,
            p.question as poll_question
        FROM leaderboard_entries le
        LEFT JOIN user_profiles up ON le.user_id = up.id
        LEFT JOIN user_roles ur ON le.user_id = ur.user_id
        LEFT JOIN locations l ON le.context_data IS NOT NULL 
            AND le.context_data ? 'location_id' 
            AND (le.context_data->>'location_id')::int = l.id
            AND l.state = 'VERIFIED'
        LEFT JOIN location_notes ln ON le.context_data IS NOT NULL 
            AND le.context_data ? 'note_id' 
            AND (le.context_data->>'note_id')::int = ln.id
        LEFT JOIN polls p ON le.context_data IS NOT NULL 
            AND le.context_data ? 'poll_id' 
            AND (le.context_data->>'poll_id')::int = p.id
        WHERE le.rank IS NOT NULL
        AND le.rank <= 5
        AND le.period_start <= $1
        AND le.period_end >= $2
        AND ($3::text IS NULL OR le.city_key = $3)
        ORDER BY le.category, le.rank ASC
    """
    
    rows = await fetch(sql, period_end, period_start, city_key)
    
    # Group entries by category and deduplicate by user_id (keep best rank per user)
    cards_dict: dict[str, List[LeaderboardUser]] = {}
    seen_users_per_category: dict[str, set] = {}  # Track seen user_ids per category
    
    for row in rows:
        category = row.get("category")
        if category not in cards_dict:
            cards_dict[category] = []
            seen_users_per_category[category] = set()
        
        user_id = str(row.get("user_id"))
        
        # Skip if we've already seen this user in this category (deduplicate)
        if user_id in seen_users_per_category[category]:
            continue
        
        display_name = row.get("display_name")
        
        # Normalize display_name (filter out UUIDs and empty names)
        normalized_name = _normalize_user_name(display_name, user_id)
        
        # Skip users without a valid display name (they shouldn't appear in leaderboards)
        if not normalized_name:
            continue
        
        # Mark this user as seen in this category
        seen_users_per_category[category].add(user_id)
        
        # Get user role from joined data
        role = None
        primary_role = row.get("primary_role")
        secondary_role = row.get("secondary_role")
        if primary_role:
            role = primary_role
            if secondary_role:
                role = f"{role} · {secondary_role}"
        
        # Extract context from context_data JSONB
        # Use joined data (location_name, note_content, poll_question) when available
        # Fallback to IDs if joined data is not available
        context_data = row.get("context_data") or {}
        
        # Handle case where context_data might be a string (asyncpg sometimes returns JSONB as string)
        if isinstance(context_data, str):
            try:
                context_data = json.loads(context_data)
            except Exception:
                context_data = {}
        
        context = None
        if isinstance(context_data, dict):
            # Build context string from available data
            # Prefer joined data over context_data IDs
            location_name = row.get("location_name")
            note_content = row.get("note_content")
            poll_question = row.get("poll_question")
            
            if context_data.get("location_id"):
                if location_name:
                    context = location_name
                else:
                    context = f"Locatie {context_data.get('location_id')}"
            elif context_data.get("note_id"):
                if note_content:
                    # Truncate note content to first 50 chars
                    if len(note_content) > 50:
                        context = note_content[:50] + "..."
                    else:
                        context = note_content
                else:
                    context = f"Söz {context_data.get('note_id')}"
            elif context_data.get("poll_id"):
                if poll_question:
                    # Truncate poll question to first 50 chars
                    if len(poll_question) > 50:
                        context = poll_question[:50] + "..."
                    else:
                        context = poll_question
                else:
                    context = f"Poll {context_data.get('poll_id')}"
        
        cards_dict[category].append(
            LeaderboardUser(
                user_id=str(user_id),
                name=normalized_name,
                avatar_url=row.get("avatar_url"),
                role=role,
                primary_role=primary_role,
                context=context,
            )
        )
    
    # Build response cards
    cards: List[LeaderboardCard] = []
    
    # Define category order: sessiz_guç should always be last
    category_order = ["soz_hafta", "mahalle_gururu", "diaspora_nabzı", "sessiz_guç"]
    
    # Build cards in the specified order
    for category in category_order:
        if category in cards_dict and cards_dict[category]:
            cards.append(
                LeaderboardCard(
                    category=category,
                    title=_get_category_title(category),
                    description=_get_category_description(category),
                    users=cards_dict[category][:5],  # Max 5 users per card
                )
            )
    
    # Add any remaining categories that weren't in the order list (shouldn't happen, but safety)
    for category, users in cards_dict.items():
        if category not in category_order and users:
            cards.append(
                LeaderboardCard(
                    category=category,
                    title=_get_category_title(category),
                    description=_get_category_description(category),
                    users=users[:5],
                )
            )
    
    return OneCikanlarResponse(
        period=period,
        city_key=city_key,
        cards=cards,
    )

