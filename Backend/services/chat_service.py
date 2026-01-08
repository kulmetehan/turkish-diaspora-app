# Backend/services/chat_service.py
from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from services.db_service import fetch, fetchrow, execute, fetchval
from app.core.logging import get_logger

logger = get_logger()


class ChatService:
    """
    Service for chat topic and message operations.
    """

    async def create_or_get_topic(
        self,
        content_type: str,
        content_id: int,
        title: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a chat topic for a content item, or return existing one.
        
        Args:
            content_type: Type of content ('feed', 'news', 'event', 'music')
            content_id: ID of the content item
            title: Title of the topic (usually from content item)
            description: Optional description/preview
            
        Returns:
            Dict with topic data
        """
        # Check if topic already exists
        existing_sql = """
            SELECT id, content_type, content_id, title, description,
                   created_at, updated_at, message_count, last_message_at, is_active
            FROM chat_topics
            WHERE content_type = $1 AND content_id = $2
        """
        existing = await fetchrow(existing_sql, content_type, content_id)
        
        if existing:
            return dict(existing)
        
        # Create new topic
        insert_sql = """
            INSERT INTO chat_topics (content_type, content_id, title, description, created_at, updated_at)
            VALUES ($1, $2, $3, $4, NOW(), NOW())
            RETURNING id, content_type, content_id, title, description,
                      created_at, updated_at, message_count, last_message_at, is_active
        """
        result = await fetchrow(insert_sql, content_type, content_id, title, description)
        
        if not result:
            raise RuntimeError("Failed to create chat topic")
        
        return dict(result)

    async def list_topics(
        self,
        content_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List chat topics with optional filtering.
        
        Args:
            content_type: Optional filter by content type
            limit: Max number of topics to return
            offset: Pagination offset
            
        Returns:
            Tuple of (topics list, total count)
        """
        from typing import Tuple
        
        # Build WHERE clause
        where_clause = "WHERE is_active = TRUE"
        params: List[Any] = []
        param_count = 0
        
        if content_type:
            param_count += 1
            where_clause += f" AND content_type = ${param_count}"
            params.append(content_type)
        
        # Get total count
        count_sql = f"SELECT COUNT(*) FROM chat_topics {where_clause}"
        if params:
            total = await fetchval(count_sql, *params)
        else:
            total = await fetchval(count_sql)
        
        # Get topics
        if content_type:
            param_count = 1  # Already has content_type param
        else:
            param_count = 0
        
        limit_param = param_count + 1
        offset_param = param_count + 2
        topics_sql = f"""
            SELECT id, content_type, content_id, title, description,
                   created_at, updated_at, message_count, last_message_at, is_active
            FROM chat_topics
            {where_clause}
            ORDER BY last_message_at DESC NULLS LAST, created_at DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        params.extend([limit, offset])
        
        topics = await fetch(topics_sql, *params)
        
        # Fetch image_url for each topic based on content_type and content_id
        topics_with_images = []
        for topic in topics:
            topic_dict = dict(topic)
            image_url = await self._get_content_image(
                topic_dict["content_type"],
                topic_dict["content_id"]
            )
            topic_dict["image_url"] = image_url
            topics_with_images.append(topic_dict)
        
        return topics_with_images, int(total) if total else 0

    async def get_topic(self, topic_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific chat topic by ID.
        
        Args:
            topic_id: ID of the topic
            
        Returns:
            Topic data or None if not found
        """
        sql = """
            SELECT id, content_type, content_id, title, description,
                   created_at, updated_at, message_count, last_message_at, is_active
            FROM chat_topics
            WHERE id = $1
        """
        result = await fetchrow(sql, topic_id)
        
        if not result:
            return None
        
        topic_dict = dict(result)
        # Fetch image_url
        image_url = await self._get_content_image(
            topic_dict["content_type"],
            topic_dict["content_id"]
        )
        topic_dict["image_url"] = image_url
        
        return topic_dict

    async def create_message(
        self,
        topic_id: int,
        user_id: str,
        content: str,
        parent_message_id: Optional[int] = None,
        quoted_message_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a new chat message.
        
        Args:
            topic_id: ID of the topic
            user_id: UUID of the user
            content: Message content
            parent_message_id: Optional parent message ID for replies
            quoted_message_id: Optional quoted message ID
            
        Returns:
            Dict with message data
        """
        # Validate topic exists
        topic = await self.get_topic(topic_id)
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")
        
        # Validate parent message if provided
        if parent_message_id:
            parent_sql = "SELECT id, topic_id FROM chat_messages WHERE id = $1 AND is_deleted = FALSE"
            parent = await fetchrow(parent_sql, parent_message_id)
            if not parent:
                raise ValueError(f"Parent message {parent_message_id} not found")
            if parent["topic_id"] != topic_id:
                raise ValueError("Parent message must be in the same topic")
        
        # Validate quoted message if provided
        if quoted_message_id:
            quoted_sql = "SELECT id, topic_id FROM chat_messages WHERE id = $1 AND is_deleted = FALSE"
            quoted = await fetchrow(quoted_sql, quoted_message_id)
            if not quoted:
                raise ValueError(f"Quoted message {quoted_message_id} not found")
            if quoted["topic_id"] != topic_id:
                raise ValueError("Quoted message must be in the same topic")
        
        # Insert message
        insert_sql = """
            INSERT INTO chat_messages (topic_id, user_id, content, parent_message_id, quoted_message_id, created_at, updated_at)
            VALUES ($1, $2::uuid, $3, $4, $5, NOW(), NOW())
            RETURNING id, topic_id, user_id, content, parent_message_id, quoted_message_id,
                      created_at, updated_at, is_edited, is_deleted, deleted_at
        """
        result = await fetchrow(
            insert_sql,
            topic_id,
            user_id,
            content,
            parent_message_id,
            quoted_message_id,
        )
        
        if not result:
            raise RuntimeError("Failed to create chat message")
        
        # Auto-subscribe user to topic if not already subscribed
        await self.subscribe_to_topic(topic_id, user_id)
        
        return dict(result)

    async def list_messages(
        self,
        topic_id: int,
        limit: int = 50,
        before_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List messages for a topic, ordered chronologically (oldest first).
        
        Args:
            topic_id: ID of the topic
            limit: Max number of messages to return
            before_id: Optional message ID to get messages before (for pagination)
            
        Returns:
            List of message dicts
        """
        # Validate topic exists
        topic = await self.get_topic(topic_id)
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")
        
        # Build WHERE clause
        where_clause = "WHERE m.topic_id = $1 AND m.is_deleted = FALSE"
        params: List[Any] = [topic_id]
        param_count = 1
        
        if before_id:
            param_count += 1
            where_clause += f" AND m.id < ${param_count}"
            params.append(before_id)
        
        # Get messages (oldest first for chat UI) with parent and quoted message data
        messages_sql = f"""
            SELECT 
                m.id, m.topic_id, m.user_id, m.content, m.parent_message_id, m.quoted_message_id,
                m.created_at, m.updated_at, m.is_edited, m.is_deleted, m.deleted_at,
                p.display_name as user_name, p.avatar_url as user_avatar,
                r.primary_role, r.secondary_role,
                -- Parent message data
                pm.id as parent_message_id_full,
                pm.content as parent_message_content,
                pm.created_at as parent_message_created_at,
                pp.display_name as parent_message_user_name,
                pp.avatar_url as parent_message_user_avatar,
                -- Quoted message data
                qm.id as quoted_message_id_full,
                qm.content as quoted_message_content,
                qm.created_at as quoted_message_created_at,
                qp.display_name as quoted_message_user_name,
                qp.avatar_url as quoted_message_user_avatar
            FROM chat_messages m
            LEFT JOIN user_profiles p ON m.user_id = p.id
            LEFT JOIN user_roles r ON m.user_id = r.user_id
            LEFT JOIN chat_messages pm ON m.parent_message_id = pm.id AND pm.is_deleted = FALSE
            LEFT JOIN user_profiles pp ON pm.user_id = pp.id
            LEFT JOIN chat_messages qm ON m.quoted_message_id = qm.id AND qm.is_deleted = FALSE
            LEFT JOIN user_profiles qp ON qm.user_id = qp.id
            {where_clause}
            ORDER BY m.created_at DESC
            LIMIT ${param_count + 1}
        """
        params.append(limit)
        
        messages = await fetch(messages_sql, *params)
        
        # Build message dicts with nested parent/quoted message data
        result_messages = []
        for msg in reversed(messages):
            msg_dict = dict(msg)
            
            # Build parent message object if exists
            parent_message = None
            if msg_dict.get("parent_message_id_full"):
                parent_message = {
                    "id": msg_dict["parent_message_id_full"],
                    "content": msg_dict.get("parent_message_content"),
                    "created_at": msg_dict.get("parent_message_created_at"),
                    "user": {
                        "name": msg_dict.get("parent_message_user_name"),
                        "avatar_url": msg_dict.get("parent_message_user_avatar"),
                    } if msg_dict.get("parent_message_user_name") or msg_dict.get("parent_message_user_avatar") else None,
                }
            
            # Build quoted message object if exists
            quoted_message = None
            if msg_dict.get("quoted_message_id_full"):
                quoted_message = {
                    "id": msg_dict["quoted_message_id_full"],
                    "content": msg_dict.get("quoted_message_content"),
                    "created_at": msg_dict.get("quoted_message_created_at"),
                    "user": {
                        "name": msg_dict.get("quoted_message_user_name"),
                        "avatar_url": msg_dict.get("quoted_message_user_avatar"),
                    } if msg_dict.get("quoted_message_user_name") or msg_dict.get("quoted_message_user_avatar") else None,
                }
            
            # Clean up the message dict (remove parent/quoted fields)
            clean_msg = {
                "id": msg_dict["id"],
                "topic_id": msg_dict["topic_id"],
                "user_id": msg_dict["user_id"],
                "content": msg_dict["content"],
                "parent_message_id": msg_dict.get("parent_message_id"),
                "quoted_message_id": msg_dict.get("quoted_message_id"),
                "created_at": msg_dict["created_at"],
                "updated_at": msg_dict["updated_at"],
                "is_edited": msg_dict.get("is_edited", False),
                "is_deleted": msg_dict.get("is_deleted", False),
                "deleted_at": msg_dict.get("deleted_at"),
                "user_name": msg_dict.get("user_name"),
                "user_avatar": msg_dict.get("user_avatar"),
                "primary_role": msg_dict.get("primary_role"),
                "secondary_role": msg_dict.get("secondary_role"),
            }
            
            if parent_message:
                clean_msg["parent_message"] = parent_message
            if quoted_message:
                clean_msg["quoted_message"] = quoted_message
            
            result_messages.append(clean_msg)
        
        return result_messages

    async def get_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific message by ID.
        
        Args:
            message_id: ID of the message
            
        Returns:
            Message data or None if not found
        """
        sql = """
            SELECT 
                m.id, m.topic_id, m.user_id, m.content, m.parent_message_id, m.quoted_message_id,
                m.created_at, m.updated_at, m.is_edited, m.is_deleted, m.deleted_at,
                p.display_name as user_name, p.avatar_url as user_avatar,
                r.primary_role, r.secondary_role,
                -- Parent message data
                pm.id as parent_message_id_full,
                pm.content as parent_message_content,
                pm.created_at as parent_message_created_at,
                pp.display_name as parent_message_user_name,
                pp.avatar_url as parent_message_user_avatar,
                -- Quoted message data
                qm.id as quoted_message_id_full,
                qm.content as quoted_message_content,
                qm.created_at as quoted_message_created_at,
                qp.display_name as quoted_message_user_name,
                qp.avatar_url as quoted_message_user_avatar
            FROM chat_messages m
            LEFT JOIN user_profiles p ON m.user_id = p.id
            LEFT JOIN user_roles r ON m.user_id = r.user_id
            LEFT JOIN chat_messages pm ON m.parent_message_id = pm.id AND pm.is_deleted = FALSE
            LEFT JOIN user_profiles pp ON pm.user_id = pp.id
            LEFT JOIN chat_messages qm ON m.quoted_message_id = qm.id AND qm.is_deleted = FALSE
            LEFT JOIN user_profiles qp ON qm.user_id = qp.id
            WHERE m.id = $1
        """
        result = await fetchrow(sql, message_id)
        
        if not result:
            return None
        
        msg_dict = dict(result)
        
        # Build parent message object if exists
        parent_message = None
        if msg_dict.get("parent_message_id_full"):
            parent_message = {
                "id": msg_dict["parent_message_id_full"],
                "content": msg_dict.get("parent_message_content"),
                "created_at": msg_dict.get("parent_message_created_at"),
                "user": {
                    "name": msg_dict.get("parent_message_user_name"),
                    "avatar_url": msg_dict.get("parent_message_user_avatar"),
                } if msg_dict.get("parent_message_user_name") or msg_dict.get("parent_message_user_avatar") else None,
            }
        
        # Build quoted message object if exists
        quoted_message = None
        if msg_dict.get("quoted_message_id_full"):
            quoted_message = {
                "id": msg_dict["quoted_message_id_full"],
                "content": msg_dict.get("quoted_message_content"),
                "created_at": msg_dict.get("quoted_message_created_at"),
                "user": {
                    "name": msg_dict.get("quoted_message_user_name"),
                    "avatar_url": msg_dict.get("quoted_message_user_avatar"),
                } if msg_dict.get("quoted_message_user_name") or msg_dict.get("quoted_message_user_avatar") else None,
            }
        
        # Clean up the message dict
        clean_msg = {
            "id": msg_dict["id"],
            "topic_id": msg_dict["topic_id"],
            "user_id": msg_dict["user_id"],
            "content": msg_dict["content"],
            "parent_message_id": msg_dict.get("parent_message_id"),
            "quoted_message_id": msg_dict.get("quoted_message_id"),
            "created_at": msg_dict["created_at"],
            "updated_at": msg_dict["updated_at"],
            "is_edited": msg_dict.get("is_edited", False),
            "is_deleted": msg_dict.get("is_deleted", False),
            "deleted_at": msg_dict.get("deleted_at"),
            "user_name": msg_dict.get("user_name"),
            "user_avatar": msg_dict.get("user_avatar"),
            "primary_role": msg_dict.get("primary_role"),
            "secondary_role": msg_dict.get("secondary_role"),
        }
        
        if parent_message:
            clean_msg["parent_message"] = parent_message
        if quoted_message:
            clean_msg["quoted_message"] = quoted_message
        
        return clean_msg

    async def update_message(
        self,
        message_id: int,
        user_id: str,
        content: str,
    ) -> Dict[str, Any]:
        """
        Update a message (only by the author).
        
        Args:
            message_id: ID of the message
            user_id: UUID of the user (must be author)
            content: New content
            
        Returns:
            Updated message data
        """
        # Check message exists and user is author
        check_sql = "SELECT id, user_id FROM chat_messages WHERE id = $1 AND is_deleted = FALSE"
        message = await fetchrow(check_sql, message_id)
        
        if not message:
            raise ValueError(f"Message {message_id} not found")
        
        # Ensure both are strings for comparison (UUID might be returned as UUID type)
        message_user_id = str(message["user_id"])
        user_id_str = str(user_id)
        
        if message_user_id != user_id_str:
            raise ValueError("Only the author can edit a message")
        
        # Update message
        update_sql = """
            UPDATE chat_messages
            SET content = $1, updated_at = NOW(), is_edited = TRUE
            WHERE id = $2
            RETURNING id, topic_id, user_id, content, parent_message_id, quoted_message_id,
                      created_at, updated_at, is_edited, is_deleted, deleted_at
        """
        result = await fetchrow(update_sql, content, message_id)
        
        if not result:
            raise RuntimeError("Failed to update message")
        
        return dict(result)

    async def delete_message(
        self,
        message_id: int,
        user_id: str,
    ) -> None:
        """
        Soft delete a message (only by the author).
        
        Args:
            message_id: ID of the message
            user_id: UUID of the user (must be author)
        """
        # Check message exists and user is author
        check_sql = "SELECT id, user_id FROM chat_messages WHERE id = $1 AND is_deleted = FALSE"
        message = await fetchrow(check_sql, message_id)
        
        if not message:
            raise ValueError(f"Message {message_id} not found")
        
        # Ensure both are strings for comparison (UUID might be returned as UUID type)
        message_user_id = str(message["user_id"])
        user_id_str = str(user_id)
        
        if message_user_id != user_id_str:
            raise ValueError("Only the author can delete a message")
        
        # Soft delete
        delete_sql = """
            UPDATE chat_messages
            SET is_deleted = TRUE, deleted_at = NOW(), updated_at = NOW()
            WHERE id = $1
        """
        await execute(delete_sql, message_id)

    async def toggle_reaction(
        self,
        message_id: int,
        user_id: str,
        emoji: str,
    ) -> Dict[str, Any]:
        """
        Toggle a reaction on a message (add if not exists, remove if exists).
        
        Args:
            message_id: ID of the message
            user_id: UUID of the user
            emoji: Emoji string (e.g., "👍", "❤️", "🔥")
            
        Returns:
            Dict with reaction counts for the message
        """
        # Check message exists
        message = await self.get_message(message_id)
        if not message:
            raise ValueError(f"Message {message_id} not found")
        
        # Check if reaction already exists
        check_sql = """
            SELECT emoji FROM chat_message_reactions
            WHERE message_id = $1 AND user_id = $2::uuid AND emoji = $3
        """
        existing = await fetchrow(check_sql, message_id, user_id, emoji)
        
        if existing:
            # Remove reaction
            delete_sql = """
                DELETE FROM chat_message_reactions
                WHERE message_id = $1 AND user_id = $2::uuid AND emoji = $3
            """
            await execute(delete_sql, message_id, user_id, emoji)
        else:
            # Add reaction
            insert_sql = """
                INSERT INTO chat_message_reactions (message_id, user_id, emoji, created_at)
                VALUES ($1, $2::uuid, $3, NOW())
                ON CONFLICT (message_id, user_id, emoji) DO NOTHING
            """
            await execute(insert_sql, message_id, user_id, emoji)
        
        # Get updated reaction counts
        counts_sql = """
            SELECT emoji, COUNT(*) as count
            FROM chat_message_reactions
            WHERE message_id = $1
            GROUP BY emoji
        """
        reactions = await fetch(counts_sql, message_id)
        
        # Convert to dict format
        reaction_counts: Dict[str, int] = {}
        for r in reactions:
            reaction_counts[str(r["emoji"])] = int(r["count"])
        
        return reaction_counts

    async def get_message_reactions(
        self,
        message_id: int,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get reactions for a message, including user's reactions if user_id provided.
        
        Args:
            message_id: ID of the message
            user_id: Optional UUID of the user to get their reactions
            
        Returns:
            Dict with reaction counts and user reactions
        """
        # Get reaction counts
        counts_sql = """
            SELECT emoji, COUNT(*) as count
            FROM chat_message_reactions
            WHERE message_id = $1
            GROUP BY emoji
        """
        reactions = await fetch(counts_sql, message_id)
        
        # Convert to dict format
        reaction_counts: Dict[str, int] = {}
        for r in reactions:
            reaction_counts[str(r["emoji"])] = int(r["count"])
        
        result: Dict[str, Any] = {"reactions": reaction_counts}
        
        # Get user's reactions if user_id provided
        if user_id:
            user_reactions_sql = """
                SELECT emoji FROM chat_message_reactions
                WHERE message_id = $1 AND user_id = $2::uuid
            """
            user_reactions = await fetch(user_reactions_sql, message_id, user_id)
            result["user_reactions"] = [str(r["emoji"]) for r in user_reactions]
        else:
            result["user_reactions"] = []
        
        return result

    async def subscribe_to_topic(
        self,
        topic_id: int,
        user_id: str,
        notification_enabled: bool = True,
    ) -> Dict[str, Any]:
        """
        Subscribe a user to a topic (or update subscription).
        
        Args:
            topic_id: ID of the topic
            user_id: UUID of the user
            notification_enabled: Whether to enable notifications
            
        Returns:
            Subscription data
        """
        # Check topic exists
        topic = await self.get_topic(topic_id)
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")
        
        # Insert or update subscription
        upsert_sql = """
            INSERT INTO chat_topic_subscriptions (topic_id, user_id, notification_enabled, subscribed_at)
            VALUES ($1, $2::uuid, $3, NOW())
            ON CONFLICT (topic_id, user_id)
            DO UPDATE SET
                notification_enabled = EXCLUDED.notification_enabled,
                subscribed_at = COALESCE(chat_topic_subscriptions.subscribed_at, NOW())
            RETURNING topic_id, user_id, last_read_at, last_read_message_id,
                      subscribed_at, notification_enabled
        """
        result = await fetchrow(upsert_sql, topic_id, user_id, notification_enabled)
        
        if not result:
            raise RuntimeError("Failed to subscribe to topic")
        
        return dict(result)

    async def mark_topic_as_read(
        self,
        topic_id: int,
        user_id: str,
        message_id: Optional[int] = None,
    ) -> None:
        """
        Mark a topic as read for a user.
        
        Args:
            topic_id: ID of the topic
            user_id: UUID of the user
            message_id: Optional specific message ID to mark as last read
        """
        # Get latest message ID if not provided
        if message_id is None:
            latest_sql = """
                SELECT id FROM chat_messages
                WHERE topic_id = $1 AND is_deleted = FALSE
                ORDER BY created_at DESC
                LIMIT 1
            """
            latest = await fetchrow(latest_sql, topic_id)
            if latest:
                message_id = latest["id"]
        
        # Update subscription
        update_sql = """
            INSERT INTO chat_topic_subscriptions (topic_id, user_id, last_read_at, last_read_message_id, subscribed_at)
            VALUES ($1, $2::uuid, NOW(), $3, NOW())
            ON CONFLICT (topic_id, user_id)
            DO UPDATE SET
                last_read_at = NOW(),
                last_read_message_id = EXCLUDED.last_read_message_id
        """
        await execute(update_sql, topic_id, user_id, message_id)

    async def get_topic_unread_count(
        self,
        topic_id: int,
        user_id: str,
    ) -> int:
        """
        Get unread message count for a topic.
        
        Args:
            topic_id: ID of the topic
            user_id: UUID of the user
            
        Returns:
            Number of unread messages
        """
        # Get last read message ID
        sub_sql = """
            SELECT last_read_message_id FROM chat_topic_subscriptions
            WHERE topic_id = $1 AND user_id = $2::uuid
        """
        sub = await fetchrow(sub_sql, topic_id, user_id)
        
        if not sub or not sub["last_read_message_id"]:
            # Not subscribed or never read - count all messages
            count_sql = """
                SELECT COUNT(*) FROM chat_messages
                WHERE topic_id = $1 AND is_deleted = FALSE
            """
            result = await fetchval(count_sql, topic_id)
            return int(result) if result else 0
        
        # Count messages after last read
        count_sql = """
            SELECT COUNT(*) FROM chat_messages
            WHERE topic_id = $1 AND id > $2 AND is_deleted = FALSE
        """
        result = await fetchval(count_sql, topic_id, sub["last_read_message_id"])
        return int(result) if result else 0

    async def _get_content_image(
        self,
        content_type: str,
        content_id: int,
    ) -> Optional[str]:
        """
        Get image URL for a content item based on content_type and content_id.
        
        Args:
            content_type: Type of content ('feed', 'news', 'event', 'music')
            content_id: ID of the content item
            
        Returns:
            Image URL or None if not found
        """
        try:
            if content_type == "news" or content_type == "music":
                # For news and music, query raw_ingested_news
                sql = "SELECT image_url FROM raw_ingested_news WHERE id = $1"
                result = await fetchval(sql, content_id)
                return result if result else None
            elif content_type == "event":
                # For events, query events_public view (which includes image_url from event_raw)
                sql = "SELECT image_url FROM events_public WHERE id = $1"
                result = await fetchval(sql, content_id)
                return result if result else None
            elif content_type == "feed":
                # For feed, query activity_stream for media_url
                sql = "SELECT media_url FROM activity_stream WHERE id = $1"
                result = await fetchval(sql, content_id)
                return result if result else None
            else:
                return None
        except Exception as e:
            logger.warning(
                "chat_service_get_image_error",
                content_type=content_type,
                content_id=content_id,
                error=str(e),
            )
            return None


# Singleton instance
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get or create ChatService singleton."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service

