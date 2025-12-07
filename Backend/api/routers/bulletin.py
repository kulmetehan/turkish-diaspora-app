# Backend/api/routers/bulletin.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field, field_validator
import json

from app.deps.auth import get_current_user, get_current_user_optional, User
from app.models.ai import ContentModerationResult, ModerationDecision
from services.db_service import fetch, fetchrow, execute
from services.moderation_service import get_moderation_service
from app.core.logging import logger
from app.core.client_id import get_client_id

router = APIRouter(prefix="/bulletin", tags=["bulletin"])


# Request/Response models
class BulletinPostCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    category: str = Field(..., pattern="^(personnel_wanted|offer|free_for_sale|event|services|other)$")
    creator_type: str = Field(..., pattern="^(user|business)$")
    business_id: Optional[int] = None  # Required if creator_type='business'
    linked_location_id: Optional[int] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    contact_whatsapp: Optional[str] = None
    show_contact_info: bool = True
    image_urls: List[str] = Field(default_factory=list)
    expires_in_days: int = Field(7, ge=1, le=365)  # Default 7 days, max 1 year
    
    @field_validator("business_id")
    @classmethod
    def validate_business_id(cls, v, info):
        creator_type = info.data.get("creator_type")
        if creator_type == "business" and not v:
            raise ValueError("business_id is required when creator_type='business'")
        return v


class CreatorInfo(BaseModel):
    type: str
    id: Optional[str] = None
    name: Optional[str] = None
    verified: Optional[bool] = None


class BulletinPostResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: str
    city: Optional[str]
    neighborhood: Optional[str]
    linked_location: Optional[dict] = None
    contact_info: Optional[dict] = None  # Only if show_contact_info = true
    image_urls: List[str]
    creator: CreatorInfo
    view_count: int
    contact_count: int
    created_at: datetime
    expires_at: Optional[datetime]
    status: str
    moderation_status: str
    moderation_message: Optional[str] = None


class BulletinReportRequest(BaseModel):
    reason: str
    details: Optional[str] = None


@router.post("/posts", response_model=BulletinPostResponse)
async def create_post(
    post: BulletinPostCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new bulletin post with AI moderation."""
    
    # Step 1: Moderate content via AI
    moderation_service = get_moderation_service()
    
    try:
        moderation_result, moderation_meta = moderation_service.moderate_post(
            title=post.title,
            description=post.description,
            category=post.category,
            city=post.city,
        )
        
        # Extract ai_log_id from meta if available (we'll store it later)
        ai_log_id = None  # Will be extracted from meta if available
        
    except Exception as e:
        # If moderation fails, default to requires_review for safety
        logger.error("moderation_failed", error=str(e), post_title=post.title)
        moderation_result = ContentModerationResult(
            decision=ModerationDecision.REQUIRES_REVIEW,
            confidence_score=0.0,
            reason="uncertain_context",
            details=f"Moderation failed: {str(e)}"
        )
        ai_log_id = None
        moderation_meta = {}
    
    # Step 2: Determine initial status based on moderation
    if moderation_result.decision == ModerationDecision.APPROVED:
        initial_status = "active"
        moderation_status = "approved"
        published_at = datetime.utcnow()
    elif moderation_result.decision == ModerationDecision.REJECTED:
        initial_status = "pending"  # Will stay pending
        moderation_status = "rejected"
        published_at = None
    else:  # REQUIRES_REVIEW
        initial_status = "pending"
        moderation_status = "requires_review"
        published_at = None
    
    # Step 3: Insert post with moderation result
    expires_at = datetime.utcnow() + timedelta(days=post.expires_in_days)
    
    # Determine creator fields
    user_id = current_user.user_id if post.creator_type == "user" else None
    business_id = post.business_id if post.creator_type == "business" else None
    
    sql = """
        INSERT INTO bulletin_posts (
            created_by_user_id,
            created_by_business_id,
            creator_type,
            title,
            description,
            category,
            city,
            neighborhood,
            linked_location_id,
            contact_phone,
            contact_email,
            contact_whatsapp,
            show_contact_info,
            image_urls,
            status,
            moderation_status,
            moderation_result,
            moderated_at,
            moderation_ai_log_id,
            expires_at,
            published_at,
            created_at,
            updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, now(), now()
        ) RETURNING *
    """
    
    try:
        row = await fetchrow(
            sql,
            user_id,
            business_id,
            post.creator_type,
            post.title,
            post.description,
            post.category,
            post.city,
            post.neighborhood,
            post.linked_location_id,
            post.contact_phone,
            post.contact_email,
            post.contact_whatsapp,
            post.show_contact_info,
            post.image_urls,
            initial_status,
            moderation_status,
            json.dumps(moderation_result.model_dump(), default=str),
            datetime.utcnow() if moderation_status != "pending" else None,
            ai_log_id,
            expires_at,
            published_at,
        )
    except Exception as e:
        logger.error("bulletin_post_insert_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create post: {str(e)}")
    
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create post")
    
    # Step 4: If rejected, return error with reason
    if moderation_result.decision == ModerationDecision.REJECTED:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Je advertentie kan niet worden goedgekeurd.",
                "reason": moderation_result.reason.value,
                "details": moderation_result.details,
            }
        )
    
    # Step 5: Build response with creator info
    # Fetch creator info using the database function
    creator_sql = "SELECT get_bulletin_post_creator($1::BIGINT) as creator_info"
    creator_row = await fetchrow(creator_sql, row["id"])
    creator_data_raw = creator_row["creator_info"] if creator_row else '{"type": "unknown"}'
    # Parse JSONB if it's a string (asyncpg sometimes returns JSONB as string)
    if isinstance(creator_data_raw, str):
        creator_data = json.loads(creator_data_raw)
    else:
        creator_data = creator_data_raw
    
    # Build contact info if show_contact_info is true
    contact_info = None
    if row["show_contact_info"]:
        contact_info = {}
        if row["contact_phone"]:
            contact_info["phone"] = row["contact_phone"]
        if row["contact_email"]:
            contact_info["email"] = row["contact_email"]
        if row["contact_whatsapp"]:
            contact_info["whatsapp"] = row["contact_whatsapp"]
    
    # Fetch linked location if present
    linked_location = None
    if row["linked_location_id"]:
        loc_sql = "SELECT id, name, address FROM locations WHERE id = $1"
        loc_row = await fetchrow(loc_sql, row["linked_location_id"])
        if loc_row:
            linked_location = {
                "id": loc_row["id"],
                "name": loc_row["name"],
                "address": loc_row.get("address"),
            }
    
    response_data = {
        "id": row["id"],
        "title": row["title"],
        "description": row.get("description"),
        "category": row["category"],
        "city": row.get("city"),
        "neighborhood": row.get("neighborhood"),
        "linked_location": linked_location,
        "contact_info": contact_info,
        "image_urls": row.get("image_urls") or [],
        "creator": CreatorInfo(**creator_data),
        "view_count": row.get("view_count", 0),
        "contact_count": row.get("contact_count", 0),
        "created_at": row["created_at"],
        "expires_at": row.get("expires_at"),
        "status": row["status"],
        "moderation_status": row["moderation_status"],
    }
    
    # Add moderation message if requires_review
    if moderation_result.decision == ModerationDecision.REQUIRES_REVIEW:
        response_data["moderation_message"] = (
            "Je advertentie is ingediend en wordt binnenkort beoordeeld door ons team."
        )
    
    return BulletinPostResponse(**response_data)


@router.get("/posts", response_model=List[BulletinPostResponse])
async def list_posts(
    status: str = Query("active", pattern="^(active|pending|expired|all)$"),
    category: Optional[str] = Query(None, pattern="^(personnel_wanted|offer|free_for_sale|event|services|other)$"),
    city: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """List bulletin posts with filtering."""
    
    # Build WHERE clause
    conditions = []
    params = []
    param_idx = 1
    
    if status != "all":
        conditions.append(f"status = ${param_idx}")
        params.append(status)
        param_idx += 1
    else:
        conditions.append(f"status != 'removed'")
    
    if category:
        conditions.append(f"category = ${param_idx}")
        params.append(category)
        param_idx += 1
    
    if city:
        conditions.append(f"city = ${param_idx}")
        params.append(city)
        param_idx += 1
    
    if search:
        conditions.append(f"(title ILIKE ${param_idx} OR description ILIKE ${param_idx})")
        search_pattern = f"%{search}%"
        params.append(search_pattern)
        params.append(search_pattern)
        param_idx += 2
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    sql = f"""
        SELECT *
        FROM bulletin_posts
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([limit, offset])
    
    rows = await fetch(sql, *params)
    
    posts = []
    for row in rows:
        # Fetch creator info
        creator_sql = "SELECT get_bulletin_post_creator($1::BIGINT) as creator_info"
        creator_row = await fetchrow(creator_sql, row["id"])
        creator_data_raw = creator_row["creator_info"] if creator_row else '{"type": "unknown"}'
        # Parse JSONB if it's a string (asyncpg sometimes returns JSONB as string)
        if isinstance(creator_data_raw, str):
            creator_data = json.loads(creator_data_raw)
        else:
            creator_data = creator_data_raw
        
        # Build contact info
        contact_info = None
        if row["show_contact_info"]:
            contact_info = {}
            if row["contact_phone"]:
                contact_info["phone"] = row["contact_phone"]
            if row["contact_email"]:
                contact_info["email"] = row["contact_email"]
            if row["contact_whatsapp"]:
                contact_info["whatsapp"] = row["contact_whatsapp"]
        
        # Fetch linked location
        linked_location = None
        if row["linked_location_id"]:
            loc_sql = "SELECT id, name, address FROM locations WHERE id = $1"
            loc_row = await fetchrow(loc_sql, row["linked_location_id"])
            if loc_row:
                linked_location = {
                    "id": loc_row["id"],
                    "name": loc_row["name"],
                    "address": loc_row.get("address"),
                }
        
        posts.append(BulletinPostResponse(
            id=row["id"],
            title=row["title"],
            description=row.get("description"),
            category=row["category"],
            city=row.get("city"),
            neighborhood=row.get("neighborhood"),
            linked_location=linked_location,
            contact_info=contact_info,
            image_urls=row.get("image_urls") or [],
            creator=CreatorInfo(**creator_data),
            view_count=row.get("view_count", 0),
            contact_count=row.get("contact_count", 0),
            created_at=row["created_at"],
            expires_at=row.get("expires_at"),
            status=row["status"],
            moderation_status=row["moderation_status"],
        ))
    
    return posts


@router.get("/posts/{post_id}", response_model=BulletinPostResponse)
async def get_post(
    post_id: int = Path(..., description="Post ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    client_id: Optional[str] = Depends(get_client_id),
):
    """Get a single post. Increments view count."""
    
    sql = "SELECT * FROM bulletin_posts WHERE id = $1 AND status != 'removed'"
    row = await fetchrow(sql, post_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Track view in interactions table (only once per user/client per post)
    if current_user or client_id:
        try:
            # Check if already viewed
            check_sql = """
                SELECT 1 FROM bulletin_post_interactions
                WHERE post_id = $1 
                  AND interaction_type = 'view'
                  AND (($2 IS NOT NULL AND user_id = $2) OR ($3 IS NOT NULL AND client_id = $3))
                LIMIT 1
            """
            existing = await fetchrow(
                check_sql,
                post_id,
                current_user.user_id if current_user else None,
                client_id if not current_user else None,
            )
            
            if not existing:
                interaction_sql = """
                    INSERT INTO bulletin_post_interactions (post_id, user_id, client_id, interaction_type, created_at)
                    VALUES ($1, $2, $3, 'view', now())
                """
                await execute(
                    interaction_sql,
                    post_id,
                    current_user.user_id if current_user else None,
                    client_id if not current_user else None,
                )
        except Exception as e:
            logger.warning("bulletin_view_tracking_failed", error=str(e), post_id=post_id)
    
    # Fetch creator info
    creator_sql = "SELECT get_bulletin_post_creator($1::BIGINT) as creator_info"
    creator_row = await fetchrow(creator_sql, post_id)
    creator_data_raw = creator_row["creator_info"] if creator_row else '{"type": "unknown"}'
    # Parse JSONB if it's a string (asyncpg sometimes returns JSONB as string)
    if isinstance(creator_data_raw, str):
        creator_data = json.loads(creator_data_raw)
    else:
        creator_data = creator_data_raw
    
    # Build contact info
    contact_info = None
    if row["show_contact_info"]:
        contact_info = {}
        if row["contact_phone"]:
            contact_info["phone"] = row["contact_phone"]
        if row["contact_email"]:
            contact_info["email"] = row["contact_email"]
        if row["contact_whatsapp"]:
            contact_info["whatsapp"] = row["contact_whatsapp"]
    
    # Fetch linked location
    linked_location = None
    if row["linked_location_id"]:
        loc_sql = "SELECT id, name, address FROM locations WHERE id = $1"
        loc_row = await fetchrow(loc_sql, row["linked_location_id"])
        if loc_row:
            linked_location = {
                "id": loc_row["id"],
                "name": loc_row["name"],
                "address": loc_row.get("address"),
            }
    
    return BulletinPostResponse(
        id=row["id"],
        title=row["title"],
        description=row.get("description"),
        category=row["category"],
        city=row.get("city"),
        neighborhood=row.get("neighborhood"),
        linked_location=linked_location,
        contact_info=contact_info,
        image_urls=row.get("image_urls") or [],
        creator=CreatorInfo(**creator_data),
        view_count=row.get("view_count", 0),
        contact_count=row.get("contact_count", 0),
        created_at=row["created_at"],
        expires_at=row.get("expires_at"),
        status=row["status"],
        moderation_status=row["moderation_status"],
    )


@router.post("/posts/{post_id}/contact")
async def track_contact_click(
    post_id: int = Path(..., description="Post ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    client_id: Optional[str] = Depends(get_client_id),
):
    """Track when someone clicks contact info."""
    
    # Verify post exists
    check_sql = "SELECT id FROM bulletin_posts WHERE id = $1 AND status = 'active'"
    check_row = await fetchrow(check_sql, post_id)
    if not check_row:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Log interaction
    try:
        interaction_sql = """
            INSERT INTO bulletin_post_interactions (post_id, user_id, client_id, interaction_type, created_at)
            VALUES ($1, $2, $3, 'contact_click', now())
        """
        await execute(
            interaction_sql,
            post_id,
            current_user.user_id if current_user else None,
            client_id if not current_user else None,
        )
    except Exception as e:
        logger.warning("bulletin_contact_tracking_failed", error=str(e), post_id=post_id)
    
    return {"ok": True}


@router.post("/posts/{post_id}/report")
async def report_post(
    post_id: int = Path(..., description="Post ID"),
    report: BulletinReportRequest = ...,
    current_user: Optional[User] = Depends(get_current_user_optional),
    client_id: Optional[str] = Depends(get_client_id),
):
    """Report a post for moderation."""
    
    # Verify post exists
    check_sql = "SELECT id FROM bulletin_posts WHERE id = $1 AND status != 'removed'"
    check_row = await fetchrow(check_sql, post_id)
    if not check_row:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Verify we have an identity
    if not current_user and not client_id:
        raise HTTPException(status_code=400, detail="Client ID or authentication required")
    
    # Create report entry
    try:
        report_sql = """
            INSERT INTO bulletin_post_reports (
                post_id, reported_by_user_id, reported_by_client_id, reason, details, created_at
            ) VALUES ($1, $2, $3, $4, $5, now())
        """
        await execute(
            report_sql,
            post_id,
            current_user.user_id if current_user else None,
            client_id if not current_user else None,
            report.reason,
            report.details,
        )
        # Trigger will auto-set moderation_status to 'reported' if 3+ reports
    except Exception as e:
        logger.error("bulletin_report_failed", error=str(e), post_id=post_id)
        raise HTTPException(status_code=500, detail=f"Failed to submit report: {str(e)}")
    
    return {"ok": True, "message": "Report submitted successfully"}


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int = Path(..., description="Post ID"),
    current_user: User = Depends(get_current_user),
):
    """Delete own post."""
    
    # Verify ownership
    check_sql = """
        SELECT id, created_by_user_id, created_by_business_id, creator_type
        FROM bulletin_posts
        WHERE id = $1
    """
    row = await fetchrow(check_sql, post_id)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check ownership
    is_owner = False
    if row["creator_type"] == "user" and row["created_by_user_id"] == current_user.user_id:
        is_owner = True
    elif row["creator_type"] == "business":
        # Check if user owns the business account
        business_check_sql = "SELECT id FROM business_accounts WHERE id = $1 AND owner_user_id = $2"
        business_row = await fetchrow(business_check_sql, row["created_by_business_id"], current_user.user_id)
        if business_row:
            is_owner = True
    
    if not is_owner:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    # Soft delete
    delete_sql = """
        UPDATE bulletin_posts
        SET status = 'removed', removed_at = now(), updated_at = now()
        WHERE id = $1
    """
    await execute(delete_sql, post_id)
    
    return {"ok": True, "message": "Post deleted successfully"}

