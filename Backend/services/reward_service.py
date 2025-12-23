# Backend/services/reward_service.py
"""
Reward Service

Manages reward assignment to users who appear in Öne Çıkanlar leaderboards.
Rewards are assigned automatically or manually when users appear in leaderboard entries.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID
import logging
import random

from services.db_service import fetch, fetchrow, execute

logger = logging.getLogger(__name__)


async def check_reward_eligibility(
    user_id: UUID,
    leaderboard_entry_id: int
) -> bool:
    """
    Check if user is eligible for a reward for this leaderboard entry.
    
    A user is eligible if:
    - They don't already have a reward for this leaderboard entry
    - The leaderboard entry exists and has a rank (1-5)
    
    Args:
        user_id: UUID of the user
        leaderboard_entry_id: ID of the leaderboard entry
    
    Returns:
        True if eligible, False otherwise
    """
    try:
        # Check if user already has a reward for this entry
        existing_sql = """
            SELECT id
            FROM user_rewards
            WHERE user_id = $1
            AND leaderboard_entry_id = $2
        """
        existing_row = await fetchrow(existing_sql, user_id, leaderboard_entry_id)
        
        if existing_row:
            logger.debug(
                f"User {user_id} already has reward for leaderboard entry {leaderboard_entry_id}"
            )
            return False
        
        # Check if leaderboard entry exists and has a valid rank (1-5)
        entry_sql = """
            SELECT rank, city_key
            FROM leaderboard_entries
            WHERE id = $1
            AND rank IS NOT NULL
            AND rank <= 5
        """
        entry_row = await fetchrow(entry_sql, leaderboard_entry_id)
        
        if not entry_row:
            logger.debug(
                f"Leaderboard entry {leaderboard_entry_id} not found or invalid rank"
            )
            return False
        
        return True
        
    except Exception as e:
        logger.error(
            f"Failed to check reward eligibility for user {user_id}, entry {leaderboard_entry_id}: {e}",
            exc_info=True
        )
        return False


async def select_available_reward(
    city_key: Optional[str] = None,
    reward_type: Optional[str] = None
) -> Optional[int]:
    """
    Select an available reward from the rewards pool.
    
    Uses round-robin selection for fair distribution:
    1. Find all available rewards (available_count > 0, not expired)
    2. Filter by city_key (match or global)
    3. Filter by reward_type if specified
    4. Select one using round-robin (least recently assigned)
    
    Args:
        city_key: Optional city key to filter rewards (None = global)
        reward_type: Optional reward type filter (None = any type)
    
    Returns:
        Reward ID if found, None otherwise
    """
    try:
        # Build query for available rewards
        sql = """
            SELECT r.id, r.available_count, r.city_key, r.reward_type,
                   COUNT(ur.id) as assigned_count
            FROM rewards r
            LEFT JOIN user_rewards ur ON r.id = ur.reward_id
            WHERE r.available_count > 0
            AND (r.expires_at IS NULL OR r.expires_at > NOW())
            AND ($1::text IS NULL OR r.city_key = $1 OR r.city_key IS NULL)
            AND ($2::text IS NULL OR r.reward_type = $2::reward_type)
            GROUP BY r.id, r.available_count, r.city_key, r.reward_type
            ORDER BY assigned_count ASC, r.id ASC
            LIMIT 10
        """
        
        rows = await fetch(sql, city_key, reward_type)
        
        if not rows:
            logger.debug(f"No available rewards found for city_key={city_key}, type={reward_type}")
            return None
        
        # Round-robin: select the reward with least assignments
        # If multiple have same count, pick randomly from top candidates
        min_assigned = min(int(row.get("assigned_count", 0) or 0) for row in rows)
        candidates = [
            row for row in rows
            if int(row.get("assigned_count", 0) or 0) == min_assigned
        ]
        
        # Random selection from candidates for fair distribution
        selected = random.choice(candidates)
        reward_id = int(selected.get("id"))
        
        logger.info(
            f"Selected reward {reward_id} for city_key={city_key}, type={reward_type}, "
            f"assigned_count={min_assigned}"
        )
        
        return reward_id
        
    except Exception as e:
        logger.error(
            f"Failed to select available reward: {e}",
            exc_info=True
        )
        return None


async def assign_reward_to_leaderboard_user(
    user_id: UUID,
    leaderboard_entry_id: int,
    city_key: Optional[str] = None,
    reward_type: Optional[str] = None
) -> Optional[int]:
    """
    Assign a reward to a user who appears in a leaderboard entry.
    
    This function:
    1. Checks eligibility (no duplicate reward for this entry)
    2. Selects an available reward
    3. Creates user_rewards entry
    4. Decrements available_count in rewards table
    
    Args:
        user_id: UUID of the user
        leaderboard_entry_id: ID of the leaderboard entry that triggered this
        city_key: Optional city key (will be fetched from leaderboard entry if not provided)
        reward_type: Optional reward type filter (None = any type)
    
    Returns:
        user_rewards ID if successful, None otherwise
    """
    try:
        # Check eligibility first
        if not await check_reward_eligibility(user_id, leaderboard_entry_id):
            logger.debug(
                f"User {user_id} not eligible for reward for entry {leaderboard_entry_id}"
            )
            return None
        
        # Get city_key from leaderboard entry if not provided
        if city_key is None:
            entry_sql = """
                SELECT city_key
                FROM leaderboard_entries
                WHERE id = $1
            """
            entry_row = await fetchrow(entry_sql, leaderboard_entry_id)
            if entry_row:
                city_key = entry_row.get("city_key")
        
        # Select available reward
        reward_id = await select_available_reward(city_key, reward_type)
        
        if not reward_id:
            logger.warning(
                f"No available reward found for user {user_id}, entry {leaderboard_entry_id}, "
                f"city_key={city_key}"
            )
            return None
        
        # Create user_rewards entry and decrement available_count atomically
        # Use transaction to ensure atomicity
        insert_sql = """
            WITH reward_update AS (
                UPDATE rewards
                SET available_count = available_count - 1,
                    updated_at = NOW()
                WHERE id = $1
                AND available_count > 0
                RETURNING id
            )
            INSERT INTO user_rewards (
                user_id,
                reward_id,
                leaderboard_entry_id,
                status,
                created_at,
                updated_at
            )
            SELECT $2, $1, $3, 'pending', NOW(), NOW()
            FROM reward_update
            WHERE EXISTS (SELECT 1 FROM reward_update)
            RETURNING id
        """
        
        result = await fetchrow(insert_sql, reward_id, user_id, leaderboard_entry_id)
        
        if not result:
            logger.warning(
                f"Failed to assign reward {reward_id} to user {user_id} - "
                f"reward may have been exhausted or already assigned"
            )
            return None
        
        user_reward_id = int(result.get("id"))
        
        logger.info(
            f"Assigned reward {reward_id} to user {user_id} for leaderboard entry {leaderboard_entry_id}, "
            f"user_reward_id={user_reward_id}"
        )
        
        return user_reward_id
        
    except Exception as e:
        logger.error(
            f"Failed to assign reward to user {user_id}, entry {leaderboard_entry_id}: {e}",
            exc_info=True
        )
        return None


