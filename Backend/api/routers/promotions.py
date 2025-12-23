# Backend/api/routers/promotions.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from typing import List, Optional
from pydantic import BaseModel

from app.deps.auth import get_current_user, User
from services.promotion_service import get_promotion_service
from services.stripe_service import get_stripe_service
from services.db_service import fetch
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/promotions", tags=["promotions"])


class CreateLocationPromotionRequest(BaseModel):
    location_id: int
    promotion_type: str  # 'trending', 'feed', 'both'
    duration_days: int  # 7, 14, or 30


class CreateNewsPromotionRequest(BaseModel):
    title: str
    content: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    duration_days: int  # 7, 14, or 30


class PromotionResponse(BaseModel):
    id: int
    promotion_type: Optional[str] = None
    location_id: Optional[int] = None
    title: Optional[str] = None
    starts_at: str
    ends_at: str
    status: str
    price_cents: Optional[int] = None
    payment_intent_id: Optional[str] = None
    client_secret: Optional[str] = None


class LocationPromotionResponse(BaseModel):
    id: int
    location_id: int
    location_name: Optional[str] = None
    promotion_type: str
    starts_at: str
    ends_at: str
    status: str
    stripe_payment_intent_id: Optional[str] = None
    created_at: str


class NewsPromotionResponse(BaseModel):
    id: int
    title: str
    content: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    starts_at: str
    ends_at: str
    status: str
    stripe_payment_intent_id: Optional[str] = None
    created_at: str


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


@router.post("/locations", response_model=PromotionResponse)
async def create_location_promotion(
    request: CreateLocationPromotionRequest,
    user: User = Depends(get_current_user),
):
    """
    Create a location promotion and return Stripe payment intent.
    """
    if request.promotion_type not in ["trending", "feed", "both"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid promotion_type. Must be 'trending', 'feed', or 'both'"
        )
    
    if request.duration_days not in [7, 14, 30]:
        raise HTTPException(
            status_code=400,
            detail="Invalid duration_days. Must be 7, 14, or 30"
        )
    
    business_account_id = await get_user_business_account(user)
    
    promotion_service = get_promotion_service()
    stripe_service = get_stripe_service()
    
    try:
        # Create promotion
        promotion = await promotion_service.create_location_promotion(
            business_account_id=business_account_id,
            location_id=request.location_id,
            promotion_type=request.promotion_type,
            duration_days=request.duration_days,
        )
        
        # Create payment intent
        payment_intent = await stripe_service.create_promotion_payment_intent(
            business_account_id=business_account_id,
            promotion_type="location",
            promotion_id=promotion["id"],
            amount_cents=promotion["price_cents"],
        )
        
        return PromotionResponse(
            id=promotion["id"],
            promotion_type=request.promotion_type,
            location_id=request.location_id,
            starts_at=promotion["starts_at"].isoformat(),
            ends_at=promotion["ends_at"].isoformat(),
            status=promotion["status"],
            price_cents=promotion["price_cents"],
            payment_intent_id=payment_intent["payment_intent_id"],
            client_secret=payment_intent["client_secret"],
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "create_location_promotion_failed",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to create promotion")


@router.post("/news", response_model=PromotionResponse)
async def create_news_promotion(
    request: CreateNewsPromotionRequest,
    user: User = Depends(get_current_user),
):
    """
    Create a news promotion and return Stripe payment intent.
    """
    if request.duration_days not in [7, 14, 30]:
        raise HTTPException(
            status_code=400,
            detail="Invalid duration_days. Must be 7, 14, or 30"
        )
    
    if not request.title or not request.content:
        raise HTTPException(
            status_code=400,
            detail="Title and content are required"
        )
    
    business_account_id = await get_user_business_account(user)
    
    promotion_service = get_promotion_service()
    stripe_service = get_stripe_service()
    
    try:
        # Create promotion
        promotion = await promotion_service.create_news_promotion(
            business_account_id=business_account_id,
            title=request.title,
            content=request.content,
            url=request.url,
            image_url=request.image_url,
            duration_days=request.duration_days,
        )
        
        # Create payment intent
        payment_intent = await stripe_service.create_promotion_payment_intent(
            business_account_id=business_account_id,
            promotion_type="news",
            promotion_id=promotion["id"],
            amount_cents=promotion["price_cents"],
        )
        
        return PromotionResponse(
            id=promotion["id"],
            title=promotion["title"],
            starts_at=promotion["starts_at"].isoformat(),
            ends_at=promotion["ends_at"].isoformat(),
            status=promotion["status"],
            price_cents=promotion["price_cents"],
            payment_intent_id=payment_intent["payment_intent_id"],
            client_secret=payment_intent["client_secret"],
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "create_news_promotion_failed",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to create promotion")


@router.get("/locations", response_model=List[LocationPromotionResponse])
async def list_location_promotions(
    user: User = Depends(get_current_user),
):
    """
    List all location promotions for the authenticated business account.
    """
    business_account_id = await get_user_business_account(user)
    
    promotion_service = get_promotion_service()
    promotions = await promotion_service.list_location_promotions(
        business_account_id=business_account_id,
    )
    
    # Get location names
    location_ids = [p["location_id"] for p in promotions if p.get("location_id")]
    location_names = {}
    if location_ids:
        location_sql = """
            SELECT id, name
            FROM locations
            WHERE id = ANY($1)
        """
        location_rows = await fetch(location_sql, location_ids)
        location_names = {row["id"]: row["name"] for row in location_rows}
    
    return [
        LocationPromotionResponse(
            id=p["id"],
            location_id=p["location_id"],
            location_name=location_names.get(p["location_id"]),
            promotion_type=p["promotion_type"],
            starts_at=p["starts_at"].isoformat() if hasattr(p["starts_at"], "isoformat") else str(p["starts_at"]),
            ends_at=p["ends_at"].isoformat() if hasattr(p["ends_at"], "isoformat") else str(p["ends_at"]),
            status=p["status"],
            stripe_payment_intent_id=p.get("stripe_payment_intent_id"),
            created_at=p["created_at"].isoformat() if hasattr(p["created_at"], "isoformat") else str(p["created_at"]),
        )
        for p in promotions
    ]


@router.get("/news", response_model=List[NewsPromotionResponse])
async def list_news_promotions(
    user: User = Depends(get_current_user),
):
    """
    List all news promotions for the authenticated business account.
    """
    business_account_id = await get_user_business_account(user)
    
    promotion_service = get_promotion_service()
    promotions = await promotion_service.list_news_promotions(
        business_account_id=business_account_id,
    )
    
    return [
        NewsPromotionResponse(
            id=p["id"],
            title=p["title"],
            content=p["content"],
            url=p.get("url"),
            image_url=p.get("image_url"),
            starts_at=p["starts_at"].isoformat() if hasattr(p["starts_at"], "isoformat") else str(p["starts_at"]),
            ends_at=p["ends_at"].isoformat() if hasattr(p["ends_at"], "isoformat") else str(p["ends_at"]),
            status=p["status"],
            stripe_payment_intent_id=p.get("stripe_payment_intent_id"),
            created_at=p["created_at"].isoformat() if hasattr(p["created_at"], "isoformat") else str(p["created_at"]),
        )
        for p in promotions
    ]


@router.delete("/locations/{promotion_id}")
async def cancel_location_promotion(
    promotion_id: int = Path(..., description="Promotion ID"),
    user: User = Depends(get_current_user),
):
    """
    Cancel a location promotion (only if pending or not started).
    """
    business_account_id = await get_user_business_account(user)
    
    promotion_service = get_promotion_service()
    cancelled = await promotion_service.cancel_promotion(
        promotion_type="location",
        promotion_id=promotion_id,
        business_account_id=business_account_id,
    )
    
    if not cancelled:
        raise HTTPException(
            status_code=400,
            detail="Promotion cannot be cancelled (may have already started or expired)"
        )
    
    return {"success": True, "message": "Promotion cancelled"}


@router.delete("/news/{promotion_id}")
async def cancel_news_promotion(
    promotion_id: int = Path(..., description="Promotion ID"),
    user: User = Depends(get_current_user),
):
    """
    Cancel a news promotion (only if pending or not started).
    """
    business_account_id = await get_user_business_account(user)
    
    promotion_service = get_promotion_service()
    cancelled = await promotion_service.cancel_promotion(
        promotion_type="news",
        promotion_id=promotion_id,
        business_account_id=business_account_id,
    )
    
    if not cancelled:
        raise HTTPException(
            status_code=400,
            detail="Promotion cannot be cancelled (may have already started or expired)"
        )
    
    return {"success": True, "message": "Promotion cancelled"}


@router.get("/claimed-locations")
async def get_claimed_locations(
    user: User = Depends(get_current_user),
):
    """
    Get list of locations claimed by the business account (for promotion selection).
    """
    business_account_id = await get_user_business_account(user)
    
    sql = """
        SELECT 
            l.id,
            l.name,
            l.address,
            l.category,
            blc.status as claim_status
        FROM business_location_claims blc
        JOIN locations l ON blc.location_id = l.id
        WHERE blc.business_account_id = $1
          AND blc.status = 'approved'
        ORDER BY l.name
    """
    
    rows = await fetch(sql, business_account_id)
    
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "address": row.get("address"),
            "category": row.get("category"),
        }
        for row in rows
    ]

























