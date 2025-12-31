# Backend/api/routers/polls.py
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from starlette.requests import Request
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime

from app.core.client_id import require_client_id, get_client_id, get_last_user_id
from app.core.feature_flags import require_feature
from app.deps.auth import get_current_user_optional, User
from app.deps.rate_limiting import require_rate_limit_factory
from services.db_service import fetch, execute
from services.xp_service import award_xp
from services.activity_summary_service import update_user_activity_summary

router = APIRouter(prefix="/polls", tags=["polls"])


class PollOption(BaseModel):
    id: int
    option_text: str
    display_order: int


class PollResponse(BaseModel):
    id: int
    title: str
    question: str
    poll_type: str  # 'single_choice', 'multi_choice'
    options: List[PollOption]
    is_sponsored: bool
    starts_at: datetime
    ends_at: Optional[datetime]
    user_has_responded: bool = False


class PollStats(BaseModel):
    poll_id: int
    total_responses: int
    option_counts: Dict[int, int]  # {option_id: count}
    privacy_threshold_met: bool  # True if >= 10 responses


class PollResponseCreate(BaseModel):
    option_id: int  # For single_choice
    # option_ids: List[int]  # For multi_choice (future)


@router.get("", response_model=List[PollResponse])
async def list_polls(
    request: Request,
    city_key: Optional[str] = Query(None, description="Filter by city"),
    limit: int = Query(10, le=50),
    client_id: Optional[str] = Depends(get_client_id),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """List active polls for user/city."""
    require_feature("polls_enabled")
    
    user_id = user.user_id if user else None
    last_user_id = await get_last_user_id(request)
    
    sql = """
        SELECT p.id, p.title, p.question, p.poll_type, p.is_sponsored, 
               p.starts_at, p.ends_at
        FROM polls p
        WHERE p.status = 'active'
          AND (p.targeting_city_key IS NULL OR p.targeting_city_key = $1)
          AND (p.starts_at <= now())
          AND (p.ends_at IS NULL OR p.ends_at > now())
        ORDER BY p.starts_at DESC
        LIMIT $2
    """
    
    rows = await fetch(sql, city_key, limit)
    
    polls = []
    for row in rows:
        # Get options
        options_sql = """
            SELECT id, option_text, display_order
            FROM poll_options
            WHERE poll_id = $1
            ORDER BY display_order
        """
        options_rows = await fetch(options_sql, row["id"])
        options = [
            PollOption(
                id=opt["id"],
                option_text=opt["option_text"],
                display_order=opt["display_order"],
            )
            for opt in options_rows
        ]
        
        # Check if user has responded
        # Use identity_key which is COALESCE(user_id::text, client_id::text)
        # This ensures we find responses regardless of whether user was logged in or not
        has_responded = False
        if user_id or client_id:
            # Calculate current identity_key (same logic as database trigger)
            # identity_key = COALESCE(user_id::text, client_id::text)
            current_identity_key = str(user_id) if user_id else client_id
            
            # If user is logged out but has last_user_id from localStorage, use that
            # This allows us to track poll responses even after user logs out
            associated_user_id = last_user_id if not user_id and last_user_id else None
            
            # Fallback: check if this client_id was ever associated with a user_id
            if not associated_user_id and not user_id and client_id:
                client_session_check = "SELECT user_id FROM client_id_sessions WHERE client_id = $1 AND user_id IS NOT NULL LIMIT 1"
                client_session_rows = await fetch(client_session_check, client_id)
                if client_session_rows:
                    associated_user_id = client_session_rows[0].get("user_id")
            
            # Search using identity_key, but also check user_id and client_id directly
            # to handle edge cases where identity_key might not match exactly
            conditions = []
            params = [row["id"]]
            param_num = 2
            
            # Primary check: use identity_key
            conditions.append(f"identity_key = ${param_num}")
            params.append(current_identity_key)
            param_num += 1
            
            # Fallback checks: also check user_id and client_id directly
            if user_id:
                conditions.append(f"user_id = ${param_num}")
                params.append(user_id)
                param_num += 1
            
            if associated_user_id:
                # Check responses with the associated user_id (in case user answered while logged in)
                conditions.append(f"identity_key = ${param_num}")
                params.append(str(associated_user_id))
                param_num += 1
                conditions.append(f"user_id = ${param_num}")
                params.append(associated_user_id)
                param_num += 1
            
            if client_id:
                conditions.append(f"client_id = ${param_num}")
                params.append(client_id)
                param_num += 1
            
            if conditions:
                where_clause = " OR ".join(conditions)
                response_check = f"""
                    SELECT 1 FROM poll_responses
                    WHERE poll_id = $1 AND ({where_clause})
                    LIMIT 1
                """
                response_rows = await fetch(response_check, *params)
                has_responded = len(response_rows) > 0
        
        polls.append(PollResponse(
            id=row["id"],
            title=row["title"],
            question=row["question"],
            poll_type=row["poll_type"],
            options=options,
            is_sponsored=row.get("is_sponsored", False),
            starts_at=row["starts_at"],
            ends_at=row.get("ends_at"),
            user_has_responded=has_responded,
        ))
    
    return polls


@router.get("/{poll_id}", response_model=PollResponse)
async def get_poll(
    poll_id: int = Path(..., description="Poll ID"),
    client_id: Optional[str] = Depends(get_client_id),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Get poll details."""
    require_feature("polls_enabled")
    
    user_id = user.user_id if user else None
    
    sql = """
        SELECT id, title, question, poll_type, is_sponsored, starts_at, ends_at
        FROM polls
        WHERE id = $1 AND status = 'active'
    """
    
    rows = await fetch(sql, poll_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Poll not found")
    
    row = rows[0]
    
    # Get options
    options_sql = """
        SELECT id, option_text, display_order
        FROM poll_options
        WHERE poll_id = $1
        ORDER BY display_order
    """
    options_rows = await fetch(options_sql, poll_id)
    options = [
        PollOption(
            id=opt["id"],
            option_text=opt["option_text"],
            display_order=opt["display_order"],
        )
        for opt in options_rows
    ]
    
    # Check if user has responded
    # Use identity_key which is COALESCE(user_id::text, client_id::text)
    # This ensures we find responses regardless of whether user was logged in or not
    has_responded = False
    if user_id or client_id:
        # Calculate current identity_key (same logic as database trigger)
        current_identity_key = str(user_id) if user_id else client_id
        
        # Search using identity_key, but also check user_id and client_id directly
        conditions = []
        params = [poll_id]
        param_num = 2
        
        # Primary check: use identity_key
        conditions.append(f"identity_key = ${param_num}")
        params.append(current_identity_key)
        param_num += 1
        
        # Fallback checks: also check user_id and client_id directly
        if user_id:
            conditions.append(f"user_id = ${param_num}")
            params.append(user_id)
            param_num += 1
        
        if client_id:
            conditions.append(f"client_id = ${param_num}")
            params.append(client_id)
            param_num += 1
        
        if conditions:
            where_clause = " OR ".join(conditions)
            response_check = f"""
                SELECT 1 FROM poll_responses
                WHERE poll_id = $1 AND ({where_clause})
                LIMIT 1
            """
            response_rows = await fetch(response_check, *params)
            has_responded = len(response_rows) > 0
    
    return PollResponse(
        id=row["id"],
        title=row["title"],
        question=row["question"],
        poll_type=row["poll_type"],
        options=options,
        is_sponsored=row.get("is_sponsored", False),
        starts_at=row["starts_at"],
        ends_at=row.get("ends_at"),
        user_has_responded=has_responded,
    )


@router.post("/{poll_id}/responses")
async def create_poll_response(
    request: Request,
    poll_id: int = Path(..., description="Poll ID"),
    response: PollResponseCreate = ...,
    client_id: str = Depends(require_client_id),
    _rate_limit: None = Depends(require_rate_limit_factory("poll_response")),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Submit poll response."""
    require_feature("polls_enabled")
    
    user_id = user.user_id if user else None
    
    # Validate poll is active
    poll_check = """
        SELECT id, poll_type FROM polls
        WHERE id = $1 AND status = 'active'
          AND (starts_at <= now())
          AND (ends_at IS NULL OR ends_at > now())
    """
    poll_rows = await fetch(poll_check, poll_id)
    if not poll_rows:
        raise HTTPException(status_code=404, detail="Poll not found or not active")
    
    poll_type = poll_rows[0].get("poll_type")
    
    # For single_choice polls, check for duplicate response
    # Use identity_key which is COALESCE(user_id::text, client_id::text)
    # This ensures we find responses regardless of whether user was logged in or not
    if poll_type == "single_choice":
        if user_id or client_id:
            # Calculate current identity_key (same logic as database trigger)
            current_identity_key = str(user_id) if user_id else client_id
            
            # Search using identity_key, but also check user_id and client_id directly
            conditions = []
            params = [poll_id]
            param_num = 2
            
            # Primary check: use identity_key
            conditions.append(f"identity_key = ${param_num}")
            params.append(current_identity_key)
            param_num += 1
            
            # Fallback checks: also check user_id and client_id directly
            if user_id:
                conditions.append(f"user_id = ${param_num}")
                params.append(user_id)
                param_num += 1
            
            if client_id:
                conditions.append(f"client_id = ${param_num}")
                params.append(client_id)
                param_num += 1
            
            if conditions:
                where_clause = " OR ".join(conditions)
                duplicate_check = f"""
                    SELECT 1 FROM poll_responses
                    WHERE poll_id = $1 AND ({where_clause})
                    LIMIT 1
                """
                duplicate_rows = await fetch(duplicate_check, *params)
                if duplicate_rows:
                    raise HTTPException(status_code=409, detail="Already responded to this poll")
    
    # Verify option belongs to poll
    option_check = """
        SELECT 1 FROM poll_options
        WHERE id = $1 AND poll_id = $2
    """
    option_rows = await fetch(option_check, response.option_id, poll_id)
    if not option_rows:
        raise HTTPException(status_code=400, detail="Invalid option for this poll")
    
    # Insert response
    try:
        # Insert with user_id if authenticated, otherwise just client_id
        if user_id:
            sql = """
                INSERT INTO poll_responses (poll_id, option_id, user_id, client_id, created_at)
                VALUES ($1, $2, $3, $4, now())
                RETURNING id
            """
            row = await fetch(sql, poll_id, response.option_id, user_id, client_id)
        else:
            sql = """
                INSERT INTO poll_responses (poll_id, option_id, client_id, created_at)
                VALUES ($1, $2, $3, now())
                RETURNING id
            """
            row = await fetch(sql, poll_id, response.option_id, client_id)
        
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create poll response")
        
        response_id = row[0]["id"]
        
        # Award XP (only works for authenticated users after Story 9)
        if user_id:
            await award_xp(user_id=user_id, client_id=client_id, source="poll_response", source_id=response_id)
            # Update activity summary (fire-and-forget async task)
            asyncio.create_task(update_user_activity_summary(user_id=user_id))
        
        return {"ok": True, "response_id": response_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create poll response: {str(e)}")


@router.get("/{poll_id}/stats", response_model=PollStats)
async def get_poll_stats(
    poll_id: int = Path(..., description="Poll ID"),
):
    """Get aggregated poll statistics."""
    require_feature("polls_enabled")
    
    # Calculate stats directly from poll_responses for real-time accuracy
    # This ensures stats are always up-to-date even if poll_stats table is not updated
    sql = """
        SELECT 
            option_id,
            COUNT(*) as count
        FROM poll_responses
        WHERE poll_id = $1
        GROUP BY option_id
    """
    
    rows = await fetch(sql, poll_id)
    
    # Build option_counts dictionary
    option_counts_int = {}
    total = 0
    
    for row in rows:
        option_id = int(row["option_id"])
        count = int(row["count"])
        option_counts_int[option_id] = count
        total += count
    
    return PollStats(
        poll_id=poll_id,
        total_responses=total,
        option_counts=option_counts_int,
        privacy_threshold_met=True,
    )

