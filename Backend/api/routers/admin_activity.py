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
    check_in_id: int = Path(..., description="Check-in ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Delete a check-in (admin only).
    Hard delete - removes the check-in record completely.
    """
    # Check if check-in exists
    check_sql = "SELECT id FROM check_ins WHERE id = $1"
    check_row = await fetchrow(check_sql, check_in_id)
    
    if not check_row:
        raise HTTPException(status_code=404, detail="Check-in not found")
    
    # Delete check-in
    delete_sql = "DELETE FROM check_ins WHERE id = $1"
    await execute(delete_sql, check_in_id)
    
    logger.info(
        "admin_check_in_deleted",
        check_in_id=check_in_id,
        admin_email=admin.email,
    )
    
    return {"ok": True, "check_in_id": check_in_id}


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

