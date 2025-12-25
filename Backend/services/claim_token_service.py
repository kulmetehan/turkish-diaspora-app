# Backend/services/claim_token_service.py
"""
Token-based Claim Service

Service for generating and validating claim tokens for token-based location claims.
Tokens are cryptographically secure and URL-safe for use in claim URLs.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

from services.db_service import fetch, fetchrow, execute
from app.core.logging import get_logger

logger = get_logger()


class TokenClaimInfo(BaseModel):
    """Information about a token-based claim."""
    location_id: int
    claim_token: str
    claim_status: str  # 'unclaimed', 'claimed_free', 'expired', 'removed'
    claimed_by_email: Optional[str] = None
    claimed_at: Optional[datetime] = None
    free_until: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    removal_reason: Optional[str] = None


async def generate_token(location_id: int) -> str:
    """
    Generate a unique, cryptographically secure token for a location.
    
    If a token already exists for this location, it will be reused.
    Otherwise, a new token is generated and stored.
    
    Args:
        location_id: The location ID to generate a token for
        
    Returns:
        The claim token (URL-safe string, minimum 32 characters)
        
    Raises:
        ValueError: If location does not exist
        RuntimeError: If token generation/storage fails
    """
    # Verify location exists
    location_sql = """
        SELECT id FROM locations WHERE id = $1
    """
    location_rows = await fetch(location_sql, location_id)
    
    if not location_rows:
        raise ValueError(f"Location {location_id} not found")
    
    # Check if token already exists for this location
    existing_token_sql = """
        SELECT claim_token FROM token_location_claims
        WHERE location_id = $1
    """
    existing_rows = await fetch(existing_token_sql, location_id)
    
    if existing_rows:
        # Token already exists, return it
        return existing_rows[0]["claim_token"]
    
    # Generate new token (URL-safe, minimum 32 characters)
    # Using 32 bytes = 43 characters in base64 URL-safe encoding
    token = secrets.token_urlsafe(32)
    
    # Ensure token is unique (retry if collision, though extremely unlikely)
    max_retries = 5
    for attempt in range(max_retries):
        # Check if token already exists
        token_check_sql = """
            SELECT id FROM token_location_claims WHERE claim_token = $1
        """
        token_rows = await fetch(token_check_sql, token)
        
        if not token_rows:
            # Token is unique, insert it
            insert_sql = """
                INSERT INTO token_location_claims (
                    location_id, claim_token, claim_status,
                    created_at, updated_at
                )
                VALUES ($1, $2, 'unclaimed', now(), now())
                RETURNING claim_token
            """
            result = await fetch(insert_sql, location_id, token)
            
            if result:
                logger.info(
                    "claim_token_generated",
                    location_id=location_id,
                    token_length=len(token),
                )
                return token
            else:
                raise RuntimeError("Failed to store claim token")
        
        # Token collision (extremely unlikely), generate new one
        if attempt < max_retries - 1:
            token = secrets.token_urlsafe(32)
            logger.warning(
                "claim_token_collision",
                location_id=location_id,
                attempt=attempt + 1,
            )
    
    raise RuntimeError("Failed to generate unique token after retries")


async def validate_token(token: str) -> Optional[TokenClaimInfo]:
    """
    Validate a claim token and return claim information.
    
    Args:
        token: The claim token to validate
        
    Returns:
        TokenClaimInfo if token is valid, None if token is invalid or expired
        
    Raises:
        ValueError: If token format is invalid
    """
    if not token or len(token) < 32:
        raise ValueError("Invalid token format")
    
    # Fetch token claim info
    sql = """
        SELECT 
            location_id, claim_token, claim_status,
            claimed_by_email, claimed_at, free_until,
            removed_at, removal_reason
        FROM token_location_claims
        WHERE claim_token = $1
    """
    row = await fetchrow(sql, token)
    
    if not row:
        logger.info("claim_token_not_found", token_length=len(token))
        return None
    
    # Check if token is expired (if status is claimed_free and free_until is past)
    if row["claim_status"] == "claimed_free" and row["free_until"]:
        if datetime.now(row["free_until"].tzinfo) > row["free_until"]:
            logger.info(
                "claim_token_expired",
                location_id=row["location_id"],
                free_until=row["free_until"].isoformat(),
            )
            # Optionally update status to expired (could be done by a background job)
            # For now, we just return the info with expired status
    
    return TokenClaimInfo(
        location_id=row["location_id"],
        claim_token=row["claim_token"],
        claim_status=row["claim_status"],
        claimed_by_email=row.get("claimed_by_email"),
        claimed_at=row.get("claimed_at"),
        free_until=row.get("free_until"),
        removed_at=row.get("removed_at"),
        removal_reason=row.get("removal_reason"),
    )


async def get_token_for_location(location_id: int) -> Optional[str]:
    """
    Get the claim token for a location if it exists.
    
    Args:
        location_id: The location ID
        
    Returns:
        The claim token if exists, None otherwise
    """
    sql = """
        SELECT claim_token FROM token_location_claims
        WHERE location_id = $1
    """
    row = await fetchrow(sql, location_id)
    
    if row:
        return row["claim_token"]
    return None

