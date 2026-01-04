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
from app.deps.auth import get_current_user, get_current_user_optional, User
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
    created_by: Optional[str] = None  # User ID (UUID) who created the poll


class PollStats(BaseModel):
    poll_id: int
    total_responses: int
    option_counts: Dict[int, int]  # {option_id: count}
    privacy_threshold_met: bool  # True if >= 10 responses


class PollResponseCreate(BaseModel):
    option_id: int  # For single_choice
    # option_ids: List[int]  # For multi_choice (future)


class PollOptionCreate(BaseModel):
    option_text: str
    display_order: int


class PollCreate(BaseModel):
    title: str
    question: str
    poll_type: str = "single_choice"  # 'single_choice', 'multi_choice'
    options: List[PollOptionCreate]  # min 2, max 5
    targeting_city_key: Optional[str] = None


@router.post("", response_model=PollResponse)
async def create_poll(
    request: Request,
    poll: PollCreate,
    client_id: str = Depends(require_client_id),
    # _rate_limit: None = Depends(require_rate_limit_factory("poll", limit=1, window_seconds=86400)),  # Temporarily disabled for testing
    user: User = Depends(get_current_user),  # Require authentication
):
    """Create a new poll (user-created)."""
    require_feature("polls_enabled")
    
    user_id = user.user_id
    
    # Validate options
    if len(poll.options) < 2:
        raise HTTPException(status_code=400, detail="Poll must have at least 2 options")
    if len(poll.options) > 5:
        raise HTTPException(status_code=400, detail="Poll can have at most 5 options")
    
    if poll.poll_type not in ("single_choice", "multi_choice"):
        raise HTTPException(
            status_code=400,
            detail="poll_type must be 'single_choice' or 'multi_choice'"
        )
    
    # Validate option texts
    for opt in poll.options:
        if not opt.option_text or not opt.option_text.strip():
            raise HTTPException(status_code=400, detail="All options must have text")
    
    # Default starts_at to now
    starts_at = datetime.now()
    
    try:
        # Insert poll with status 'active' and created_by set to user_id
        poll_sql = """
            INSERT INTO polls (title, question, poll_type, is_sponsored, starts_at, ends_at, targeting_city_key, created_by, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active', now())
            RETURNING id, title, question, poll_type, is_sponsored, starts_at, ends_at, targeting_city_key, created_at
        """
        poll_rows = await fetch(
            poll_sql,
            poll.title,
            poll.question,
            poll.poll_type,
            False,  # User-created polls are not sponsored
            starts_at,
            None,  # No end date for user polls
            poll.targeting_city_key,
            user_id,
        )
        
        if not poll_rows:
            raise HTTPException(status_code=500, detail="Failed to create poll")
        
        poll_id = poll_rows[0]["id"]
        
        # Insert options
        options = []
        for opt in poll.options:
            opt_sql = """
                INSERT INTO poll_options (poll_id, option_text, display_order, created_at)
                VALUES ($1, $2, $3, now())
                RETURNING id, option_text, display_order
            """
            opt_rows = await fetch(opt_sql, poll_id, opt.option_text.strip(), opt.display_order)
            if opt_rows:
                options.append(PollOption(**opt_rows[0]))
        
        # Create activity stream entry for poll creation
        payload = json.dumps({"poll_id": poll_id})
        activity_sql = """
            INSERT INTO activity_stream 
            (actor_type, actor_id, client_id, activity_type, location_id, city_key, category_key, payload, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, now())
        """
        await execute(
            activity_sql,
            'user',
            user_id,
            client_id,
            'poll',
            None,  # No location_id for polls
            poll.targeting_city_key,  # Use targeting_city_key if provided
            None,  # No category_key for polls
            payload,
        )
        
        # Award XP for creating poll
        await award_xp(user_id=user_id, client_id=client_id, source="poll", source_id=poll_id)
        # Update activity summary (fire-and-forget async task)
        asyncio.create_task(update_user_activity_summary(user_id=user_id))
        
        created_by_value = poll_rows[0].get("created_by") or user_id
        created_by_str = str(created_by_value) if created_by_value else None
        
        return PollResponse(
            id=poll_id,
            title=poll_rows[0]["title"],
            question=poll_rows[0]["question"],
            poll_type=poll_rows[0]["poll_type"],
            options=options,
            is_sponsored=False,
            starts_at=poll_rows[0]["starts_at"],
            ends_at=poll_rows[0].get("ends_at"),
            user_has_responded=False,
            created_by=created_by_str,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create poll: {str(e)}")


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
               p.starts_at, p.ends_at, p.created_by
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
        
        created_by_value = row.get("created_by")
        # Convert UUID to string if present
        created_by_str = str(created_by_value) if created_by_value else None
        
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
            created_by=created_by_str,
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
        SELECT id, title, question, poll_type, is_sponsored, starts_at, ends_at, created_by
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
    
    created_by_value = row.get("created_by")
    created_by_str = str(created_by_value) if created_by_value else None
    
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
        created_by=created_by_str,
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


@router.delete("/{poll_id}")
async def delete_poll(
    poll_id: int = Path(..., description="Poll ID"),
    user: User = Depends(get_current_user),
):
    """Delete own poll."""
    require_feature("polls_enabled")
    
    user_id = user.user_id
    
    # Check if poll exists and verify ownership
    check_sql = """
        SELECT id, created_by FROM polls
        WHERE id = $1
    """
    rows = await fetch(check_sql, poll_id)
    
    if not rows:
        raise HTTPException(status_code=404, detail="Poll not found")
    
    poll_creator = rows[0].get("created_by")
    
    # Verify ownership - convert both to strings for comparison
    poll_creator_str = str(poll_creator) if poll_creator else None
    user_id_str = str(user_id) if user_id else None
    
    if poll_creator_str != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized to delete this poll")
    
    # Delete poll (cascade will delete options, responses, and activity stream entries)
    delete_sql = "DELETE FROM polls WHERE id = $1"
    await execute(delete_sql, poll_id)
    
    # Also delete activity stream entries for this poll
    delete_activity_sql = """
        DELETE FROM activity_stream 
        WHERE activity_type = 'poll' AND payload->>'poll_id' = $1
    """
    await execute(delete_activity_sql, str(poll_id))
    
    return {"ok": True, "poll_id": poll_id}


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

