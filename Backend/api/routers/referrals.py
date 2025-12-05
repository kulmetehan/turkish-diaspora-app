# Backend/api/routers/referrals.py
from __future__ import annotations

import secrets
import string
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from uuid import UUID

from app.deps.auth import get_current_user, get_current_user_optional, User
from services.db_service import fetch, execute
from app.core.logging import get_logger
from services.xp_service import award_xp

logger = get_logger()

router = APIRouter(prefix="/referrals", tags=["referrals"])


def generate_referral_code(length: int = 8) -> str:
    """Generate a random alphanumeric referral code."""
    alphabet = string.ascii_uppercase + string.digits
    # Remove ambiguous characters: 0, O, I, 1
    alphabet = alphabet.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
    return "".join(secrets.choice(alphabet) for _ in range(length))


class ReferralCodeResponse(BaseModel):
    code: str
    uses_count: int
    created_at: str


class ReferralStatsResponse(BaseModel):
    total_referrals: int
    referrals_last_30d: int
    referral_code: str


class ClaimReferralRequest(BaseModel):
    code: str


class ClaimReferralResponse(BaseModel):
    success: bool
    referrer_name: Optional[str] = None
    message: str


@router.get("/code", response_model=ReferralCodeResponse)
async def get_my_referral_code(
    user: User = Depends(get_current_user),
):
    """
    Get or create the current user's referral code.
    """
    # Check if user already has a referral code
    sql = """
        SELECT code, uses_count, created_at
        FROM referral_codes
        WHERE user_id = $1::uuid
    """
    rows = await fetch(sql, user.user_id)
    
    if rows:
        row = rows[0]
        return ReferralCodeResponse(
            code=row["code"],
            uses_count=row.get("uses_count", 0) or 0,
            created_at=row["created_at"].isoformat() if row.get("created_at") else "",
        )
    
    # Generate a new referral code
    max_attempts = 10
    for _ in range(max_attempts):
        code = generate_referral_code()
        
        # Check if code is unique
        check_sql = "SELECT id FROM referral_codes WHERE code = $1"
        existing = await fetch(check_sql, code)
        
        if not existing:
            # Create new referral code
            insert_sql = """
                INSERT INTO referral_codes (user_id, code, uses_count, created_at)
                VALUES ($1::uuid, $2, 0, now())
                RETURNING code, uses_count, created_at
            """
            result = await fetch(insert_sql, user.user_id, code)
            
            if result:
                row = result[0]
                logger.info("referral_code_created", user_id=str(user.user_id), code=code)
                return ReferralCodeResponse(
                    code=row["code"],
                    uses_count=0,
                    created_at=row["created_at"].isoformat() if row.get("created_at") else "",
                )
    
    raise HTTPException(status_code=500, detail="Failed to generate unique referral code")


@router.post("/claim", response_model=ClaimReferralResponse)
async def claim_referral(
    request: ClaimReferralRequest,
    user: User = Depends(get_current_user),
):
    """
    Claim a referral code during signup.
    This should be called after user signs up but before they complete onboarding.
    """
    code = request.code.strip().upper()
    
    # Find referral code owner
    find_sql = """
        SELECT user_id
        FROM referral_codes
        WHERE code = $1
    """
    rows = await fetch(find_sql, code)
    
    if not rows:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    
    referrer_id = rows[0]["user_id"]
    
    # Check if user is trying to refer themselves
    if referrer_id == user.user_id:
        raise HTTPException(status_code=400, detail="You cannot use your own referral code")
    
    # Check if user has already been referred
    check_existing_sql = """
        SELECT id FROM referrals WHERE referred_id = $1::uuid
    """
    existing = await fetch(check_existing_sql, user.user_id)
    
    if existing:
        raise HTTPException(status_code=400, detail="You have already claimed a referral code")
    
    # Create referral relationship
    try:
        insert_sql = """
            INSERT INTO referrals (referrer_id, referred_id, code, created_at)
            VALUES ($1::uuid, $2::uuid, $3, now())
            RETURNING id
        """
        await execute(insert_sql, referrer_id, user.user_id, code)
        
        # Update referral code uses count
        update_count_sql = """
            UPDATE referral_codes
            SET uses_count = uses_count + 1
            WHERE code = $3
        """
        await execute(update_count_sql, referrer_id, user.user_id, code)
        
        # Award XP bonuses
        try:
            # Award XP to referrer (50 XP)
            await award_xp(
                user_id=str(referrer_id),
                client_id=None,
                source="referral",
                source_id=None,
                amount=50,
            )
            
            # Award welcome bonus to referred user (25 XP)
            await award_xp(
                user_id=str(user.user_id),
                client_id=None,
                source="referral_welcome",
                source_id=None,
                amount=25,
            )
            
            # Mark XP as awarded
            mark_xp_sql = """
                UPDATE referrals
                SET referrer_xp_awarded = true, referred_xp_awarded = true
                WHERE referred_id = $1::uuid AND code = $2
            """
            await execute(mark_xp_sql, user.user_id, code)
            
        except Exception as e:
            logger.warning("referral_xp_award_failed", error=str(e), exc_info=True)
            # Don't fail the referral claim if XP awarding fails
        
        # Get referrer name for response
        profile_sql = """
            SELECT display_name
            FROM user_profiles
            WHERE id = $1::uuid
        """
        profile_rows = await fetch(profile_sql, referrer_id)
        referrer_name = profile_rows[0].get("display_name") if profile_rows else None
        
        logger.info(
            "referral_claimed",
            referrer_id=str(referrer_id),
            referred_id=str(user.user_id),
            code=code,
        )
        
        return ClaimReferralResponse(
            success=True,
            referrer_name=referrer_name,
            message="Referral code claimed successfully! Welcome bonus awarded.",
        )
        
    except Exception as e:
        logger.error("referral_claim_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to claim referral: {str(e)}")


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    user: User = Depends(get_current_user),
):
    """
    Get referral statistics for the current user.
    """
    # Get referral code
    code_sql = """
        SELECT code
        FROM referral_codes
        WHERE user_id = $1::uuid
    """
    code_rows = await fetch(code_sql, user.user_id)
    
    if not code_rows:
        raise HTTPException(status_code=404, detail="Referral code not found. Generate one first.")
    
    code = code_rows[0]["code"]
    
    # Get referral stats
    stats_sql = """
        SELECT 
            COUNT(*) as total_referrals,
            COUNT(*) FILTER (WHERE created_at >= now() - INTERVAL '30 days') as referrals_last_30d
        FROM referrals
        WHERE referrer_id = $1::uuid
    """
    stats_rows = await fetch(stats_sql, user.user_id)
    
    if not stats_rows:
        return ReferralStatsResponse(
            total_referrals=0,
            referrals_last_30d=0,
            referral_code=code,
        )
    
    row = stats_rows[0]
    return ReferralStatsResponse(
        total_referrals=row.get("total_referrals", 0) or 0,
        referrals_last_30d=row.get("referrals_last_30d", 0) or 0,
        referral_code=code,
    )

