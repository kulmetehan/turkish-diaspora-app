# Backend/api/routers/admin_chat.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.deps.admin_auth import verify_admin_user, AdminUser
from services.db_service import fetch, fetchrow, execute
from services.chat_service import get_chat_service

router = APIRouter(prefix="/admin/chat", tags=["admin-chat"])


class GeneralTopicCreate(BaseModel):
    title: str
    description: Optional[str] = None
    topic_category: Optional[str] = None
    image_url: Optional[str] = None


class GeneralTopicUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    topic_category: Optional[str] = None
    image_url: Optional[str] = None


class ChatTopicResponse(BaseModel):
    id: int
    content_type: str
    content_id: int
    title: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_at: Optional[datetime] = None
    is_active: bool
    image_url: Optional[str] = None
    is_pinned: bool
    pinned_at: Optional[datetime] = None
    topic_category: Optional[str] = None


@router.post("/topics/general", response_model=ChatTopicResponse)
async def create_general_topic(
    topic: GeneralTopicCreate,
    admin: AdminUser = Depends(verify_admin_user),
):
    """Create a general chat topic (Turkchat)."""
    
    if not topic.title or not topic.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    
    chat_service = get_chat_service()
    
    try:
        # Create general topic with content_type = 'general' and content_id = 0 (placeholder)
        # Note: General topics don't have a real content_id, but we need unique constraint
        # We'll use a negative ID or generate a unique one
        # For now, use topic_id itself as content_id (will need to handle uniqueness)
        
        # First, get the next topic ID to use as content_id for uniqueness
        next_id_sql = "SELECT COALESCE(MAX(id), 0) + 1 FROM chat_topics"
        next_id_result = await fetchrow(next_id_sql)
        next_id = next_id_result[0] if next_id_result else 1
        
        # Create topic with general content_type
        insert_sql = """
            INSERT INTO chat_topics (
                content_type, content_id, title, description, 
                topic_category, image_url, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            RETURNING id, content_type, content_id, title, description,
                      created_at, updated_at, message_count, last_message_at, is_active,
                      is_pinned, pinned_at, topic_category, image_url
        """
        result = await fetchrow(
            insert_sql,
            "general",
            -next_id,  # Use negative ID for general topics to avoid conflicts
            topic.title.strip(),
            topic.description.strip() if topic.description else None,
            topic.topic_category.strip() if topic.topic_category else None,
            topic.image_url.strip() if topic.image_url else None,
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create general topic")
        
        topic_dict = dict(result)
        
        return ChatTopicResponse(**topic_dict)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create general topic: {str(e)}")


@router.get("/topics/general", response_model=List[ChatTopicResponse])
async def list_general_topics(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """List all general chat topics (Turkchat)."""
    
    chat_service = get_chat_service()
    
    try:
        topics, total = await chat_service.list_topics(
            content_type="general",
            limit=limit,
            offset=offset,
        )
        
        return [ChatTopicResponse(**topic) for topic in topics]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list general topics: {str(e)}")


@router.patch("/topics/general/{topic_id}", response_model=ChatTopicResponse)
async def update_general_topic(
    topic_id: int = Path(..., description="Topic ID"),
    update: GeneralTopicUpdate = ...,
    admin: AdminUser = Depends(verify_admin_user),
):
    """Update a general chat topic."""
    
    # Check if topic exists and is general
    check_sql = """
        SELECT id, content_type FROM chat_topics
        WHERE id = $1 AND content_type = 'general' AND is_active = TRUE
    """
    check_result = await fetchrow(check_sql, topic_id)
    
    if not check_result:
        raise HTTPException(status_code=404, detail="General topic not found")
    
    # Build update SQL dynamically
    updates = []
    values = []
    param_num = 1
    
    if update.title is not None:
        if not update.title.strip():
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        updates.append(f"title = ${param_num}")
        values.append(update.title.strip())
        param_num += 1
    
    if update.description is not None:
        updates.append(f"description = ${param_num}")
        values.append(update.description.strip() if update.description else None)
        param_num += 1
    
    if update.topic_category is not None:
        updates.append(f"topic_category = ${param_num}")
        values.append(update.topic_category.strip() if update.topic_category else None)
        param_num += 1
    
    if update.image_url is not None:
        updates.append(f"image_url = ${param_num}")
        values.append(update.image_url.strip() if update.image_url else None)
        param_num += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append(f"updated_at = NOW()")
    values.append(topic_id)
    
    updates_str = ", ".join(updates)
    
    update_sql = f"""
        UPDATE chat_topics
        SET {updates_str}
        WHERE id = ${param_num}
        RETURNING id, content_type, content_id, title, description,
                  created_at, updated_at, message_count, last_message_at, is_active,
                  is_pinned, pinned_at, topic_category, image_url
    """
    
    result = await fetchrow(update_sql, *values)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update topic")
    
    topic_dict = dict(result)
    
    return ChatTopicResponse(**topic_dict)


@router.delete("/topics/general/{topic_id}")
async def delete_general_topic(
    topic_id: int = Path(..., description="Topic ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """Delete a general chat topic (soft delete by setting is_active = FALSE)."""
    
    # Check if topic exists (must be general topic)
    check_sql = """
        SELECT id, content_type FROM chat_topics
        WHERE id = $1 AND content_type = 'general' AND is_active = TRUE
    """
    check_result = await fetchrow(check_sql, topic_id)
    
    if not check_result:
        raise HTTPException(status_code=404, detail="General topic not found")
    
    # Soft delete by setting is_active = FALSE
    delete_sql = """
        UPDATE chat_topics
        SET is_active = FALSE, updated_at = NOW()
        WHERE id = $1
    """
    await execute(delete_sql, topic_id)
    
    return {"ok": True, "topic_id": topic_id}


@router.post("/topics/{topic_id}/pin")
async def pin_topic(
    topic_id: int = Path(..., description="Topic ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """Pin a chat topic to the top."""
    
    # Check if topic exists
    check_sql = "SELECT id FROM chat_topics WHERE id = $1 AND is_active = TRUE"
    check_result = await fetchrow(check_sql, topic_id)
    
    if not check_result:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # Pin topic
    pin_sql = """
        UPDATE chat_topics
        SET is_pinned = TRUE, pinned_at = NOW(), updated_at = NOW()
        WHERE id = $1
    """
    await execute(pin_sql, topic_id)
    
    return {"ok": True, "topic_id": topic_id, "pinned": True}


@router.post("/topics/{topic_id}/unpin")
async def unpin_topic(
    topic_id: int = Path(..., description="Topic ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """Unpin a chat topic."""
    
    # Check if topic exists
    check_sql = "SELECT id FROM chat_topics WHERE id = $1 AND is_active = TRUE"
    check_result = await fetchrow(check_sql, topic_id)
    
    if not check_result:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # Unpin topic
    unpin_sql = """
        UPDATE chat_topics
        SET is_pinned = FALSE, pinned_at = NULL, updated_at = NOW()
        WHERE id = $1
    """
    await execute(unpin_sql, topic_id)
    
    return {"ok": True, "topic_id": topic_id, "pinned": False}

