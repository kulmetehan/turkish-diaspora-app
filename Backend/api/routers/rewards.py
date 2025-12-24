# Backend/api/routers/rewards.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from app.deps.auth import get_current_user, User
from services.db_service import fetch, fetchrow, execute
from services.reward_service import (
    assign_reward_to_leaderboard_user,
    check_reward_eligibility,
)

router = APIRouter(prefix="/rewards", tags=["rewards"])


class RewardResponse(BaseModel):
    """Reward details for user."""
    id: int
    title: str
    description: Optional[str] = None
    reward_type: str
    sponsor: str
    status: str
    claimed_at: Optional[datetime] = None
    created_at: datetime


class UserRewardResponse(BaseModel):
    """User reward entry."""
    id: int
    reward: RewardResponse
    leaderboard_entry_id: Optional[int] = None
    status: str
    claimed_at: Optional[datetime] = None
    created_at: datetime


class ClaimRewardResponse(BaseModel):
    """Response after claiming a reward."""
    success: bool
    reward: Optional[RewardResponse] = None
    message: str


@router.get("/me", response_model=List[UserRewardResponse])
async def get_my_rewards(
    user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status (pending, claimed, expired, cancelled)")
):
    """
    Get all rewards for the current user.
    
    Returns list of user rewards, optionally filtered by status.
    """
    try:
        sql = """
            SELECT 
                ur.id,
                ur.leaderboard_entry_id,
                ur.status,
                ur.claimed_at,
                ur.created_at,
                r.id as reward_id,
                r.title,
                r.description,
                r.reward_type,
                r.sponsor
            FROM user_rewards ur
            INNER JOIN rewards r ON ur.reward_id = r.id
            WHERE ur.user_id = $1::uuid
            AND ($2::text IS NULL OR ur.status = $2::reward_status)
            ORDER BY ur.created_at DESC
        """
        
        rows = await fetch(sql, user.user_id, status)
        
        rewards = []
        for row in rows:
            rewards.append(
                UserRewardResponse(
                    id=int(row.get("id")),
                    reward=RewardResponse(
                        id=int(row.get("reward_id")),
                        title=row.get("title"),
                        description=row.get("description"),
                        reward_type=row.get("reward_type"),
                        sponsor=row.get("sponsor"),
                        status=row.get("status"),
                        claimed_at=row.get("claimed_at"),
                        created_at=row.get("created_at"),
                    ),
                    leaderboard_entry_id=int(row.get("leaderboard_entry_id")) if row.get("leaderboard_entry_id") else None,
                    status=row.get("status"),
                    claimed_at=row.get("claimed_at"),
                    created_at=row.get("created_at"),
                )
            )
        
        return rewards
        
    except Exception as e:
        error_str = str(e)
        error_type = type(e).__name__
        
        # Graceful degradation: if tables don't exist, return empty list
        if "does not exist" in error_str.lower() or "UndefinedTableError" in error_type:
            return []
        
        raise HTTPException(status_code=500, detail=f"Failed to fetch rewards: {str(e)}")


@router.get("/me/pending", response_model=List[UserRewardResponse])
async def get_my_pending_rewards(
    user: User = Depends(get_current_user)
):
    """
    Get pending (unclaimed) rewards for the current user.
    
    Convenience endpoint that returns only pending rewards.
    """
    return await get_my_rewards(user=user, status="pending")


@router.post("/{reward_id}/claim", response_model=ClaimRewardResponse)
async def claim_reward(
    reward_id: int = Path(..., description="User reward ID (from user_rewards table)"),
    user: User = Depends(get_current_user)
):
    """
    Claim a reward.
    
    Updates the reward status to 'claimed' and sets claimed_at timestamp.
    Only the owner of the reward can claim it.
    """
    try:
        # Verify reward belongs to user and is pending
        check_sql = """
            SELECT ur.id, ur.status, r.id as reward_id, r.title, r.description, 
                   r.reward_type, r.sponsor, ur.created_at
            FROM user_rewards ur
            INNER JOIN rewards r ON ur.reward_id = r.id
            WHERE ur.id = $1
            AND ur.user_id = $2::uuid
        """
        
        row = await fetchrow(check_sql, reward_id, user.user_id)
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Reward not found or you don't have permission to claim it"
            )
        
        current_status = row.get("status")
        if current_status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Reward cannot be claimed. Current status: {current_status}"
            )
        
        # Update reward status to claimed
        update_sql = """
            UPDATE user_rewards
            SET status = 'claimed',
                claimed_at = NOW(),
                updated_at = NOW()
            WHERE id = $1
            AND user_id = $2::uuid
            AND status = 'pending'
            RETURNING id
        """
        
        result = await fetchrow(update_sql, reward_id, user.user_id)
        
        if not result:
            raise HTTPException(
                status_code=400,
                detail="Failed to claim reward. It may have already been claimed or expired."
            )
        
        # Fetch updated reward details
        reward_sql = """
            SELECT 
                ur.id,
                ur.status,
                ur.claimed_at,
                ur.created_at,
                r.id as reward_id,
                r.title,
                r.description,
                r.reward_type,
                r.sponsor
            FROM user_rewards ur
            INNER JOIN rewards r ON ur.reward_id = r.id
            WHERE ur.id = $1
        """
        
        reward_row = await fetchrow(reward_sql, reward_id)
        
        return ClaimRewardResponse(
            success=True,
            reward=RewardResponse(
                id=int(reward_row.get("reward_id")),
                title=reward_row.get("title"),
                description=reward_row.get("description"),
                reward_type=reward_row.get("reward_type"),
                sponsor=reward_row.get("sponsor"),
                status=reward_row.get("status"),
                claimed_at=reward_row.get("claimed_at"),
                created_at=reward_row.get("created_at"),
            ),
            message="Reward successfully claimed"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to claim reward: {str(e)}")


@router.post("/assign/{leaderboard_entry_id}")
async def assign_reward_to_entry(
    leaderboard_entry_id: int = Path(..., description="Leaderboard entry ID"),
    reward_type: Optional[str] = Query(None, description="Optional reward type filter"),
    user: User = Depends(get_current_user)
):
    """
    Manually assign a reward to a user for a leaderboard entry.
    
    This endpoint can be used by admins or automated processes to assign rewards.
    The reward will be automatically selected from available rewards.
    
    Note: This is a convenience endpoint. In production, rewards might be assigned
    automatically via database triggers or worker processes.
    """
    try:
        # Get leaderboard entry details
        entry_sql = """
            SELECT user_id, city_key, rank
            FROM leaderboard_entries
            WHERE id = $1
        """
        
        entry_row = await fetchrow(entry_sql, leaderboard_entry_id)
        
        if not entry_row:
            raise HTTPException(
                status_code=404,
                detail="Leaderboard entry not found"
            )
        
        user_id_uuid = UUID(str(entry_row.get("user_id")))
        city_key = entry_row.get("city_key")
        
        # Check eligibility
        if not await check_reward_eligibility(user_id_uuid, leaderboard_entry_id):
            raise HTTPException(
                status_code=400,
                detail="User is not eligible for a reward for this leaderboard entry"
            )
        
        # Assign reward
        user_reward_id = await assign_reward_to_leaderboard_user(
            user_id=user_id_uuid,
            leaderboard_entry_id=leaderboard_entry_id,
            city_key=city_key,
            reward_type=reward_type
        )
        
        if not user_reward_id:
            raise HTTPException(
                status_code=400,
                detail="Failed to assign reward. No available rewards found."
            )
        
        return {
            "success": True,
            "user_reward_id": user_reward_id,
            "message": "Reward assigned successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign reward: {str(e)}")

