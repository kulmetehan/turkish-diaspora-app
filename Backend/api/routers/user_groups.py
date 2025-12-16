# Backend/api/routers/user_groups.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID

from app.deps.auth import get_current_user, User
from services.group_service import get_group_service
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/groups", tags=["user-groups"])


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = True


class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: UUID
    is_public: bool
    member_count: int
    created_at: str
    updated_at: str


class GroupMemberResponse(BaseModel):
    id: int
    group_id: int
    user_id: UUID
    role: str
    joined_at: str


class ActivityResponse(BaseModel):
    id: int
    actor_type: str
    actor_id: Optional[UUID]
    activity_type: str
    location_id: Optional[int]
    city_key: Optional[str]
    category_key: Optional[str]
    payload: Optional[dict]
    created_at: str


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    group: GroupCreate,
    user: User = Depends(get_current_user),
):
    """
    Create a new user group.
    """
    if len(group.name) < 3 or len(group.name) > 100:
        raise HTTPException(
            status_code=400,
            detail="Group name must be between 3 and 100 characters"
        )
    
    group_service = get_group_service()
    
    try:
        created_group = await group_service.create_group(
            name=group.name,
            description=group.description,
            created_by=user.user_id,
            is_public=group.is_public,
        )
        
        # Convert to response format
        return GroupResponse(
            id=created_group["id"],
            name=created_group["name"],
            description=created_group["description"],
            created_by=created_group["created_by"],
            is_public=created_group["is_public"],
            member_count=created_group["member_count"],
            created_at=created_group["created_at"].isoformat() if hasattr(created_group["created_at"], "isoformat") else str(created_group["created_at"]),
            updated_at=created_group["updated_at"].isoformat() if hasattr(created_group["updated_at"], "isoformat") else str(created_group["updated_at"]),
        )
    except Exception as e:
        logger.error(
            "group_creation_failed",
            user_id=str(user.user_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create group: {str(e)}"
        )


@router.get("", response_model=List[GroupResponse])
async def list_groups(
    search: Optional[str] = Query(None, description="Search term"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: Optional[User] = Depends(get_current_user),
):
    """
    List groups with optional filters.
    """
    group_service = get_group_service()
    
    groups = await group_service.list_groups(
        search=search,
        is_public=is_public,
        limit=limit,
        offset=offset,
    )
    
    return [
        GroupResponse(
            id=g["id"],
            name=g["name"],
            description=g["description"],
            created_by=g["created_by"],
            is_public=g["is_public"],
            member_count=g["member_count"],
            created_at=g["created_at"].isoformat() if hasattr(g["created_at"], "isoformat") else str(g["created_at"]),
            updated_at=g["updated_at"].isoformat() if hasattr(g["updated_at"], "isoformat") else str(g["updated_at"]),
        )
        for g in groups
    ]


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int = Path(..., description="Group ID"),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get group details.
    """
    group_service = get_group_service()
    group = await group_service.get_group(group_id)
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return GroupResponse(
        id=group["id"],
        name=group["name"],
        description=group["description"],
        created_by=group["created_by"],
        is_public=group["is_public"],
        member_count=group["member_count"],
        created_at=group["created_at"].isoformat() if hasattr(group["created_at"], "isoformat") else str(group["created_at"]),
        updated_at=group["updated_at"].isoformat() if hasattr(group["updated_at"], "isoformat") else str(group["updated_at"]),
    )


@router.post("/{group_id}/join", status_code=201)
async def join_group(
    group_id: int = Path(..., description="Group ID"),
    user: User = Depends(get_current_user),
):
    """
    Join a group.
    """
    group_service = get_group_service()
    
    try:
        membership = await group_service.join_group(
            group_id=group_id,
            user_id=user.user_id,
        )
        return {"ok": True, "message": "Joined group successfully", "membership": membership}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{group_id}/leave", status_code=204)
async def leave_group(
    group_id: int = Path(..., description="Group ID"),
    user: User = Depends(get_current_user),
):
    """
    Leave a group.
    """
    group_service = get_group_service()
    
    try:
        await group_service.leave_group(
            group_id=group_id,
            user_id=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{group_id}/members", response_model=List[GroupMemberResponse])
async def list_members(
    group_id: int = Path(..., description="Group ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: Optional[User] = Depends(get_current_user),
):
    """
    List group members.
    """
    group_service = get_group_service()
    members = await group_service.list_members(
        group_id=group_id,
        limit=limit,
        offset=offset,
    )
    
    return [
        GroupMemberResponse(
            id=m["id"],
            group_id=m["group_id"],
            user_id=m["user_id"],
            role=m["role"],
            joined_at=m["joined_at"].isoformat() if hasattr(m["joined_at"], "isoformat") else str(m["joined_at"]),
        )
        for m in members
    ]


@router.get("/{group_id}/activity", response_model=List[ActivityResponse])
async def get_group_activity(
    group_id: int = Path(..., description="Group ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get group activity feed.
    """
    group_service = get_group_service()
    activity = await group_service.get_group_activity(
        group_id=group_id,
        limit=limit,
        offset=offset,
    )
    
    return [
        ActivityResponse(
            id=a["id"],
            actor_type=a["actor_type"],
            actor_id=a.get("actor_id"),
            activity_type=a["activity_type"],
            location_id=a.get("location_id"),
            city_key=a.get("city_key"),
            category_key=a.get("category_key"),
            payload=a.get("payload"),
            created_at=a["created_at"].isoformat() if hasattr(a["created_at"], "isoformat") else str(a["created_at"]),
        )
        for a in activity
    ]

















