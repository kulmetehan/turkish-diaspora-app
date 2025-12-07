# Backend/api/routers/admin_bulletin.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.deps.admin_auth import verify_admin_user, AdminUser
from services.db_service import fetch, fetchrow, execute

router = APIRouter(prefix="/admin/bulletin", tags=["admin-bulletin"])


class BulletinPostModerationResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: str
    city: Optional[str]
    moderation_status: str
    moderation_result: Optional[dict]
    created_at: datetime
    creator_type: str
    view_count: int
    contact_count: int


class ModerateAction(BaseModel):
    action: str  # "approve" or "reject"
    reason: Optional[str] = None


@router.get("/review-queue", response_model=List[BulletinPostModerationResponse])
async def get_review_queue(
    status: Optional[str] = Query(None, description="Filter by moderation_status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """Get posts that need review (requires_review or reported)."""
    
    conditions = ["status != 'removed'"]
    params = []
    param_idx = 1
    
    if status:
        conditions.append(f"moderation_status = ${param_idx}")
        params.append(status)
        param_idx += 1
    else:
        # Default: show requires_review and reported
        conditions.append("moderation_status IN ('requires_review', 'reported')")
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
        SELECT id, title, description, category, city, moderation_status, moderation_result,
               created_at, creator_type, view_count, contact_count
        FROM bulletin_posts
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([limit, offset])
    
    rows = await fetch(sql, *params)
    
    return [
        BulletinPostModerationResponse(
            id=row["id"],
            title=row["title"],
            description=row.get("description"),
            category=row["category"],
            city=row.get("city"),
            moderation_status=row["moderation_status"],
            moderation_result=row.get("moderation_result"),
            created_at=row["created_at"],
            creator_type=row["creator_type"],
            view_count=row.get("view_count", 0),
            contact_count=row.get("contact_count", 0),
        )
        for row in rows
    ]


@router.post("/posts/{post_id}/moderate")
async def moderate_post(
    post_id: int = Path(..., description="Post ID"),
    action: ModerateAction = ...,
    admin: AdminUser = Depends(verify_admin_user),
):
    """Admin can manually approve/reject posts."""
    
    if action.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")
    
    # Verify post exists
    check_sql = "SELECT id, moderation_status FROM bulletin_posts WHERE id = $1"
    row = await fetchrow(check_sql, post_id)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if action.action == "approve":
        update_sql = """
            UPDATE bulletin_posts
            SET moderation_status = 'approved',
                status = 'active',
                published_at = COALESCE(published_at, now()),
                moderated_at = now(),
                updated_at = now()
            WHERE id = $1
        """
        await execute(update_sql, post_id)
        return {"ok": True, "message": "Post approved and published"}
    else:  # reject
        update_sql = """
            UPDATE bulletin_posts
            SET moderation_status = 'rejected',
                status = 'pending',
                updated_at = now(),
                moderated_at = now()
            WHERE id = $1
        """
        await execute(update_sql, post_id)
        return {"ok": True, "message": "Post rejected"}

