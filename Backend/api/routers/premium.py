# Backend/api/routers/premium.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.deps.auth import get_current_user, User
from services.premium_service import get_premium_service
from services.stripe_service import get_stripe_service
from services.db_service import fetch
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/premium", tags=["premium"])


class SubscribeRequest(BaseModel):
    tier: str  # 'premium' or 'pro'
    success_url: str
    cancel_url: str


class SubscriptionStatusResponse(BaseModel):
    tier: str
    status: str
    stripe_subscription_id: Optional[str]
    current_period_end: Optional[str]
    enabled_features: list[str]


class FeaturesResponse(BaseModel):
    tier: str
    features: list[str]


async def get_user_business_account(user: User) -> int:
    """
    Get the business account ID for the current user.
    """
    sql = """
        SELECT id FROM business_accounts WHERE owner_user_id = $1
        LIMIT 1
    """
    result = await fetch(sql, user.user_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Business account not found"
        )
    
    return result[0]["id"]


@router.post("/subscribe")
async def create_subscription(
    request: SubscribeRequest,
    user: User = Depends(get_current_user),
):
    """
    Create a Stripe Checkout session for subscription.
    """
    if request.tier not in ["premium", "pro"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid tier. Must be 'premium' or 'pro'"
        )
    
    business_account_id = await get_user_business_account(user)
    
    stripe_service = get_stripe_service()
    session = await stripe_service.create_checkout_session(
        business_account_id=business_account_id,
        tier=request.tier,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )
    
    return session


@router.get("/features", response_model=FeaturesResponse)
async def get_features(
    tier: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get available features for a subscription tier.
    If tier is not provided, returns features for user's current tier.
    """
    premium_service = get_premium_service()
    
    if tier:
        if tier not in ["basic", "premium", "pro"]:
            raise HTTPException(status_code=400, detail="Invalid tier")
        features = await premium_service.get_features_for_tier(tier)
    else:
        # Get user's current tier
        business_account_id = await get_user_business_account(user)
        account_sql = """
            SELECT subscription_tier FROM business_accounts WHERE id = $1
        """
        account_rows = await fetch(account_sql, business_account_id)
        if not account_rows:
            raise HTTPException(status_code=404, detail="Business account not found")
        tier = account_rows[0]["subscription_tier"]
        features = await premium_service.get_features_for_tier(tier)
    
    return FeaturesResponse(tier=tier, features=features)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="stripe-signature"),
):
    """
    Handle Stripe webhook events.
    """
    payload = await request.body()
    
    stripe_service = get_stripe_service()
    
    try:
        result = await stripe_service.handle_webhook(
            payload=payload,
            signature=stripe_signature,
        )
        return result
    except Exception as e:
        logger.error(
            "stripe_webhook_error",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")


@router.get("/subscription", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    user: User = Depends(get_current_user),
):
    """
    Get current subscription status for the authenticated user's business account.
    """
    business_account_id = await get_user_business_account(user)
    
    premium_service = get_premium_service()
    status = await premium_service.get_subscription_status(
        business_account_id=business_account_id,
    )
    
    return SubscriptionStatusResponse(**status)


















