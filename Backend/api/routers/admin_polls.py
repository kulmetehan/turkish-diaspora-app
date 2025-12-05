# Backend/api/routers/admin_polls.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.deps.admin_auth import verify_admin_user, AdminUser
from services.db_service import fetch, execute

router = APIRouter(prefix="/admin/polls", tags=["admin-polls"])


class PollOptionCreate(BaseModel):
    option_text: str
    display_order: int


class PollCreate(BaseModel):
    title: str
    question: str
    poll_type: str  # 'single_choice', 'multi_choice'
    options: List[PollOptionCreate]  # min 2, max 5
    is_sponsored: bool = False
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    targeting_city_key: Optional[str] = None


class PollOption(BaseModel):
    id: int
    option_text: str
    display_order: int


class PollResponse(BaseModel):
    id: int
    title: str
    question: str
    poll_type: str
    options: List[PollOption]
    is_sponsored: bool
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
    targeting_city_key: Optional[str]
    created_at: datetime


class PollUpdate(BaseModel):
    title: Optional[str] = None
    question: Optional[str] = None
    poll_type: Optional[str] = None
    is_sponsored: Optional[bool] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    targeting_city_key: Optional[str] = None


@router.post("", response_model=PollResponse)
async def create_poll(
    poll: PollCreate,
    admin: AdminUser = Depends(verify_admin_user),
):
    """Create a new poll."""
    
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
    
    # Default starts_at to now if not provided
    starts_at = poll.starts_at or datetime.now()
    
    try:
        # Insert poll
        poll_sql = """
            INSERT INTO polls (title, question, poll_type, is_sponsored, starts_at, ends_at, targeting_city_key, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, now())
            RETURNING id, title, question, poll_type, is_sponsored, starts_at, ends_at, targeting_city_key, created_at
        """
        poll_rows = await fetch(
            poll_sql,
            poll.title,
            poll.question,
            poll.poll_type,
            poll.is_sponsored,
            starts_at,
            poll.ends_at,
            poll.targeting_city_key,
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
            opt_rows = await fetch(opt_sql, poll_id, opt.option_text, opt.display_order)
            if opt_rows:
                options.append(PollOption(**opt_rows[0]))
        
        return PollResponse(
            id=poll_id,
            title=poll_rows[0]["title"],
            question=poll_rows[0]["question"],
            poll_type=poll_rows[0]["poll_type"],
            options=options,
            is_sponsored=poll_rows[0].get("is_sponsored", False),
            starts_at=poll_rows[0].get("starts_at"),
            ends_at=poll_rows[0].get("ends_at"),
            targeting_city_key=poll_rows[0].get("targeting_city_key"),
            created_at=poll_rows[0]["created_at"],
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create poll: {str(e)}")


@router.get("", response_model=List[PollResponse])
async def list_polls(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """List all polls."""
    
    sql = """
        SELECT 
            p.id, p.title, p.question, p.poll_type, p.is_sponsored,
            p.starts_at, p.ends_at, p.targeting_city_key, p.created_at
        FROM polls p
        ORDER BY p.created_at DESC
        LIMIT $1 OFFSET $2
    """
    
    rows = await fetch(sql, limit, offset)
    
    polls = []
    for row in rows:
        # Get options for each poll
        opt_sql = """
            SELECT id, option_text, display_order
            FROM poll_options
            WHERE poll_id = $1
            ORDER BY display_order
        """
        opt_rows = await fetch(opt_sql, row["id"])
        options = [PollOption(**opt) for opt in opt_rows]
        
        polls.append(PollResponse(
            id=row["id"],
            title=row["title"],
            question=row["question"],
            poll_type=row["poll_type"],
            options=options,
            is_sponsored=row.get("is_sponsored", False),
            starts_at=row.get("starts_at"),
            ends_at=row.get("ends_at"),
            targeting_city_key=row.get("targeting_city_key"),
            created_at=row["created_at"],
        ))
    
    return polls


@router.put("/{poll_id}", response_model=PollResponse)
async def update_poll(
    poll_id: int = Path(..., description="Poll ID"),
    update: PollUpdate = ...,
    admin: AdminUser = Depends(verify_admin_user),
):
    """Update a poll."""
    
    # Build update SQL dynamically
    updates = []
    values = []
    param_num = 1
    
    if update.title is not None:
        updates.append(f"title = ${param_num}")
        values.append(update.title)
        param_num += 1
    
    if update.question is not None:
        updates.append(f"question = ${param_num}")
        values.append(update.question)
        param_num += 1
    
    if update.poll_type is not None:
        if update.poll_type not in ("single_choice", "multi_choice"):
            raise HTTPException(
                status_code=400,
                detail="poll_type must be 'single_choice' or 'multi_choice'"
            )
        updates.append(f"poll_type = ${param_num}")
        values.append(update.poll_type)
        param_num += 1
    
    if update.is_sponsored is not None:
        updates.append(f"is_sponsored = ${param_num}")
        values.append(update.is_sponsored)
        param_num += 1
    
    if update.starts_at is not None:
        updates.append(f"starts_at = ${param_num}")
        values.append(update.starts_at)
        param_num += 1
    
    if update.ends_at is not None:
        updates.append(f"ends_at = ${param_num}")
        values.append(update.ends_at)
        param_num += 1
    
    if update.targeting_city_key is not None:
        updates.append(f"targeting_city_key = ${param_num}")
        values.append(update.targeting_city_key)
        param_num += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates_str = ", ".join(updates)
    values.append(poll_id)
    
    sql = f"""
        UPDATE polls
        SET {updates_str}
        WHERE id = ${param_num}
        RETURNING id, title, question, poll_type, is_sponsored, starts_at, ends_at, targeting_city_key, created_at
    """
    
    rows = await fetch(sql, *values)
    
    if not rows:
        raise HTTPException(status_code=404, detail="Poll not found")
    
    row = rows[0]
    
    # Get options
    opt_sql = """
        SELECT id, option_text, display_order
        FROM poll_options
        WHERE poll_id = $1
        ORDER BY display_order
    """
    opt_rows = await fetch(opt_sql, poll_id)
    options = [PollOption(**opt) for opt in opt_rows]
    
    return PollResponse(
        id=row["id"],
        title=row["title"],
        question=row["question"],
        poll_type=row["poll_type"],
        options=options,
        is_sponsored=row.get("is_sponsored", False),
        starts_at=row.get("starts_at"),
        ends_at=row.get("ends_at"),
        city_key=row.get("city_key"),
        created_at=row["created_at"],
    )


@router.delete("/{poll_id}")
async def delete_poll(
    poll_id: int = Path(..., description="Poll ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """Delete a poll."""
    
    # Check if poll exists
    check_sql = "SELECT id FROM polls WHERE id = $1"
    check_rows = await fetch(check_sql, poll_id)
    
    if not check_rows:
        raise HTTPException(status_code=404, detail="Poll not found")
    
    # Delete poll (cascade will delete options and responses)
    delete_sql = "DELETE FROM polls WHERE id = $1"
    await execute(delete_sql, poll_id)
    
    return {"ok": True, "poll_id": poll_id}

