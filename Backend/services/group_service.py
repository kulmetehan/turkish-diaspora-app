# Backend/services/group_service.py
from __future__ import annotations

from typing import Dict, Any, List, Optional
from uuid import UUID

from services.db_service import fetch, execute, fetchrow
from app.core.logging import get_logger

logger = get_logger()


class GroupService:
    """
    Service for user groups management.
    """
    
    async def create_group(
        self,
        name: str,
        description: Optional[str],
        created_by: UUID,
        is_public: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new user group.
        
        Args:
            name: Group name
            description: Group description
            created_by: User ID of creator
            is_public: Whether group is public
            
        Returns:
            Dict with group data
        """
        sql = """
            INSERT INTO user_groups (name, description, created_by, is_public)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, description, created_by, is_public, member_count, created_at, updated_at
        """
        
        result = await fetch(sql, name, description, created_by, is_public)
        
        if not result:
            raise ValueError("Failed to create group")
        
        # Creator is automatically added as owner by trigger
        return dict(result[0])
    
    async def get_group(self, group_id: int) -> Optional[Dict[str, Any]]:
        """
        Get group details.
        
        Args:
            group_id: Group ID
            
        Returns:
            Dict with group data or None
        """
        sql = """
            SELECT id, name, description, created_by, is_public, member_count, created_at, updated_at
            FROM user_groups
            WHERE id = $1
        """
        
        result = await fetchrow(sql, group_id)
        return dict(result) if result else None
    
    async def list_groups(
        self,
        search: Optional[str] = None,
        is_public: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List groups with optional filters.
        
        Args:
            search: Search term for name/description
            is_public: Filter by public/private
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of group dicts
        """
        conditions = []
        params = []
        param_num = 1
        
        if search:
            conditions.append(f"(name ILIKE ${param_num} OR description ILIKE ${param_num})")
            params.append(f"%{search}%")
            param_num += 1
        
        if is_public is not None:
            conditions.append(f"is_public = ${param_num}")
            params.append(is_public)
            param_num += 1
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        sql = f"""
            SELECT id, name, description, created_by, is_public, member_count, created_at, updated_at
            FROM user_groups
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_num} OFFSET ${param_num + 1}
        """
        params.extend([limit, offset])
        
        result = await fetch(sql, *params)
        return [dict(row) for row in result]
    
    async def join_group(
        self,
        group_id: int,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Join a group.
        
        Args:
            group_id: Group ID
            user_id: User ID
            
        Returns:
            Dict with membership data
        """
        # Check if already a member
        check_sql = """
            SELECT id FROM user_group_members
            WHERE group_id = $1 AND user_id = $2
        """
        existing = await fetchrow(check_sql, group_id, user_id)
        
        if existing:
            raise ValueError("User is already a member of this group")
        
        # Add member
        sql = """
            INSERT INTO user_group_members (group_id, user_id, role)
            VALUES ($1, $2, 'member')
            RETURNING id, group_id, user_id, role, joined_at
        """
        
        result = await fetch(sql, group_id, user_id)
        
        if not result:
            raise ValueError("Failed to join group")
        
        logger.info(
            "user_joined_group",
            group_id=group_id,
            user_id=str(user_id),
        )
        
        return dict(result[0])
    
    async def leave_group(
        self,
        group_id: int,
        user_id: UUID,
    ) -> None:
        """
        Leave a group.
        
        Args:
            group_id: Group ID
            user_id: User ID
        """
        # Check if user is owner
        check_sql = """
            SELECT role FROM user_group_members
            WHERE group_id = $1 AND user_id = $2
        """
        member = await fetchrow(check_sql, group_id, user_id)
        
        if not member:
            raise ValueError("User is not a member of this group")
        
        if member["role"] == "owner":
            raise ValueError("Group owner cannot leave group. Transfer ownership first.")
        
        # Remove member
        sql = """
            DELETE FROM user_group_members
            WHERE group_id = $1 AND user_id = $2
        """
        await execute(sql, group_id, user_id)
        
        logger.info(
            "user_left_group",
            group_id=group_id,
            user_id=str(user_id),
        )
    
    async def list_members(
        self,
        group_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List group members.
        
        Args:
            group_id: Group ID
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of member dicts
        """
        sql = """
            SELECT id, group_id, user_id, role, joined_at
            FROM user_group_members
            WHERE group_id = $1
            ORDER BY 
                CASE role
                    WHEN 'owner' THEN 1
                    WHEN 'admin' THEN 2
                    ELSE 3
                END,
                joined_at ASC
            LIMIT $2 OFFSET $3
        """
        
        result = await fetch(sql, group_id, limit, offset)
        return [dict(row) for row in result]
    
    async def get_group_activity(
        self,
        group_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get activity feed for a group.
        
        Args:
            group_id: Group ID
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of activity dicts
        """
        # Get group member user IDs
        members_sql = """
            SELECT user_id FROM user_group_members
            WHERE group_id = $1
        """
        members = await fetch(members_sql, group_id)
        user_ids = [row["user_id"] for row in members]
        
        if not user_ids:
            return []
        
        # Get activity from activity_stream
        sql = """
            SELECT 
                id, actor_type, actor_id, activity_type,
                location_id, city_key, category_key, payload, created_at
            FROM activity_stream
            WHERE actor_id = ANY($1::uuid[])
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        result = await fetch(sql, user_ids, limit, offset)
        return [dict(row) for row in result]
    
    async def check_membership(
        self,
        group_id: int,
        user_id: UUID,
    ) -> Optional[str]:
        """
        Check if user is a member of a group and return their role.
        
        Args:
            group_id: Group ID
            user_id: User ID
            
        Returns:
            Role if member, None otherwise
        """
        sql = """
            SELECT role FROM user_group_members
            WHERE group_id = $1 AND user_id = $2
        """
        
        result = await fetchrow(sql, group_id, user_id)
        return result["role"] if result else None


# Singleton instance
_group_service: Optional[GroupService] = None


def get_group_service() -> GroupService:
    """Get or create GroupService singleton."""
    global _group_service
    if _group_service is None:
        _group_service = GroupService()
    return _group_service







