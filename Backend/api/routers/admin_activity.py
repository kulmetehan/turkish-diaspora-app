# Backend/api/routers/admin_activity.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Optional, List
from app.deps.admin_auth import verify_admin_user, AdminUser
from services.db_service import fetch, fetchrow, execute
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/admin/activity", tags=["admin-activity"])


@router.delete("/check-ins/{check_in_id}")
async def delete_check_in_admin(
    check_in_id: int = Path(..., description="Check-in ID or Activity Stream ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Delete a check-in (admin only).
    Hard delete - removes the check-in record completely.
    
    Accepts either:
    - check_in_id: Direct ID from check_ins table (preferred, from payload)
    - activity_stream_id: ID from activity_stream table (fallback for old entries)
    """
    # First, try to find check-in directly by ID
    check_sql = "SELECT id FROM check_ins WHERE id = $1"
    check_row = await fetchrow(check_sql, check_in_id)
    
    actual_check_in_id = None
    
    if check_row:
        # Found directly - this is a check_in_id
        actual_check_in_id = check_in_id
    else:
        # Not found as check_in_id - try as activity_stream_id
        # Find check-in via activity_stream entry (for old entries without check_in_id in payload)
        activity_sql = """
            SELECT 
                (payload->>'check_in_id')::int as check_in_id_from_payload,
                location_id,
                actor_id,
                created_at
            FROM activity_stream
            WHERE id = $1 AND activity_type = 'check_in'
        """
        activity_row = await fetchrow(activity_sql, check_in_id)
        
        if activity_row:
            # Try payload first (for new entries)
            payload_check_in_id = activity_row.get("check_in_id_from_payload")
            if payload_check_in_id:
                actual_check_in_id = payload_check_in_id
            else:
                # Fallback: find check-in by location_id, actor_id, and created_at (for old entries)
                fallback_sql = """
                    SELECT id FROM check_ins
                    WHERE location_id = $1
                      AND (user_id = $2 OR (user_id IS NULL AND $2 IS NULL))
                      AND ABS(EXTRACT(EPOCH FROM (created_at - $3))) < 5
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                fallback_row = await fetchrow(
                    fallback_sql,
                    activity_row["location_id"],
                    activity_row["actor_id"],
                    activity_row["created_at"],
                )
                if fallback_row:
                    actual_check_in_id = fallback_row["id"]
    
    if not actual_check_in_id:
        raise HTTPException(status_code=404, detail="Check-in not found")
    
    # Get check-in details before deletion for activity stream cleanup
    check_in_details_sql = """
        SELECT location_id, user_id, created_at
        FROM check_ins
        WHERE id = $1
    """
    check_in_details = await fetchrow(check_in_details_sql, actual_check_in_id)
    
    if not check_in_details:
        raise HTTPException(status_code=404, detail="Check-in not found")
    
    location_id = check_in_details["location_id"]
    user_id = check_in_details["user_id"]
    created_at = check_in_details["created_at"]
    
    # Delete activity stream entries for this check-in BEFORE deleting the check-in
    delete_activity_sql = """
        DELETE FROM activity_stream
        WHERE activity_type = 'check_in'
          AND (
            (payload->>'check_in_id')::int = $1
            OR (
              location_id = $2
              AND actor_id = $3
              AND ABS(EXTRACT(EPOCH FROM (created_at - $4))) < 5
            )
          )
    """
    await execute(delete_activity_sql, actual_check_in_id, location_id, user_id, created_at)
    
    # Delete check-in
    delete_sql = "DELETE FROM check_ins WHERE id = $1"
    await execute(delete_sql, actual_check_in_id)
    
    logger.info(
        "admin_check_in_deleted",
        check_in_id=actual_check_in_id,
        admin_email=admin.email,
    )
    
    return {"ok": True, "check_in_id": actual_check_in_id}


@router.delete("/notes/{note_id}")
async def delete_note_admin(
    note_id: int = Path(..., description="Note ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Delete a note (admin only).
    Hard delete - removes the note record completely.
    """
    # Check if note exists
    check_sql = "SELECT id FROM location_notes WHERE id = $1"
    check_row = await fetchrow(check_sql, note_id)
    
    if not check_row:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Delete note
    delete_sql = "DELETE FROM location_notes WHERE id = $1"
    await execute(delete_sql, note_id)
    
    logger.info(
        "admin_note_deleted",
        note_id=note_id,
        admin_email=admin.email,
    )
    
    return {"ok": True, "note_id": note_id}


@router.get("/check-ins")
async def list_check_ins_admin(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """List all check-ins (admin only)."""
    sql = """
        SELECT 
            ci.id,
            ci.location_id,
            ci.user_id,
            ci.created_at,
            l.name as location_name,
            up.display_name as user_name,
            au.email as user_email
        FROM check_ins ci
        LEFT JOIN locations l ON l.id = ci.location_id
        LEFT JOIN user_profiles up ON up.id = ci.user_id
        LEFT JOIN auth.users au ON au.id = ci.user_id
        ORDER BY ci.created_at DESC
        LIMIT $1 OFFSET $2
    """
    rows = await fetch(sql, limit, offset)
    
    return [
        {
            "id": row["id"],
            "location_id": row["location_id"],
            "location_name": row.get("location_name"),
            "user_id": str(row["user_id"]) if row.get("user_id") else None,
            "user_name": row.get("user_name"),
            "user_email": row.get("user_email"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        }
        for row in rows
    ]


@router.get("/notes")
async def list_notes_admin(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """List all notes (admin only)."""
    sql = """
        SELECT 
            ln.id,
            ln.location_id,
            ln.user_id,
            ln.content,
            ln.created_at,
            l.name as location_name,
            up.display_name as user_name,
            au.email as user_email
        FROM location_notes ln
        LEFT JOIN locations l ON l.id = ln.location_id
        LEFT JOIN user_profiles up ON up.id = ln.user_id
        LEFT JOIN auth.users au ON au.id = ln.user_id
        ORDER BY ln.created_at DESC
        LIMIT $1 OFFSET $2
    """
    rows = await fetch(sql, limit, offset)
    
    return [
        {
            "id": row["id"],
            "location_id": row["location_id"],
            "location_name": row.get("location_name"),
            "user_id": str(row["user_id"]) if row.get("user_id") else None,
            "user_name": row.get("user_name"),
            "user_email": row.get("user_email"),
            "content": row.get("content"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        }
        for row in rows
    ]

