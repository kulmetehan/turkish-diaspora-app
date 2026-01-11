# Backend/api/routers/chat.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.deps.auth import get_current_user, User
from services.chat_service import get_chat_service
from services.push_service import get_push_service

router = APIRouter(prefix="/chat", tags=["chat"])


# Request/Response Models
class ChatTopic(BaseModel):
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
    is_pinned: Optional[bool] = False
    pinned_at: Optional[datetime] = None
    topic_category: Optional[str] = None


class ChatTopicListResponse(BaseModel):
    items: List[ChatTopic]
    total: int
    limit: int
    offset: int


class ChatMessageUser(BaseModel):
    id: str  # UUID as string
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    primary_role: Optional[str] = None
    secondary_role: Optional[str] = None


class ChatMessage(BaseModel):
    id: int
    topic_id: int
    user_id: str  # UUID as string
    content: str
    parent_message_id: Optional[int] = None
    quoted_message_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_edited: bool
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    user: Optional[ChatMessageUser] = None
    reactions: Optional[dict] = None  # Reaction counts: {"👍": 5, "❤️": 3, ...}
    user_reactions: Optional[List[str]] = None  # Current user's reactions
    parent_message: Optional["ChatMessage"] = None  # Nested parent message
    quoted_message: Optional["ChatMessage"] = None  # Nested quoted message


class ChatMessageListResponse(BaseModel):
    items: List[ChatMessage]
    has_more: bool


class CreateTopicRequest(BaseModel):
    content_type: str  # 'feed', 'news', 'event', 'music'
    content_id: int
    title: str
    description: Optional[str] = None


class CreateMessageRequest(BaseModel):
    content: str
    parent_message_id: Optional[int] = None
    quoted_message_id: Optional[int] = None


class EditMessageRequest(BaseModel):
    content: str


class ReactionRequest(BaseModel):
    emoji: str  # e.g., "👍", "❤️", "🔥"


class SubscriptionRequest(BaseModel):
    notification_enabled: bool = True


# Topic Endpoints
@router.post("/topics", response_model=ChatTopic)
async def create_topic(
    request: CreateTopicRequest,
    user: User = Depends(get_current_user),
):
    """Create a chat topic for a content item."""
    chat_service = get_chat_service()
    
    # Validate content_type
    valid_types = ["feed", "news", "event", "music"]
    if request.content_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"content_type must be one of: {', '.join(valid_types)}"
        )
    
    try:
        topic = await chat_service.create_or_get_topic(
            content_type=request.content_type,
            content_id=request.content_id,
            title=request.title,
            description=request.description,
        )
        
        # Auto-subscribe user to topic
        await chat_service.subscribe_to_topic(topic["id"], str(user.user_id))
        
        return ChatTopic(**topic)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create topic: {str(e)}")


@router.get("/topics", response_model=ChatTopicListResponse)
async def list_topics(
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
):
    """List chat topics with optional filtering."""
    chat_service = get_chat_service()
    
    # Validate content_type if provided (allow 'general' for Turkchat)
    if content_type:
        valid_types = ["feed", "news", "event", "music", "general"]
        if content_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"content_type must be one of: {', '.join(valid_types)}"
            )
    
    try:
        topics, total = await chat_service.list_topics(
            content_type=content_type,
            limit=limit,
            offset=offset,
        )
        
        return ChatTopicListResponse(
            items=[ChatTopic(**t) for t in topics],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        from app.core.logging import get_logger
        logger = get_logger()
        logger.error(
            "Failed to list chat topics",
            extra={
                "content_type": content_type,
                "limit": limit,
                "offset": offset,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to list topics: {str(e)}")


@router.get("/topics/by-content", response_model=ChatTopic)
async def get_topic_by_content(
    content_type: str = Query(..., description="Content type (feed, news, event, music)"),
    content_id: int = Query(..., description="Content ID"),
    user: User = Depends(get_current_user),
):
    """Get a chat topic by content_type and content_id (without creating). Returns 404 if not found."""
    
    # Validate content_type
    valid_types = ["feed", "news", "event", "music"]
    if content_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"content_type must be one of: {', '.join(valid_types)}"
        )
    
    # Validate content_id
    if content_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="content_id must be a positive integer"
        )
    
    try:
        # Get existing topic if it exists - use chat_service instead of direct query
        chat_service = get_chat_service()
        # For get_topic_by_content, we need to find by content_type + content_id
        # Use list_topics and filter, or better: extend chat_service to support this
        from services.db_service import fetchrow
        existing_sql = """
            SELECT id FROM chat_topics
            WHERE content_type = $1 AND content_id = $2 AND is_active = TRUE
        """
        topic_row = await fetchrow(existing_sql, content_type, content_id)
        
        if not topic_row:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        topic_id = topic_row["id"]
        topic = await chat_service.get_topic(topic_id)
        
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Convert to dict and ensure all fields are present
        topic_dict = dict(topic)
        
        # Ensure message_count is an int (might come as Decimal from DB)
        if 'message_count' in topic_dict:
            topic_dict['message_count'] = int(topic_dict['message_count'])
        
        # Ensure new fields have default values
        topic_dict['is_pinned'] = topic_dict.get('is_pinned', False)
        topic_dict['pinned_at'] = topic_dict.get('pinned_at')
        topic_dict['topic_category'] = topic_dict.get('topic_category')
        
        result = ChatTopic(**topic_dict)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        from app.core.logging import get_logger
        logger = get_logger()
        logger.error("Failed to get chat topic by content", extra={
            "content_type": content_type,
            "content_id": content_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail=f"Failed to get topic: {str(e)}")


@router.get("/topics/{topic_id}", response_model=ChatTopic)
async def get_topic(
    topic_id: int = Path(..., description="Topic ID"),
    user: User = Depends(get_current_user),
):
    """Get a specific chat topic."""
    chat_service = get_chat_service()
    
    topic = await chat_service.get_topic(topic_id)
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return ChatTopic(**topic)


@router.get("/topics/{topic_id}/messages", response_model=ChatMessageListResponse)
async def get_messages(
    topic_id: int = Path(..., description="Topic ID"),
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = Query(None, description="Get messages before this ID"),
    user: User = Depends(get_current_user),
):
    """Get messages for a topic."""
    chat_service = get_chat_service()
    
    try:
        messages = await chat_service.list_messages(
            topic_id=topic_id,
            limit=limit + 1,  # Fetch one extra to check if there are more
            before_id=before_id,
        )
        
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]
        
        # Get reactions for each message
        result_messages = []
        for msg in messages:
            reactions_data = await chat_service.get_message_reactions(
                message_id=msg["id"],
                user_id=str(user.user_id),
            )
            
            # Build user object
            user_obj = None
            if msg.get("user_name") or msg.get("user_id"):
                user_obj = ChatMessageUser(
                    id=str(msg["user_id"]),
                    name=msg.get("user_name"),
                    avatar_url=msg.get("user_avatar"),
                    primary_role=msg.get("primary_role"),
                    secondary_role=msg.get("secondary_role"),
                )
            
            # Build parent message object if exists
            parent_message_obj = None
            if msg.get("parent_message"):
                parent_msg_data = msg["parent_message"]
                parent_user_obj = None
                if parent_msg_data.get("user"):
                    parent_user_obj = ChatMessageUser(
                        id="",  # Parent message user ID not needed for preview
                        name=parent_msg_data["user"].get("name"),
                        avatar_url=parent_msg_data["user"].get("avatar_url"),
                    )
                parent_message_obj = ChatMessage(
                    id=parent_msg_data["id"],
                    topic_id=msg["topic_id"],  # Same topic
                    user_id="",  # Not needed for preview
                    content=parent_msg_data["content"],
                    created_at=parent_msg_data["created_at"],
                    updated_at=parent_msg_data["created_at"],
                    is_edited=False,
                    is_deleted=False,
                    user=parent_user_obj,
                )
            
            # Build quoted message object if exists
            quoted_message_obj = None
            if msg.get("quoted_message"):
                quoted_msg_data = msg["quoted_message"]
                quoted_user_obj = None
                if quoted_msg_data.get("user"):
                    quoted_user_obj = ChatMessageUser(
                        id="",  # Quoted message user ID not needed for preview
                        name=quoted_msg_data["user"].get("name"),
                        avatar_url=quoted_msg_data["user"].get("avatar_url"),
                    )
                quoted_message_obj = ChatMessage(
                    id=quoted_msg_data["id"],
                    topic_id=msg["topic_id"],  # Same topic
                    user_id="",  # Not needed for preview
                    content=quoted_msg_data["content"],
                    created_at=quoted_msg_data["created_at"],
                    updated_at=quoted_msg_data["created_at"],
                    is_edited=False,
                    is_deleted=False,
                    user=quoted_user_obj,
                )
            
            result_messages.append(
                ChatMessage(
                    id=msg["id"],
                    topic_id=msg["topic_id"],
                    user_id=str(msg["user_id"]),
                    content=msg["content"],
                    parent_message_id=msg.get("parent_message_id"),
                    quoted_message_id=msg.get("quoted_message_id"),
                    created_at=msg["created_at"],
                    updated_at=msg["updated_at"],
                    is_edited=msg.get("is_edited", False),
                    is_deleted=msg.get("is_deleted", False),
                    deleted_at=msg.get("deleted_at"),
                    user=user_obj,
                    reactions=reactions_data.get("reactions"),
                    user_reactions=reactions_data.get("user_reactions"),
                    parent_message=parent_message_obj,
                    quoted_message=quoted_message_obj,
                )
            )
        
        return ChatMessageListResponse(items=result_messages, has_more=has_more)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")


@router.get("/messages/{message_id}", response_model=ChatMessage)
async def get_message(
    message_id: int = Path(..., description="Message ID"),
    user: User = Depends(get_current_user),
):
    """Get a specific message by ID."""
    chat_service = get_chat_service()
    
    try:
        msg = await chat_service.get_message(message_id)
        
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Get reactions for the message
        reactions_data = await chat_service.get_message_reactions(
            message_id=message_id,
            user_id=str(user.user_id),
        )
        
        # Build user object
        user_obj = None
        if msg.get("user_name") or msg.get("user_id"):
            user_obj = ChatMessageUser(
                id=str(msg["user_id"]),
                name=msg.get("user_name"),
                avatar_url=msg.get("user_avatar"),
                primary_role=msg.get("primary_role"),
                secondary_role=msg.get("secondary_role"),
            )
        
        # Build parent message object if exists
        parent_message_obj = None
        if msg.get("parent_message"):
            parent_msg_data = msg["parent_message"]
            parent_user_obj = None
            if parent_msg_data.get("user"):
                parent_user_obj = ChatMessageUser(
                    id="",  # Parent message user ID not needed for preview
                    name=parent_msg_data["user"].get("name"),
                    avatar_url=parent_msg_data["user"].get("avatar_url"),
                )
            parent_message_obj = ChatMessage(
                id=parent_msg_data["id"],
                topic_id=msg["topic_id"],  # Same topic
                user_id="",  # Not needed for preview
                content=parent_msg_data["content"],
                created_at=parent_msg_data["created_at"],
                updated_at=parent_msg_data["created_at"],
                is_edited=False,
                is_deleted=False,
                user=parent_user_obj,
            )
        
        # Build quoted message object if exists
        quoted_message_obj = None
        if msg.get("quoted_message"):
            quoted_msg_data = msg["quoted_message"]
            quoted_user_obj = None
            if quoted_msg_data.get("user"):
                quoted_user_obj = ChatMessageUser(
                    id="",  # Quoted message user ID not needed for preview
                    name=quoted_msg_data["user"].get("name"),
                    avatar_url=quoted_msg_data["user"].get("avatar_url"),
                )
            quoted_message_obj = ChatMessage(
                id=quoted_msg_data["id"],
                topic_id=msg["topic_id"],  # Same topic
                user_id="",  # Not needed for preview
                content=quoted_msg_data["content"],
                created_at=quoted_msg_data["created_at"],
                updated_at=quoted_msg_data["created_at"],
                is_edited=False,
                is_deleted=False,
                user=quoted_user_obj,
            )
        
        return ChatMessage(
            id=msg["id"],
            topic_id=msg["topic_id"],
            user_id=str(msg["user_id"]),
            content=msg["content"],
            parent_message_id=msg.get("parent_message_id"),
            quoted_message_id=msg.get("quoted_message_id"),
            created_at=msg["created_at"],
            updated_at=msg["updated_at"],
            is_edited=msg.get("is_edited", False),
            is_deleted=msg.get("is_deleted", False),
            deleted_at=msg.get("deleted_at"),
            user=user_obj,
            reactions=reactions_data.get("reactions"),
            user_reactions=reactions_data.get("user_reactions"),
            parent_message=parent_message_obj,
            quoted_message=quoted_message_obj,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get message: {str(e)}")


@router.post("/topics/{topic_id}/messages", response_model=ChatMessage)
async def create_message(
    topic_id: int = Path(..., description="Topic ID"),
    request: CreateMessageRequest = ...,
    user: User = Depends(get_current_user),
):
    """Create a new message in a topic."""
    chat_service = get_chat_service()
    push_service = get_push_service()
    
    # Validate content
    if not request.content or not request.content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty")
    
    try:
        message = await chat_service.create_message(
            topic_id=topic_id,
            user_id=str(user.user_id),
            content=request.content.strip(),
            parent_message_id=request.parent_message_id,
            quoted_message_id=request.quoted_message_id,
        )
        
        # Get topic for notification
        topic = await chat_service.get_topic(topic_id)
        if topic:
            # Get all subscribers except sender
            subscribers_sql = """
                SELECT DISTINCT user_id FROM chat_topic_subscriptions
                WHERE topic_id = $1 AND user_id != $2::uuid AND notification_enabled = TRUE
            """
            from services.db_service import fetch
            subscribers = await fetch(subscribers_sql, topic_id, str(user.user_id))
            
            # Send push notifications to subscribers
            # For chat messages, use "Turkbot" as title
            for sub in subscribers:
                await push_service.send_notification(
                    user_id=str(sub["user_id"]),
                    notification_type="chat_message",
                    title="Turkbot",
                    body="Je hebt een nieuw bericht ontvangen.",
                    data={
                        "type": "chat_message",
                        "topic_id": topic_id,
                        "message_id": message["id"],
                        "topic_title": topic["title"],
                        "url": f"/chat/topic/{topic_id}",
                    },
                )
        
        # Get full message with user data and reactions
        full_message = await chat_service.get_message(message["id"])
        if not full_message:
            raise HTTPException(status_code=500, detail="Failed to retrieve created message")
        
        reactions_data = await chat_service.get_message_reactions(
            message_id=message["id"],
            user_id=str(user.user_id),
        )
        
        # Build user object
        user_obj = None
        if full_message.get("user_name") or full_message.get("user_id"):
            user_obj = ChatMessageUser(
                id=str(full_message["user_id"]),
                name=full_message.get("user_name"),
                avatar_url=full_message.get("user_avatar"),
                primary_role=full_message.get("primary_role"),
                secondary_role=full_message.get("secondary_role"),
            )
        
        return ChatMessage(
            id=full_message["id"],
            topic_id=full_message["topic_id"],
            user_id=str(full_message["user_id"]),
            content=full_message["content"],
            parent_message_id=full_message.get("parent_message_id"),
            quoted_message_id=full_message.get("quoted_message_id"),
            created_at=full_message["created_at"],
            updated_at=full_message["updated_at"],
            is_edited=full_message.get("is_edited", False),
            is_deleted=full_message.get("is_deleted", False),
            deleted_at=full_message.get("deleted_at"),
            user=user_obj,
            reactions=reactions_data.get("reactions"),
            user_reactions=reactions_data.get("user_reactions"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create message: {str(e)}")


@router.post("/messages/{message_id}/reply", response_model=ChatMessage)
async def reply_to_message(
    message_id: int = Path(..., description="Message ID to reply to"),
    request: CreateMessageRequest = ...,
    user: User = Depends(get_current_user),
):
    """Reply to a specific message."""
    chat_service = get_chat_service()
    
    # Get parent message to get topic_id
    parent_message = await chat_service.get_message(message_id)
    if not parent_message:
        raise HTTPException(status_code=404, detail="Parent message not found")
    
    try:
        message = await chat_service.create_message(
            topic_id=parent_message["topic_id"],
            user_id=str(user.user_id),
            content=request.content.strip(),
            parent_message_id=message_id,
            quoted_message_id=request.quoted_message_id,
        )
        
        # Get full message with user data and reactions
        full_message = await chat_service.get_message(message["id"])
        if not full_message:
            raise HTTPException(status_code=500, detail="Failed to retrieve created message")
        
        reactions_data = await chat_service.get_message_reactions(
            message_id=message["id"],
            user_id=str(user.user_id),
        )
        
        # Build user object
        user_obj = None
        if full_message.get("user_name") or full_message.get("user_id"):
            user_obj = ChatMessageUser(
                id=str(full_message["user_id"]),
                name=full_message.get("user_name"),
                avatar_url=full_message.get("user_avatar"),
                primary_role=full_message.get("primary_role"),
                secondary_role=full_message.get("secondary_role"),
            )
        
        return ChatMessage(
            id=full_message["id"],
            topic_id=full_message["topic_id"],
            user_id=str(full_message["user_id"]),
            content=full_message["content"],
            parent_message_id=full_message.get("parent_message_id"),
            quoted_message_id=full_message.get("quoted_message_id"),
            created_at=full_message["created_at"],
            updated_at=full_message["updated_at"],
            is_edited=full_message.get("is_edited", False),
            is_deleted=full_message.get("is_deleted", False),
            deleted_at=full_message.get("deleted_at"),
            user=user_obj,
            reactions=reactions_data.get("reactions"),
            user_reactions=reactions_data.get("user_reactions"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reply to message: {str(e)}")


@router.post("/messages/{message_id}/quote", response_model=ChatMessage)
async def quote_message(
    message_id: int = Path(..., description="Message ID to quote"),
    request: CreateMessageRequest = ...,
    user: User = Depends(get_current_user),
):
    """Quote a message in a new message."""
    chat_service = get_chat_service()
    
    # Get quoted message to get topic_id
    quoted_message = await chat_service.get_message(message_id)
    if not quoted_message:
        raise HTTPException(status_code=404, detail="Quoted message not found")
    
    try:
        message = await chat_service.create_message(
            topic_id=quoted_message["topic_id"],
            user_id=str(user.user_id),
            content=request.content.strip(),
            parent_message_id=request.parent_message_id,
            quoted_message_id=message_id,
        )
        
        # Get full message with user data and reactions
        full_message = await chat_service.get_message(message["id"])
        if not full_message:
            raise HTTPException(status_code=500, detail="Failed to retrieve created message")
        
        reactions_data = await chat_service.get_message_reactions(
            message_id=message["id"],
            user_id=str(user.user_id),
        )
        
        # Build user object
        user_obj = None
        if full_message.get("user_name") or full_message.get("user_id"):
            user_obj = ChatMessageUser(
                id=str(full_message["user_id"]),
                name=full_message.get("user_name"),
                avatar_url=full_message.get("user_avatar"),
                primary_role=full_message.get("primary_role"),
                secondary_role=full_message.get("secondary_role"),
            )
        
        return ChatMessage(
            id=full_message["id"],
            topic_id=full_message["topic_id"],
            user_id=str(full_message["user_id"]),
            content=full_message["content"],
            parent_message_id=full_message.get("parent_message_id"),
            quoted_message_id=full_message.get("quoted_message_id"),
            created_at=full_message["created_at"],
            updated_at=full_message["updated_at"],
            is_edited=full_message.get("is_edited", False),
            is_deleted=full_message.get("is_deleted", False),
            deleted_at=full_message.get("deleted_at"),
            user=user_obj,
            reactions=reactions_data.get("reactions"),
            user_reactions=reactions_data.get("user_reactions"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to quote message: {str(e)}")


@router.put("/messages/{message_id}", response_model=ChatMessage)
async def edit_message(
    message_id: int = Path(..., description="Message ID"),
    request: EditMessageRequest = ...,
    user: User = Depends(get_current_user),
):
    """Edit a message (only by the author)."""
    chat_service = get_chat_service()
    
    if not request.content or not request.content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty")
    
    try:
        message = await chat_service.update_message(
            message_id=message_id,
            user_id=str(user.user_id),
            content=request.content.strip(),
        )
        
        # Get full message with user data and reactions
        full_message = await chat_service.get_message(message["id"])
        if not full_message:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated message")
        
        reactions_data = await chat_service.get_message_reactions(
            message_id=message["id"],
            user_id=str(user.user_id),
        )
        
        # Build user object
        user_obj = None
        if full_message.get("user_name") or full_message.get("user_id"):
            user_obj = ChatMessageUser(
                id=str(full_message["user_id"]),
                name=full_message.get("user_name"),
                avatar_url=full_message.get("user_avatar"),
                primary_role=full_message.get("primary_role"),
                secondary_role=full_message.get("secondary_role"),
            )
        
        return ChatMessage(
            id=full_message["id"],
            topic_id=full_message["topic_id"],
            user_id=str(full_message["user_id"]),
            content=full_message["content"],
            parent_message_id=full_message.get("parent_message_id"),
            quoted_message_id=full_message.get("quoted_message_id"),
            created_at=full_message["created_at"],
            updated_at=full_message["updated_at"],
            is_edited=full_message.get("is_edited", False),
            is_deleted=full_message.get("is_deleted", False),
            deleted_at=full_message.get("deleted_at"),
            user=user_obj,
            reactions=reactions_data.get("reactions"),
            user_reactions=reactions_data.get("user_reactions"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to edit message: {str(e)}")


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int = Path(..., description="Message ID"),
    user: User = Depends(get_current_user),
):
    """Delete a message (only by the author, soft delete)."""
    chat_service = get_chat_service()
    
    try:
        await chat_service.delete_message(
            message_id=message_id,
            user_id=str(user.user_id),
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete message: {str(e)}")


@router.post("/messages/{message_id}/reactions")
async def toggle_reaction(
    message_id: int = Path(..., description="Message ID"),
    request: ReactionRequest = ...,
    user: User = Depends(get_current_user),
):
    """Toggle a reaction on a message."""
    chat_service = get_chat_service()
    
    if not request.emoji or not request.emoji.strip():
        raise HTTPException(status_code=400, detail="Emoji cannot be empty")
    
    try:
        reactions = await chat_service.toggle_reaction(
            message_id=message_id,
            user_id=str(user.user_id),
            emoji=request.emoji.strip(),
        )
        return {"reactions": reactions}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle reaction: {str(e)}")


@router.post("/topics/{topic_id}/subscribe")
async def subscribe_to_topic(
    topic_id: int = Path(..., description="Topic ID"),
    request: SubscriptionRequest = ...,
    user: User = Depends(get_current_user),
):
    """Subscribe to a topic (for notifications)."""
    chat_service = get_chat_service()
    
    try:
        subscription = await chat_service.subscribe_to_topic(
            topic_id=topic_id,
            user_id=str(user.user_id),
            notification_enabled=request.notification_enabled,
        )
        return {"success": True, "subscription": subscription}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to subscribe: {str(e)}")


@router.post("/topics/{topic_id}/mark-read")
async def mark_topic_as_read(
    topic_id: int = Path(..., description="Topic ID"),
    message_id: Optional[int] = Query(None, description="Optional message ID to mark as last read"),
    user: User = Depends(get_current_user),
):
    """Mark a topic as read."""
    chat_service = get_chat_service()
    
    try:
        await chat_service.mark_topic_as_read(
            topic_id=topic_id,
            user_id=str(user.user_id),
            message_id=message_id,
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark as read: {str(e)}")


@router.get("/topics/{topic_id}/unread-count")
async def get_unread_count(
    topic_id: int = Path(..., description="Topic ID"),
    user: User = Depends(get_current_user),
):
    """Get unread message count for a topic."""
    chat_service = get_chat_service()
    
    try:
        count = await chat_service.get_topic_unread_count(
            topic_id=topic_id,
            user_id=str(user.user_id),
        )
        return {"unread_count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get unread count: {str(e)}")


class ContentItemPreview(BaseModel):
    """Simplified content item data for chat preview."""
    id: int
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    content_type: str  # 'news', 'event', 'feed', 'music'
    activity_type: Optional[str] = None  # For feed items: 'poll', 'poll_response', 'check_in', etc.
    poll_id: Optional[int] = None  # For poll activities
    location_id: Optional[int] = None  # For check_in activities


@router.get("/topics/{topic_id}/content-item", response_model=ContentItemPreview)
async def get_content_item_for_preview(
    topic_id: int = Path(..., description="Topic ID"),
    user: User = Depends(get_current_user),
):
    """Get content item data for a chat topic preview."""
    from app.core.logging import get_logger
    logger = get_logger()
    
    chat_service = get_chat_service()
    
    # Get topic to find content_type and content_id
    topic = await chat_service.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    content_type = topic.get("content_type")
    content_id = topic.get("content_id")
    
    logger.debug(
        "content_item_preview_request",
        topic_id=topic_id,
        content_type=content_type,
        content_id=content_id,
    )
    
    # Don't fetch content for general topics
    if content_type == "general":
        raise HTTPException(status_code=400, detail="General topics don't have content items")
    
    try:
        from services.db_service import fetchrow
        
        if content_type == "news" or content_type == "music":
            # Fetch news item
            # Use summary or first 280 chars of content for description
            # For music, we might need to check if content_id matches a news item
            # Music items are stored in raw_ingested_news but might have different IDs
            news_sql = """
                SELECT id, title, 
                       COALESCE(summary, LEFT(content, 280)) as description,
                       image_url, link as url,
                       source_key
                FROM raw_ingested_news
                WHERE id = $1
            """
            news_row = await fetchrow(news_sql, content_id)
            if not news_row:
                # Fallback: Use topic data (especially for music items that aren't stored in raw_ingested_news)
                # Music items have derived IDs from hash and may not exist in database
                if content_type == "music":
                    # For music, use topic title/description/image_url
                    # URL retrieval priority: topic.url field → description parsing → news feed API
                    import re
                    description = topic.get("description") or ""
                    
                    # First, try to get URL from topic.url field (most reliable)
                    url = topic.get("url")
                    
                    # If not in topic.url, try to extract URL from description
                    if not url and description:
                        url_match = re.search(r'https?://[^\s]+', description)
                        if url_match:
                            url = url_match.group(0).rstrip('.,;!?)')
                    
                    # If URL still not found, try to find the track in news feed by derived_id
                    # This is a fallback since music tracks might not be in raw_ingested_news
                    if not url:
                        try:
                            # Try to get from news API by content_id (derived_id)
                            # Note: This might not work if the track is not in the current feed
                            # but it's worth trying
                            from services.news_service import list_news_by_feed, FeedType
                            # Search in both NL and TR music feeds
                            for country in ["nl", "tr"]:
                                try:
                                    feed_type = FeedType.NL if country == "nl" else FeedType.TR
                                    items, _ = await list_news_by_feed(
                                        feed_type,
                                        limit=100,
                                        offset=0,
                                        categories=None,
                                    )
                                    # Find matching item by id
                                    matching_item = next((item for item in items if item.id == content_id), None)
                                    if matching_item and matching_item.url:
                                        url = matching_item.url
                                        break
                                except Exception:
                                    continue
                        except Exception:
                            pass  # If fetching fails, continue without URL
                    
                    if not url:
                        logger.debug(
                            "music_url_not_found",
                            content_id=content_id,
                            topic_has_url=bool(topic.get("url")),
                            description_has_url=bool(re.search(r'https?://[^\s]+', description or "")),
                        )
                    
                    return ContentItemPreview(
                        id=content_id,  # Use the derived_id
                        title=topic.get("title") or "",
                        description=description,
                        image_url=topic.get("image_url"),
                        url=url,
                        content_type="music",
                    )
                else:
                    # For news items, this should not happen, but handle gracefully
                    raise HTTPException(status_code=404, detail="News item not found")
            
            return ContentItemPreview(
                id=news_row["id"],
                title=news_row.get("title") or "",
                description=news_row.get("description"),
                image_url=news_row.get("image_url"),
                url=news_row.get("url"),
                content_type=content_type,
            )
        
        elif content_type == "event":
            # Fetch event from events_public view
            event_sql = """
                SELECT id, title, summary_ai as description, image_url, url
                FROM events_public
                WHERE id = $1
            """
            event_row = await fetchrow(event_sql, content_id)
            if not event_row:
                raise HTTPException(status_code=404, detail="Event not found")
            
            return ContentItemPreview(
                id=event_row["id"],
                title=event_row.get("title") or "",
                description=event_row.get("description"),
                image_url=event_row.get("image_url"),
                url=event_row.get("url"),
                content_type="event",
            )
        
        elif content_type == "feed":
            # CRITICAL FIX: Check if content_id is a poll_id FIRST to avoid ID collision
            # Poll chat topics use poll_id as content_id, but activity_stream.id might 
            # coincidentally match (e.g., check_in with same ID as poll_id)
            # So we check polls table first, then fall back to activity_stream lookup
            feed_row = None
            
            # First, check if content_id is a poll_id (highest priority for feed items)
            # This prevents ID collision where poll_id matches an activity_stream.id
            poll_check_sql = """
                SELECT id, title, question, targeting_city_key
                FROM polls
                WHERE id = $1
            """
            poll_row = await fetchrow(poll_check_sql, content_id)
            
            if poll_row:
                logger.debug(
                    "poll_detected_for_feed_content",
                    poll_id=poll_row["id"],
                    content_id=content_id,
                )
                # This is a poll - return poll preview data directly
                # NEVER use activity_stream.id lookup for polls to avoid ID collision
                # with check_ins or other activities that might have the same ID
                return ContentItemPreview(
                    id=content_id,  # Use poll_id as id
                    title=poll_row.get("title") or "Poll",
                    description=poll_row.get("question"),
                    image_url=None,  # Polls don't have images
                    url=None,  # Polls don't have external URLs
                    content_type="feed",
                    activity_type="poll",
                    poll_id=poll_row["id"],
                    location_id=None,  # Polls NEVER have location_id - critical for avoiding location links
                )
            
            # If not a poll, proceed with normal activity_stream.id lookup
            feed_sql = """
                SELECT 
                    ast.id, 
                    ast.activity_type,
                    ast.location_id,
                    ast.payload,
                    l.name as location_name,
                    COALESCE(
                        ast.payload->>'title',
                        ast.payload->>'content',
                        CASE 
                            WHEN ast.activity_type = 'check_in' AND l.name IS NOT NULL THEN l.name
                            ELSE 'Activity'
                        END
                    ) as title,
                    ast.payload->>'content' as description,
                    ast.media_url as image_url
                FROM activity_stream ast
                LEFT JOIN locations l ON ast.location_id = l.id
                WHERE ast.id = $1
            """
            feed_row = await fetchrow(feed_sql, content_id)
            
            if not feed_row:
                logger.debug(
                    "activity_stream_not_found",
                    content_id=content_id,
                    content_type=content_type,
                    checking_activity_stream=True,
                )
                raise HTTPException(status_code=404, detail="Feed item not found")
            
            activity_type = feed_row.get("activity_type")
            payload = feed_row.get("payload") or {}
            location_name = feed_row.get("location_name")
            
            # Extract poll_id from payload if present (for poll_response activities)
            poll_id = None
            if isinstance(payload, dict):
                poll_id = payload.get("poll_id")
                if poll_id:
                    try:
                        poll_id = int(poll_id)
                    except (ValueError, TypeError):
                        poll_id = None
            
            # For poll_response activities, try to get poll title from polls table
            title = feed_row.get("title") or "Activity"
            if activity_type == "poll_response" and poll_id:
                try:
                    poll_sql = """
                        SELECT title, question
                        FROM polls
                        WHERE id = $1
                    """
                    poll_data_row = await fetchrow(poll_sql, poll_id)
                    if poll_data_row and poll_data_row.get("title"):
                        title = poll_data_row.get("title")
                        # Use poll question as description if available
                        if poll_data_row.get("question") and not feed_row.get("description"):
                            feed_row = dict(feed_row)
                            feed_row["description"] = poll_data_row.get("question")
                except Exception:
                    pass  # Fallback to default title if poll not found
            
            # For check-ins, use location name as title if available
            if activity_type == "check_in" and location_name:
                title = location_name
            
            # Extract and convert location_id
            # IMPORTANT: For polls and poll_responses, don't use location_id even if it exists
            # Polls should not link to locations
            location_id = None
            if activity_type not in ("poll", "poll_response"):
                location_id = feed_row.get("location_id")
                try:
                    location_id = int(location_id) if location_id else None
                except (ValueError, TypeError):
                    location_id = None
            
            return ContentItemPreview(
                id=feed_row["id"],
                title=title,
                description=feed_row.get("description"),
                image_url=feed_row.get("image_url"),
                url=None,  # Feed items don't have external URLs
                content_type="feed",
                activity_type=activity_type,
                poll_id=poll_id,
                location_id=location_id,
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported content_type: {content_type}")
    
    except HTTPException:
        raise
    except Exception as e:
        from app.core.logging import get_logger
        logger = get_logger()
        logger.error("Failed to get content item for preview", extra={
            "topic_id": topic_id,
            "content_type": content_type,
            "content_id": content_id,
            "error": str(e),
            "error_type": type(e).__name__,
        })
        raise HTTPException(status_code=500, detail=f"Failed to get content item: {str(e)}")

