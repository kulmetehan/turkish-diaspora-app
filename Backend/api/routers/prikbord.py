# Backend/api/routers/prikbord.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from starlette.requests import Request
from pydantic import BaseModel, Field
import json

from app.deps.auth import get_current_user, get_current_user_optional, User
from app.deps.admin_auth import verify_admin_user, AdminUser
from services.db_service import fetch, fetchrow, execute
from services.link_preview_service import get_link_preview_service, Platform
from services.og_validation_service import get_og_validation_service
from app.core.logging import logger
from app.core.client_id import get_client_id

router = APIRouter(prefix="/prikbord", tags=["prikbord"])


# Request/Response models
class SharedLinkCreate(BaseModel):
    url: Optional[str] = None  # Made optional for media posts
    media_urls: List[str] = Field(default_factory=list)
    post_type: str = Field("link", pattern="^(link|media)$")
    linked_location_id: Optional[int] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    context_tags: List[str] = Field(default_factory=list)
    creator_type: str = Field("user", pattern="^(user|business)$")
    business_id: Optional[int] = None
    # Optional manual preview data (used when automatic preview fails)
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class CreatorInfo(BaseModel):
    type: str
    id: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    primary_role: Optional[str] = None
    secondary_role: Optional[str] = None
    verified: Optional[bool] = None


class SharedLinkResponse(BaseModel):
    id: int
    url: str
    platform: str
    title: Optional[str]
    description: Optional[str]
    image_url: Optional[str]
    video_url: Optional[str]
    preview_method: Optional[str]
    creator: CreatorInfo
    linked_location: Optional[dict] = None
    city: Optional[str]
    neighborhood: Optional[str]
    context_tags: List[str]
    media_urls: List[str] = Field(default_factory=list)
    post_type: str = "link"
    view_count: int
    like_count: int
    bookmark_count: int
    is_liked: bool = False
    is_bookmarked: bool = False
    reactions: Optional[dict] = None  # {reaction_type: count}
    user_reaction: Optional[str] = None  # Current user's reaction type
    created_at: datetime
    status: str


async def check_rate_limit(user_id: Optional[UUID], client_id: Optional[str], request: Request) -> None:
    """Check rate limit: 25 links/day per user, 20/day per IP."""
    from datetime import datetime, timedelta
    from services.db_service import fetchrow
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if user_id:
        # Check user limit
        check_sql = """
            SELECT COUNT(*) as count
            FROM shared_links
            WHERE created_by_user_id = $1
              AND created_at >= $2
        """
        row = await fetchrow(check_sql, user_id, today_start)
        if row and row.get("count", 0) >= 25:
            raise HTTPException(status_code=429, detail="Maximum 25 links per dag bereikt")
    else:
        # Check IP limit (simple check for anonymous users)
        check_sql = """
            SELECT COUNT(*) as count
            FROM shared_links
            WHERE created_by_user_id IS NULL
              AND created_at >= $1
        """
        row = await fetchrow(check_sql, today_start)
        if row and row.get("count", 0) >= 20:
            raise HTTPException(status_code=429, detail="Maximum 20 links per dag bereikt (anonieme gebruikers)")


@router.post("/links", response_model=SharedLinkResponse)
async def create_link(
    link: SharedLinkCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    client_id: Optional[str] = Depends(get_client_id),
):
    """Create a new shared link with automatic preview generation or manual preview data, or create a media post."""
    
    # Rate limiting
    await check_rate_limit(current_user.user_id, client_id, request)
    
    # Determine post_type and media_urls
    post_type = link.post_type
    media_urls = link.media_urls or []
    
    # If media_urls provided, ensure post_type is 'media'
    if media_urls and post_type == "link":
        post_type = "media"
    
    # Determine creator fields
    user_id = current_user.user_id if link.creator_type == "user" else None
    business_id = link.business_id if link.creator_type == "business" else None
    
    # Handle media posts differently
    if post_type == "media":
        # Validate media post
        if not media_urls:
            raise HTTPException(status_code=400, detail="Media posts vereisen minimaal één media bestand")
        
        # For media posts, use first media URL as placeholder URL if url not provided
        normalized_url = link.url or (media_urls[0] if media_urls else "")
        platform = Platform.MEDIA
        title = link.title or None
        description = link.description or None
        image_url = media_urls[0] if media_urls else None  # Use first media as preview
        video_url = None
        preview_method = "media_upload"
        preview_cache_expires_at = datetime.utcnow() + timedelta(days=7)
    else:
        # Handle link posts
        if not link.url:
            raise HTTPException(status_code=400, detail="Link posts vereisen een URL")
        
        # Normalize URL
        normalized_url = link.url.strip()
        if not normalized_url.startswith(("http://", "https://")):
            normalized_url = "https://" + normalized_url
        
        # Check for duplicate URL (only for link posts)
        check_sql = "SELECT id FROM shared_links WHERE url = $1 AND post_type = 'link'"
        existing = await fetchrow(check_sql, normalized_url)
        if existing:
            # Return existing link
            return await get_link_by_id(existing["id"], current_user)
        
        # Validate Open Graph metadata (only if manual preview data is not provided)
        if not (link.title or link.description or link.image_url):
            og_validation_service = get_og_validation_service()
            is_valid, error_message = await og_validation_service.validate_og_metadata(normalized_url)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_message or "Deze link kan niet worden gedeeld omdat er geen preview beschikbaar is. Probeer een link van YouTube, Marktplaats of een nieuwssite.")
        
        # Use manual preview data if provided, otherwise generate automatically
        if link.title or link.description or link.image_url:
            # Manual preview data provided
            preview_service = get_link_preview_service()
            platform = preview_service.detect_platform(normalized_url)
            
            title = link.title
            description = link.description
            image_url = link.image_url
            video_url = None
            preview_method = "manual"
        else:
            # Generate preview automatically
            preview_service = get_link_preview_service()
            try:
                preview = await preview_service.generate_preview(link.url)
                title = preview.title
                description = preview.description
                image_url = preview.image_url
                video_url = preview.video_url
                platform = preview.platform
                preview_method = preview.preview_method
            except Exception as e:
                logger.error("preview_generation_failed", url=link.url, error=str(e))
                raise HTTPException(status_code=400, detail=f"Kon preview niet genereren: {str(e)}")
        
        # Set preview cache expiry (7 days)
        preview_cache_expires_at = datetime.utcnow() + timedelta(days=7)
    
    # Insert link
    insert_sql = """
        INSERT INTO shared_links (
            url, platform, title, description, image_url, video_url,
            preview_method, preview_fetched_at, preview_cache_expires_at,
            created_by_user_id, created_by_business_id, creator_type,
            linked_location_id, city, neighborhood, context_tags,
            media_urls, post_type,
            created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, now(), $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, now(), now()
        ) RETURNING *
    """
    
    try:
        row = await fetchrow(
            insert_sql,
            normalized_url,
            platform.value,
            title,
            description,
            image_url,
            video_url,
            preview_method,
            preview_cache_expires_at,
            user_id,
            business_id,
            link.creator_type,
            link.linked_location_id,
            link.city,
            link.neighborhood,
            link.context_tags,
            media_urls,
            post_type,
        )
    except Exception as e:
        logger.error("shared_link_insert_failed", error=str(e), url=link.url)
        raise HTTPException(status_code=500, detail=f"Failed to create link: {str(e)}")
    
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create link")
    
    return await _build_link_response(row, current_user)


@router.get("/platforms")
async def get_available_platforms():
    """Get list of platforms that have active content."""
    sql = """
        SELECT DISTINCT platform
        FROM shared_links
        WHERE status = 'active'
        ORDER BY platform
    """
    rows = await fetch(sql)
    platforms = [row["platform"] for row in rows]
    return {"platforms": platforms}


@router.get("/links", response_model=List[SharedLinkResponse])
async def list_links(
    platform: Optional[str] = Query(None, pattern="^(marktplaats|instagram|facebook|youtube|twitter|tiktok|news|event|other)$"),
    city: Optional[str] = None,
    tags: Optional[str] = Query(None, description="Comma-separated context tags"),
    trending: bool = Query(False, description="Show trending links"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """List shared links with filtering."""
    
    # Build WHERE clause
    conditions = ["status = 'active'"]
    params = []
    param_idx = 1
    
    if platform:
        conditions.append(f"platform = ${param_idx}")
        params.append(platform)
        param_idx += 1
    
    if city:
        conditions.append(f"city = ${param_idx}")
        params.append(city)
        param_idx += 1
    
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        conditions.append(f"context_tags && ${param_idx}::text[]")
        params.append(tag_list)
        param_idx += 1
    
    where_clause = " AND ".join(conditions)
    
    # Build ORDER BY
    if trending:
        # Trending: views + likes, time-weighted
        order_by = """
            ORDER BY (
                (view_count * 1.0 + like_count * 2.0) * 
                EXP(-EXTRACT(EPOCH FROM (now() - created_at)) / 86400.0 / 7.0)
            ) DESC
        """
    else:
        order_by = "ORDER BY created_at DESC"
    
    sql = f"""
        SELECT *
        FROM shared_links
        WHERE {where_clause}
        {order_by}
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([limit, offset])
    
    rows = await fetch(sql, *params)
    
    links = []
    for row in rows:
        links.append(await _build_link_response(row, current_user))
    
    return links


async def get_link_by_id(link_id: int, current_user: Optional[User] = None) -> SharedLinkResponse:
    """Helper to get a single link by ID."""
    sql = "SELECT * FROM shared_links WHERE id = $1 AND status != 'removed'"
    row = await fetchrow(sql, link_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Link not found")
    
    return await _build_link_response(row, current_user)


@router.get("/links/{link_id}", response_model=SharedLinkResponse)
async def get_link(
    link_id: int = Path(..., description="Link ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    client_id: Optional[str] = Depends(get_client_id),
):
    """Get a single link. Increments view count."""
    
    link = await get_link_by_id(link_id, current_user)
    
    # Track view (only once per user/client per link)
    if current_user or client_id:
        try:
            check_sql = """
                SELECT 1 FROM shared_link_interactions
                WHERE link_id = $1 
                  AND interaction_type = 'view'
                  AND (($2 IS NOT NULL AND user_id = $2) OR ($3 IS NOT NULL AND client_id = $3))
                LIMIT 1
            """
            existing = await fetchrow(
                check_sql,
                link_id,
                current_user.user_id if current_user else None,
                client_id if not current_user else None,
            )
            
            if not existing:
                interaction_sql = """
                    INSERT INTO shared_link_interactions (link_id, user_id, client_id, interaction_type, created_at)
                    VALUES ($1, $2, $3, 'view', now())
                """
                await execute(
                    interaction_sql,
                    link_id,
                    current_user.user_id if current_user else None,
                    client_id if not current_user else None,
                )
        except Exception as e:
            logger.warning("shared_link_view_tracking_failed", error=str(e), link_id=link_id)
    
    return link


@router.post("/links/{link_id}/like")
async def toggle_like(
    link_id: int = Path(..., description="Link ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    client_id: Optional[str] = Depends(get_client_id),
):
    """Toggle like on a link."""
    
    # Verify link exists
    check_sql = "SELECT id FROM shared_links WHERE id = $1 AND status = 'active'"
    check_row = await fetchrow(check_sql, link_id)
    if not check_row:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if not current_user and not client_id:
        raise HTTPException(status_code=401, detail="Authentication or client ID required")
    
    # Check if already liked
    check_like_sql = """
        SELECT id FROM shared_link_interactions
        WHERE link_id = $1 
          AND interaction_type = 'like'
          AND (($2 IS NOT NULL AND user_id = $2) OR ($3 IS NOT NULL AND client_id = $3))
        LIMIT 1
    """
    existing = await fetchrow(
        check_like_sql,
        link_id,
        current_user.user_id if current_user else None,
        client_id if not current_user else None,
    )
    
    if existing:
        # Unlike: delete interaction
        delete_sql = """
            DELETE FROM shared_link_interactions
            WHERE id = $1
        """
        await execute(delete_sql, existing["id"])
        return {"liked": False}
    else:
        # Like: create interaction
        insert_sql = """
            INSERT INTO shared_link_interactions (link_id, user_id, client_id, interaction_type, created_at)
            VALUES ($1, $2, $3, 'like', now())
        """
        await execute(
            insert_sql,
            link_id,
            current_user.user_id if current_user else None,
            client_id if not current_user else None,
        )
        return {"liked": True}


@router.post("/links/{link_id}/bookmark")
async def toggle_bookmark(
    link_id: int = Path(..., description="Link ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    client_id: Optional[str] = Depends(get_client_id),
):
    """Toggle bookmark on a link."""
    
    # Verify link exists
    check_sql = "SELECT id FROM shared_links WHERE id = $1 AND status = 'active'"
    check_row = await fetchrow(check_sql, link_id)
    if not check_row:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if not current_user and not client_id:
        raise HTTPException(status_code=401, detail="Authentication or client ID required")
    
    # Check if already bookmarked
    check_bookmark_sql = """
        SELECT id FROM shared_link_interactions
        WHERE link_id = $1 
          AND interaction_type = 'bookmark'
          AND (($2 IS NOT NULL AND user_id = $2) OR ($3 IS NOT NULL AND client_id = $3))
        LIMIT 1
    """
    existing = await fetchrow(
        check_bookmark_sql,
        link_id,
        current_user.user_id if current_user else None,
        client_id if not current_user else None,
    )
    
    if existing:
        # Unbookmark: delete interaction
        delete_sql = """
            DELETE FROM shared_link_interactions
            WHERE id = $1
        """
        await execute(delete_sql, existing["id"])
        return {"bookmarked": False}
    else:
        # Bookmark: create interaction
        insert_sql = """
            INSERT INTO shared_link_interactions (link_id, user_id, client_id, interaction_type, created_at)
            VALUES ($1, $2, $3, 'bookmark', now())
        """
        await execute(
            insert_sql,
            link_id,
            current_user.user_id if current_user else None,
            client_id if not current_user else None,
        )
        return {"bookmarked": True}


class ReactionToggleRequest(BaseModel):
    reaction_type: str  # Emoji string (e.g., "🔥", "❤️", "👍", etc.)


@router.post("/links/{link_id}/reactions", response_model=dict)
async def toggle_link_reaction(
    link_id: int = Path(..., description="Link ID"),
    request: ReactionToggleRequest = ...,
    client_id: Optional[str] = Depends(get_client_id),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Toggle emoji reaction on a shared link."""
    
    user_id = current_user.user_id if current_user else None
    
    if not user_id and not client_id:
        raise HTTPException(status_code=400, detail="Either authentication or client_id required")
    
    # Basic validation: ensure reaction_type is a non-empty string
    if not request.reaction_type or not isinstance(request.reaction_type, str) or len(request.reaction_type.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="reaction_type must be a non-empty string (emoji)"
        )
    
    # Limit emoji length to prevent abuse
    if len(request.reaction_type) > 10:
        raise HTTPException(
            status_code=400,
            detail="reaction_type too long (max 10 characters)"
        )
    
    # Check if link exists
    check_sql = "SELECT id FROM shared_links WHERE id = $1 AND status = 'active'"
    check_row = await fetchrow(check_sql, link_id)
    if not check_row:
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Check if already reacted with this type
    if user_id:
        check_reaction_sql = """
            SELECT id FROM shared_link_reactions 
            WHERE link_id = $1 AND user_id = $2 AND reaction_type = $3
        """
        existing = await fetchrow(check_reaction_sql, link_id, user_id, request.reaction_type)
    else:
        check_reaction_sql = """
            SELECT id FROM shared_link_reactions 
            WHERE link_id = $1 AND client_id = $2 AND reaction_type = $3
        """
        existing = await fetchrow(check_reaction_sql, link_id, client_id, request.reaction_type)
    
    if existing:
        # Remove reaction
        if user_id:
            delete_sql = """
                DELETE FROM shared_link_reactions 
                WHERE link_id = $1 AND user_id = $2 AND reaction_type = $3
            """
            await execute(delete_sql, link_id, user_id, request.reaction_type)
        else:
            delete_sql = """
                DELETE FROM shared_link_reactions 
                WHERE link_id = $1 AND client_id = $2 AND reaction_type = $3
            """
            await execute(delete_sql, link_id, client_id, request.reaction_type)
        is_active = False
    else:
        # Add reaction
        if user_id:
            insert_sql = """
                INSERT INTO shared_link_reactions (link_id, user_id, reaction_type) 
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """
            await execute(insert_sql, link_id, user_id, request.reaction_type)
        else:
            insert_sql = """
                INSERT INTO shared_link_reactions (link_id, client_id, reaction_type) 
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """
            await execute(insert_sql, link_id, client_id, request.reaction_type)
        is_active = True
    
    # Get updated count
    count_sql = """
        SELECT COUNT(*) as count 
        FROM shared_link_reactions 
        WHERE link_id = $1 AND reaction_type = $2
    """
    count_rows = await fetch(count_sql, link_id, request.reaction_type)
    count = count_rows[0]["count"] if count_rows else 0
    
    return {
        "reaction_type": request.reaction_type,
        "is_active": is_active,
        "count": count
    }


@router.get("/links/{link_id}/reactions", response_model=dict)
async def get_link_reactions(
    link_id: int = Path(..., description="Link ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get reaction counts for a shared link."""
    
    # Check if link exists
    check_sql = "SELECT id FROM shared_links WHERE id = $1 AND status = 'active'"
    check_row = await fetchrow(check_sql, link_id)
    if not check_row:
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Get reaction counts grouped by type
    counts_sql = """
        SELECT reaction_type, COUNT(*) as count
        FROM shared_link_reactions
        WHERE link_id = $1
        GROUP BY reaction_type
        ORDER BY count DESC, reaction_type ASC
    """
    count_rows = await fetch(counts_sql, link_id)
    
    # Build reactions dict dynamically from database results
    reactions: dict = {}
    for row in count_rows:
        reaction_type = row["reaction_type"]
        reactions[reaction_type] = row["count"]
    
    # Get user's reaction if authenticated
    user_reaction = None
    if current_user:
        user_reaction_sql = """
            SELECT reaction_type
            FROM shared_link_reactions
            WHERE link_id = $1 AND user_id = $2
            LIMIT 1
        """
        user_reaction_rows = await fetch(user_reaction_sql, link_id, current_user.user_id)
        if user_reaction_rows:
            user_reaction = user_reaction_rows[0]["reaction_type"]
    
    return {
        "reactions": reactions,
        "user_reaction": user_reaction
    }


@router.get("/links/trending", response_model=List[SharedLinkResponse])
async def get_trending_links(
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get trending links (most viewed/liked, time-weighted)."""
    return await list_links(trending=True, limit=limit, current_user=current_user)


@router.delete("/links/{link_id}")
async def delete_link(
    link_id: int = Path(..., description="Link ID"),
    current_user: User = Depends(get_current_user),
):
    """Delete own link."""
    
    # Verify ownership
    check_sql = """
        SELECT id, created_by_user_id, created_by_business_id, creator_type
        FROM shared_links
        WHERE id = $1
    """
    row = await fetchrow(check_sql, link_id)
    if not row:
        raise HTTPException(status_code=404, detail="Link not found")
    
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
        raise HTTPException(status_code=403, detail="Not authorized to delete this link")
    
    # Soft delete
    delete_sql = """
        UPDATE shared_links
        SET status = 'removed', updated_at = now()
        WHERE id = $1
    """
    await execute(delete_sql, link_id)
    
    return {"ok": True, "message": "Link deleted successfully"}


@router.get("/links/admin/list")
async def list_links_admin(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """List all shared links (admin only)."""
    sql = """
        SELECT 
            sl.id,
            sl.url,
            sl.title,
            sl.description,
            sl.platform,
            sl.status,
            sl.created_at,
            sl.created_by_user_id,
            up.display_name as user_name,
            au.email as user_email
        FROM shared_links sl
        LEFT JOIN user_profiles up ON up.id = sl.created_by_user_id
        LEFT JOIN auth.users au ON au.id = sl.created_by_user_id
        ORDER BY sl.created_at DESC
        LIMIT $1 OFFSET $2
    """
    rows = await fetch(sql, limit, offset)
    
    return [
        {
            "id": row["id"],
            "url": row["url"],
            "title": row.get("title"),
            "description": row.get("description"),
            "platform": row.get("platform"),
            "status": row.get("status"),
            "user_id": str(row["created_by_user_id"]) if row.get("created_by_user_id") else None,
            "user_name": row.get("user_name"),
            "user_email": row.get("user_email"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        }
        for row in rows
    ]


@router.delete("/links/{link_id}/admin")
async def delete_link_admin(
    link_id: int = Path(..., description="Link ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """Delete any shared link (admin only)."""
    
    # Check if link exists
    check_sql = "SELECT id FROM shared_links WHERE id = $1"
    check_row = await fetchrow(check_sql, link_id)
    
    if not check_row:
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Soft delete
    delete_sql = """
        UPDATE shared_links
        SET status = 'removed', updated_at = now()
        WHERE id = $1
    """
    await execute(delete_sql, link_id)
    
    logger.info(
        "admin_shared_link_deleted",
        link_id=link_id,
        admin_email=admin.email,
    )
    
    return {"ok": True, "link_id": link_id, "message": "Link deleted successfully"}


async def _build_link_response(row: dict, current_user: Optional[User] = None) -> SharedLinkResponse:
    """Build SharedLinkResponse from database row."""
    
    # Fetch creator info
    creator_info = {"type": "unknown"}
    if row["creator_type"] == "business":
        creator_sql = """
            SELECT id, company_name, EXISTS(
                SELECT 1 FROM business_location_claims blc
                WHERE blc.business_account_id = ba.id AND blc.status = 'approved'
                LIMIT 1
            ) as verified
            FROM business_accounts ba
            WHERE ba.id = $1
        """
        creator_row = await fetchrow(creator_sql, row["created_by_business_id"])
        if creator_row:
            creator_info = {
                "type": "business",
                "id": str(creator_row["id"]),
                "name": creator_row["company_name"],
                "verified": creator_row.get("verified", False),
            }
    else:
        creator_sql = """
            SELECT 
                up.id, 
                COALESCE(up.display_name, split_part(au.email, '@', 1)) as name,
                up.avatar_url,
                ur.primary_role,
                ur.secondary_role
            FROM user_profiles up
            INNER JOIN auth.users au ON au.id = up.id
            LEFT JOIN user_roles ur ON ur.user_id = up.id
            WHERE up.id = $1
        """
        creator_row = await fetchrow(creator_sql, row["created_by_user_id"])
        if creator_row:
            creator_info = {
                "type": "user",
                "id": str(creator_row["id"]),
                "name": creator_row["name"],
                "avatar_url": creator_row.get("avatar_url"),
                "primary_role": creator_row.get("primary_role"),
                "secondary_role": creator_row.get("secondary_role"),
            }
    
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
    
    # Check if current user has liked/bookmarked
    is_liked = False
    is_bookmarked = False
    user_id = current_user.user_id if current_user else None
    if user_id:
        interaction_sql = """
            SELECT interaction_type
            FROM shared_link_interactions
            WHERE link_id = $1 AND user_id = $2 AND interaction_type IN ('like', 'bookmark')
        """
        interactions = await fetch(interaction_sql, row["id"], user_id)
        for interaction in interactions:
            if interaction["interaction_type"] == "like":
                is_liked = True
            elif interaction["interaction_type"] == "bookmark":
                is_bookmarked = True
    
    # Get reaction counts
    reactions_sql = """
        SELECT reaction_type, COUNT(*) as count
        FROM shared_link_reactions
        WHERE link_id = $1
        GROUP BY reaction_type
        ORDER BY count DESC, reaction_type ASC
    """
    reaction_rows = await fetch(reactions_sql, row["id"])
    reactions = {}
    for r_row in reaction_rows:
        reactions[r_row["reaction_type"]] = r_row["count"]
    
    # Get user's reaction if authenticated
    user_reaction = None
    if user_id:
        user_reaction_sql = """
            SELECT reaction_type
            FROM shared_link_reactions
            WHERE link_id = $1 AND user_id = $2
            LIMIT 1
        """
        user_reaction_rows = await fetch(user_reaction_sql, row["id"], user_id)
        if user_reaction_rows:
            user_reaction = user_reaction_rows[0]["reaction_type"]
    
    return SharedLinkResponse(
        id=row["id"],
        url=row["url"],
        platform=row["platform"],
        title=row.get("title"),
        description=row.get("description"),
        image_url=row.get("image_url"),
        video_url=row.get("video_url"),
        preview_method=row.get("preview_method"),
        creator=CreatorInfo(**creator_info),
        linked_location=linked_location,
        city=row.get("city"),
        neighborhood=row.get("neighborhood"),
        context_tags=row.get("context_tags") or [],
        media_urls=row.get("media_urls") or [],
        post_type=row.get("post_type", "link"),
        view_count=row.get("view_count", 0),
        like_count=row.get("like_count", 0),
        bookmark_count=row.get("bookmark_count", 0),
        is_liked=is_liked,
        is_bookmarked=is_bookmarked,
        reactions=reactions if reactions else None,
        user_reaction=user_reaction,
        created_at=row["created_at"],
        status=row["status"],
    )

