# Backend/services/promotion_service.py
from __future__ import annotations

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

from services.db_service import fetch, execute
from app.core.logging import get_logger

logger = get_logger()


def get_promotion_price(
    promotion_type: str,  # 'location_trending', 'location_feed', 'news'
    duration_days: int,
) -> int:
    """
    Get promotion price in cents based on type and duration.
    
    Args:
        promotion_type: Type of promotion ('location_trending', 'location_feed', 'news')
        duration_days: Duration in days (7, 14, or 30)
        
    Returns:
        Price in cents
    """
    env_key = f"PROMOTION_{promotion_type.upper()}_PRICE_{duration_days}D"
    price = os.getenv(env_key)
    
    if not price:
        # Default pricing if env vars not set
        defaults = {
            ("location_trending", 7): 5000,
            ("location_trending", 14): 9000,
            ("location_trending", 30): 15000,
            ("location_feed", 7): 3000,
            ("location_feed", 14): 5500,
            ("location_feed", 30): 9000,
            ("news", 7): 2000,
            ("news", 14): 3500,
            ("news", 30): 5500,
        }
        return defaults.get((promotion_type, duration_days), 0)
    
    try:
        return int(price)
    except ValueError:
        logger.warning(
            "invalid_promotion_price_env",
            env_key=env_key,
            value=price,
        )
        return 0


def calculate_promotion_dates(duration_days: int) -> tuple[datetime, datetime]:
    """
    Calculate starts_at and ends_at for a promotion.
    
    Args:
        duration_days: Duration in days
        
    Returns:
        Tuple of (starts_at, ends_at) timestamps
    """
    now = datetime.now(timezone.utc)
    starts_at = now
    ends_at = now + timedelta(days=duration_days)
    return starts_at, ends_at


class PromotionService:
    """
    Service for promotion management (locations and news).
    """
    
    async def create_location_promotion(
        self,
        business_account_id: int,
        location_id: int,
        promotion_type: str,  # 'trending', 'feed', 'both'
        duration_days: int,
    ) -> Dict[str, Any]:
        """
        Create a location promotion request.
        
        Args:
            business_account_id: Business account ID
            location_id: Location ID to promote
            promotion_type: Type of promotion ('trending', 'feed', 'both')
            duration_days: Duration in days (7, 14, or 30)
            
        Returns:
            Dict with promotion details including price
        """
        # Verify location is claimed by business
        claim_sql = """
            SELECT id, status
            FROM business_location_claims
            WHERE location_id = $1 AND business_account_id = $2
        """
        claim_rows = await fetch(claim_sql, location_id, business_account_id)
        
        if not claim_rows or claim_rows[0]["status"] != "approved":
            raise ValueError("Location not claimed or not approved for this business account")
        
        # Calculate price based on promotion type
        if promotion_type == "both":
            # Sum of trending and feed prices
            trending_price = get_promotion_price("location_trending", duration_days)
            feed_price = get_promotion_price("location_feed", duration_days)
            total_price = trending_price + feed_price
        elif promotion_type == "trending":
            total_price = get_promotion_price("location_trending", duration_days)
        elif promotion_type == "feed":
            total_price = get_promotion_price("location_feed", duration_days)
        else:
            raise ValueError(f"Invalid promotion_type: {promotion_type}")
        
        # Calculate dates
        starts_at, ends_at = calculate_promotion_dates(duration_days)
        
        # Insert promotion record
        insert_sql = """
            INSERT INTO promoted_locations (
                location_id,
                business_account_id,
                promotion_type,
                starts_at,
                ends_at,
                status
            )
            VALUES ($1, $2, $3, $4, $5, 'pending')
            RETURNING id, location_id, business_account_id, promotion_type,
                      starts_at, ends_at, status, created_at
        """
        rows = await fetch(
            insert_sql,
            location_id,
            business_account_id,
            promotion_type,
            starts_at,
            ends_at,
        )
        
        if not rows:
            raise ValueError("Failed to create promotion")
        
        promotion = dict(rows[0])
        promotion["price_cents"] = total_price
        promotion["duration_days"] = duration_days
        
        logger.info(
            "location_promotion_created",
            promotion_id=promotion["id"],
            location_id=location_id,
            business_account_id=business_account_id,
            promotion_type=promotion_type,
            price_cents=total_price,
        )
        
        return promotion
    
    async def create_news_promotion(
        self,
        business_account_id: int,
        title: str,
        content: str,
        url: Optional[str],
        image_url: Optional[str],
        duration_days: int,
    ) -> Dict[str, Any]:
        """
        Create a news promotion request.
        
        Args:
            business_account_id: Business account ID
            title: News title
            content: News content
            url: Optional URL
            image_url: Optional image URL
            duration_days: Duration in days (7, 14, or 30)
            
        Returns:
            Dict with promotion details including price
        """
        # Calculate price
        total_price = get_promotion_price("news", duration_days)
        
        # Calculate dates
        starts_at, ends_at = calculate_promotion_dates(duration_days)
        
        # Insert promotion record
        insert_sql = """
            INSERT INTO promoted_news (
                business_account_id,
                title,
                content,
                url,
                image_url,
                starts_at,
                ends_at,
                status
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending')
            RETURNING id, business_account_id, title, content, url, image_url,
                      starts_at, ends_at, status, created_at
        """
        rows = await fetch(
            insert_sql,
            business_account_id,
            title,
            content,
            url,
            image_url,
            starts_at,
            ends_at,
        )
        
        if not rows:
            raise ValueError("Failed to create promotion")
        
        promotion = dict(rows[0])
        promotion["price_cents"] = total_price
        promotion["duration_days"] = duration_days
        
        logger.info(
            "news_promotion_created",
            promotion_id=promotion["id"],
            business_account_id=business_account_id,
            price_cents=total_price,
        )
        
        return promotion
    
    async def update_promotion_payment_intent(
        self,
        promotion_type: str,  # 'location' or 'news'
        promotion_id: int,
        payment_intent_id: str,
    ) -> None:
        """
        Update promotion with Stripe payment intent ID.
        
        Args:
            promotion_type: 'location' or 'news'
            promotion_id: Promotion ID
            payment_intent_id: Stripe payment intent ID
        """
        if promotion_type == "location":
            update_sql = """
                UPDATE promoted_locations
                SET stripe_payment_intent_id = $1, updated_at = now()
                WHERE id = $2
            """
        elif promotion_type == "news":
            update_sql = """
                UPDATE promoted_news
                SET stripe_payment_intent_id = $1, updated_at = now()
                WHERE id = $2
            """
        else:
            raise ValueError(f"Invalid promotion_type: {promotion_type}")
        
        await execute(update_sql, payment_intent_id, promotion_id)
    
    async def activate_promotion(
        self,
        promotion_type: str,  # 'location' or 'news'
        promotion_id: int,
    ) -> None:
        """
        Activate a promotion after payment succeeds.
        
        Args:
            promotion_type: 'location' or 'news'
            promotion_id: Promotion ID
        """
        if promotion_type == "location":
            update_sql = """
                UPDATE promoted_locations
                SET status = 'active', updated_at = now()
                WHERE id = $1 AND status = 'pending'
            """
        elif promotion_type == "news":
            update_sql = """
                UPDATE promoted_news
                SET status = 'active', updated_at = now()
                WHERE id = $1 AND status = 'pending'
            """
        else:
            raise ValueError(f"Invalid promotion_type: {promotion_type}")
        
        await execute(update_sql, promotion_id)
        
        logger.info(
            "promotion_activated",
            promotion_type=promotion_type,
            promotion_id=promotion_id,
        )
    
    async def get_active_location_promotions(
        self,
        location_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get active location promotions.
        
        Args:
            location_ids: Optional list of location IDs to filter by
            
        Returns:
            List of active promotion records
        """
        now = datetime.now(timezone.utc)
        
        conditions = [
            "status = 'active'",
            "starts_at <= $1",
            "ends_at > $1",
        ]
        params = [now]
        
        if location_ids:
            # Use ANY for array matching
            conditions.append("location_id = ANY($2)")
            params.append(location_ids)
        
        where_clause = " AND ".join(conditions)
        
        sql = f"""
            SELECT 
                id,
                location_id,
                business_account_id,
                promotion_type,
                starts_at,
                ends_at
            FROM promoted_locations
            WHERE {where_clause}
        """
        
        rows = await fetch(sql, *params)
        return [dict(row) for row in rows]
    
    async def get_active_news_promotions(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get active news promotions.
        
        Args:
            limit: Maximum number of promotions to return
            
        Returns:
            List of active promotion records
        """
        now = datetime.now(timezone.utc)
        
        sql = """
            SELECT 
                id,
                business_account_id,
                title,
                content,
                url,
                image_url,
                starts_at,
                ends_at
            FROM promoted_news
            WHERE status = 'active'
              AND starts_at <= $1
              AND ends_at > $1
            ORDER BY starts_at DESC
            LIMIT $2
        """
        
        rows = await fetch(sql, now, limit)
        return [dict(row) for row in rows]
    
    async def list_location_promotions(
        self,
        business_account_id: int,
    ) -> List[Dict[str, Any]]:
        """
        List all location promotions for a business account.
        
        Args:
            business_account_id: Business account ID
            
        Returns:
            List of promotion records
        """
        sql = """
            SELECT 
                id,
                location_id,
                promotion_type,
                starts_at,
                ends_at,
                status,
                stripe_payment_intent_id,
                created_at
            FROM promoted_locations
            WHERE business_account_id = $1
            ORDER BY created_at DESC
        """
        
        rows = await fetch(sql, business_account_id)
        return [dict(row) for row in rows]
    
    async def list_news_promotions(
        self,
        business_account_id: int,
    ) -> List[Dict[str, Any]]:
        """
        List all news promotions for a business account.
        
        Args:
            business_account_id: Business account ID
            
        Returns:
            List of promotion records
        """
        sql = """
            SELECT 
                id,
                title,
                content,
                url,
                image_url,
                starts_at,
                ends_at,
                status,
                stripe_payment_intent_id,
                created_at
            FROM promoted_news
            WHERE business_account_id = $1
            ORDER BY created_at DESC
        """
        
        rows = await fetch(sql, business_account_id)
        return [dict(row) for row in rows]
    
    async def cancel_promotion(
        self,
        promotion_type: str,  # 'location' or 'news'
        promotion_id: int,
        business_account_id: int,
    ) -> bool:
        """
        Cancel a promotion (only if pending or not started).
        
        Args:
            promotion_type: 'location' or 'news'
            promotion_id: Promotion ID
            business_account_id: Business account ID (for verification)
            
        Returns:
            True if cancelled, False if not cancellable
        """
        now = datetime.now(timezone.utc)
        
        if promotion_type == "location":
            update_sql = """
                UPDATE promoted_locations
                SET status = 'cancelled', updated_at = now()
                WHERE id = $1
                  AND business_account_id = $2
                  AND status IN ('pending', 'active')
                  AND starts_at > $3
            """
        elif promotion_type == "news":
            update_sql = """
                UPDATE promoted_news
                SET status = 'cancelled', updated_at = now()
                WHERE id = $1
                  AND business_account_id = $2
                  AND status IN ('pending', 'active')
                  AND starts_at > $3
            """
        else:
            raise ValueError(f"Invalid promotion_type: {promotion_type}")
        
        result = await execute(update_sql, promotion_id, business_account_id, now)
        
        if result == "UPDATE 1":
            logger.info(
                "promotion_cancelled",
                promotion_type=promotion_type,
                promotion_id=promotion_id,
            )
            return True
        
        return False
    
    async def expire_promotions(self) -> Dict[str, int]:
        """
        Mark expired promotions as expired.
        Called by worker.
        
        Returns:
            Dict with counts of expired promotions
        """
        now = datetime.now(timezone.utc)
        
        # Expire location promotions
        location_sql = """
            UPDATE promoted_locations
            SET status = 'expired', updated_at = now()
            WHERE status = 'active'
              AND ends_at <= $1
        """
        await execute(location_sql, now)
        
        # Expire news promotions
        news_sql = """
            UPDATE promoted_news
            SET status = 'expired', updated_at = now()
            WHERE status = 'active'
              AND ends_at <= $1
        """
        await execute(news_sql, now)
        
        # Get counts
        location_count_sql = """
            SELECT COUNT(*) as count
            FROM promoted_locations
            WHERE status = 'expired'
              AND updated_at >= $1 - INTERVAL '1 minute'
        """
        news_count_sql = """
            SELECT COUNT(*) as count
            FROM promoted_news
            WHERE status = 'expired'
              AND updated_at >= $1 - INTERVAL '1 minute'
        """
        
        location_rows = await fetch(location_count_sql, now)
        news_rows = await fetch(news_count_sql, now)
        
        location_count = location_rows[0]["count"] if location_rows else 0
        news_count = news_rows[0]["count"] if news_rows else 0
        
        logger.info(
            "promotions_expired",
            location_count=location_count,
            news_count=news_count,
        )
        
        return {
            "location_count": location_count,
            "news_count": news_count,
        }


# Singleton instance
_promotion_service: Optional[PromotionService] = None


def get_promotion_service() -> PromotionService:
    """Get or create PromotionService singleton."""
    global _promotion_service
    if _promotion_service is None:
        _promotion_service = PromotionService()
    return _promotion_service

















