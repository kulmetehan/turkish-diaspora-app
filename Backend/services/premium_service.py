# Backend/services/premium_service.py
from __future__ import annotations

from typing import Dict, Any, List, Optional

from services.db_service import fetch
from app.core.logging import get_logger

logger = get_logger()


class PremiumService:
    """
    Service for premium feature management and access control.
    """
    
    PREMIUM_FEATURES = {
        "basic": [],
        "premium": [
            "enhanced_location_info",
            "advanced_analytics",
            "priority_support",
        ],
        "pro": [
            "enhanced_location_info",
            "advanced_analytics",
            "priority_support",
            "api_access",
            "custom_branding",
        ],
    }
    
    async def get_features_for_tier(self, tier: str) -> List[str]:
        """
        Get list of features available for a subscription tier.
        
        Args:
            tier: Subscription tier ('basic', 'premium', 'pro')
            
        Returns:
            List of feature keys
        """
        return self.PREMIUM_FEATURES.get(tier, [])
    
    async def has_feature(
        self,
        business_account_id: int,
        feature_key: str,
    ) -> bool:
        """
        Check if a business account has access to a specific feature.
        
        Args:
            business_account_id: Business account ID
            feature_key: Feature key to check
            
        Returns:
            True if feature is enabled
        """
        # Get subscription tier
        account_sql = """
            SELECT subscription_tier, subscription_status
            FROM business_accounts
            WHERE id = $1
        """
        account_rows = await fetch(account_sql, business_account_id)
        
        if not account_rows:
            return False
        
        account = account_rows[0]
        tier = account["subscription_tier"]
        status = account["subscription_status"]
        
        # Check if subscription is active
        if status != "active":
            return False
        
        # Check if feature is in tier
        tier_features = await self.get_features_for_tier(tier)
        if feature_key not in tier_features:
            return False
        
        # Check feature flag (may be disabled even if in tier)
        feature_sql = """
            SELECT is_enabled
            FROM premium_features
            WHERE business_account_id = $1 AND feature_key = $2
        """
        feature_rows = await fetch(feature_sql, business_account_id, feature_key)
        
        if feature_rows:
            return feature_rows[0]["is_enabled"]
        
        # Default to enabled if feature is in tier and no flag exists
        return True
    
    async def get_subscription_status(
        self,
        business_account_id: int,
    ) -> Dict[str, Any]:
        """
        Get current subscription status for a business account.
        
        Args:
            business_account_id: Business account ID
            
        Returns:
            Dict with subscription status
        """
        account_sql = """
            SELECT 
                subscription_tier,
                subscription_status,
                stripe_subscription_id,
                current_period_end
            FROM business_accounts
            WHERE id = $1
        """
        account_rows = await fetch(account_sql, business_account_id)
        
        if not account_rows:
            raise ValueError("Business account not found")
        
        account = account_rows[0]
        
        # Get enabled features
        features_sql = """
            SELECT feature_key
            FROM premium_features
            WHERE business_account_id = $1 AND is_enabled = true
        """
        features_rows = await fetch(features_sql, business_account_id)
        enabled_features = [row["feature_key"] for row in features_rows]
        
        return {
            "tier": account["subscription_tier"],
            "status": account["subscription_status"],
            "stripe_subscription_id": account["stripe_subscription_id"],
            "current_period_end": account["current_period_end"].isoformat() if account["current_period_end"] else None,
            "enabled_features": enabled_features,
        }


# Singleton instance
_premium_service: Optional[PremiumService] = None


def get_premium_service() -> PremiumService:
    """Get or create PremiumService singleton."""
    global _premium_service
    if _premium_service is None:
        _premium_service = PremiumService()
    return _premium_service



