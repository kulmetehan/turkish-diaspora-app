# Backend/services/business_analytics_service.py
from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from services.db_service import fetch, fetchrow
from app.core.logging import get_logger

logger = get_logger()


class BusinessAnalyticsService:
    """
    Service for business analytics and metrics.
    """
    
    async def get_overview(
        self,
        business_account_id: int,
        period_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Get overview metrics for a business account.
        
        Args:
            business_account_id: Business account ID
            period_days: Number of days to look back
            
        Returns:
            Dict with overview metrics
        """
        # Get claimed locations
        locations_sql = """
            SELECT location_id, status
            FROM business_location_claims
            WHERE business_account_id = $1
        """
        location_rows = await fetch(locations_sql, business_account_id)
        
        approved_location_ids = [
            row["location_id"] for row in location_rows
            if row["status"] == "approved"
        ]
        
        if not approved_location_ids:
            return {
                "total_locations": 0,
                "approved_locations": 0,
                "total_views": 0,
                "total_check_ins": 0,
                "total_reactions": 0,
                "total_notes": 0,
                "total_favorites": 0,
                "trending_locations": 0,
                "period_days": period_days,
            }
        
        # Calculate period
        period_start = datetime.now() - timedelta(days=period_days)
        
        # Get activity metrics from activity_stream
        activity_sql = """
            SELECT 
                activity_type,
                COUNT(*) as count
            FROM activity_stream
            WHERE location_id = ANY($1::bigint[])
                AND created_at >= $2
            GROUP BY activity_type
        """
        activity_rows = await fetch(activity_sql, approved_location_ids, period_start)
        
        # Aggregate by activity type
        metrics = {
            "check_ins": 0,
            "reactions": 0,
            "notes": 0,
            "favorites": 0,
        }
        
        for row in activity_rows:
            activity_type = row["activity_type"]
            count = row["count"]
            if activity_type in metrics:
                metrics[activity_type] = count
        
        # Get trending locations count (if trending_locations table exists)
        trending_sql = """
            SELECT COUNT(DISTINCT location_id) as count
            FROM trending_locations
            WHERE location_id = ANY($1::bigint[])
                AND created_at >= $2
        """
        try:
            trending_rows = await fetch(trending_sql, approved_location_ids, period_start)
            trending_count = trending_rows[0]["count"] if trending_rows else 0
        except Exception:
            # trending_locations table might not exist
            trending_count = 0
        
        return {
            "total_locations": len(location_rows),
            "approved_locations": len(approved_location_ids),
            "total_views": 0,  # Views would need separate tracking
            "total_check_ins": metrics["check_ins"],
            "total_reactions": metrics["reactions"],
            "total_notes": metrics["notes"],
            "total_favorites": metrics["favorites"],
            "trending_locations": trending_count,
            "period_days": period_days,
        }
    
    async def get_location_analytics(
        self,
        business_account_id: int,
        location_id: int,
        period_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Get detailed analytics for a specific location.
        
        Args:
            business_account_id: Business account ID
            location_id: Location ID
            period_days: Number of days to look back
            
        Returns:
            Dict with location-specific metrics
        """
        # Verify location belongs to business account
        claim_sql = """
            SELECT status
            FROM business_location_claims
            WHERE business_account_id = $1 AND location_id = $2
        """
        claim_rows = await fetch(claim_sql, business_account_id, location_id)
        
        if not claim_rows:
            raise ValueError("Location not found or not claimed by this business account")
        
        # Calculate period
        period_start = datetime.now() - timedelta(days=period_days)
        
        # Get activity metrics
        activity_sql = """
            SELECT 
                activity_type,
                COUNT(*) as count
            FROM activity_stream
            WHERE location_id = $1
                AND created_at >= $2
            GROUP BY activity_type
        """
        activity_rows = await fetch(activity_sql, location_id, period_start)
        
        metrics = {
            "check_ins": 0,
            "reactions": 0,
            "notes": 0,
            "favorites": 0,
        }
        
        for row in activity_rows:
            activity_type = row["activity_type"]
            count = row["count"]
            if activity_type in metrics:
                metrics[activity_type] = count
        
        # Get trending status
        trending_sql = """
            SELECT trending_score, created_at
            FROM trending_locations
            WHERE location_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        """
        try:
            trending_rows = await fetch(trending_sql, location_id)
            is_trending = len(trending_rows) > 0
            trending_score = trending_rows[0]["trending_score"] if trending_rows else None
        except Exception:
            is_trending = False
            trending_score = None
        
        return {
            "location_id": location_id,
            "views": 0,  # Would need separate tracking
            "check_ins": metrics["check_ins"],
            "reactions": metrics["reactions"],
            "notes": metrics["notes"],
            "favorites": metrics["favorites"],
            "trending_score": trending_score,
            "is_trending": is_trending,
            "period_days": period_days,
        }
    
    async def get_engagement_metrics(
        self,
        business_account_id: int,
        period_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Get engagement metrics across all locations.
        
        Args:
            business_account_id: Business account ID
            period_days: Number of days to look back
            
        Returns:
            Dict with engagement metrics
        """
        # Get approved locations
        locations_sql = """
            SELECT location_id
            FROM business_location_claims
            WHERE business_account_id = $1 AND status = 'approved'
        """
        location_rows = await fetch(locations_sql, business_account_id)
        location_ids = [row["location_id"] for row in location_rows]
        
        if not location_ids:
            return {
                "total_engagement": 0,
                "engagement_rate": 0.0,
                "top_locations": [],
                "activity_timeline": [],
            }
        
        # Calculate period
        period_start = datetime.now() - timedelta(days=period_days)
        
        # Get total engagement
        engagement_sql = """
            SELECT 
                COUNT(*) as total_engagement
            FROM activity_stream
            WHERE location_id = ANY($1::bigint[])
                AND created_at >= $2
        """
        engagement_rows = await fetch(engagement_sql, location_ids, period_start)
        total_engagement = engagement_rows[0]["total_engagement"] if engagement_rows else 0
        
        # Get top locations by engagement
        top_locations_sql = """
            SELECT 
                location_id,
                COUNT(*) as engagement_count
            FROM activity_stream
            WHERE location_id = ANY($1::bigint[])
                AND created_at >= $2
            GROUP BY location_id
            ORDER BY engagement_count DESC
            LIMIT 10
        """
        top_locations_rows = await fetch(top_locations_sql, location_ids, period_start)
        top_locations = [
            {
                "location_id": row["location_id"],
                "engagement_count": row["engagement_count"],
            }
            for row in top_locations_rows
        ]
        
        # Get activity timeline (daily aggregation)
        timeline_sql = """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count
            FROM activity_stream
            WHERE location_id = ANY($1::bigint[])
                AND created_at >= $2
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """
        timeline_rows = await fetch(timeline_sql, location_ids, period_start)
        activity_timeline = [
            {
                "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                "count": row["count"],
            }
            for row in timeline_rows
        ]
        
        # Calculate engagement rate (would need views data)
        engagement_rate = 0.0  # Placeholder
        
        return {
            "total_engagement": total_engagement,
            "engagement_rate": engagement_rate,
            "top_locations": top_locations,
            "activity_timeline": activity_timeline,
        }
    
    async def get_trending_metrics(
        self,
        business_account_id: int,
    ) -> Dict[str, Any]:
        """
        Get trending statistics for claimed locations.
        
        Args:
            business_account_id: Business account ID
            
        Returns:
            Dict with trending metrics
        """
        # Get approved locations
        locations_sql = """
            SELECT location_id
            FROM business_location_claims
            WHERE business_account_id = $1 AND status = 'approved'
        """
        location_rows = await fetch(locations_sql, business_account_id)
        location_ids = [row["location_id"] for row in location_rows]
        
        if not location_ids:
            return {
                "trending_locations": [],
                "trending_scores": [],
            }
        
        # Get trending locations
        trending_sql = """
            SELECT 
                location_id,
                trending_score,
                created_at
            FROM trending_locations
            WHERE location_id = ANY($1::bigint[])
            ORDER BY trending_score DESC, created_at DESC
        """
        try:
            trending_rows = await fetch(trending_sql, location_ids)
            trending_locations = [
                {
                    "location_id": row["location_id"],
                    "trending_score": float(row["trending_score"]) if row["trending_score"] else 0.0,
                    "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
                }
                for row in trending_rows
            ]
        except Exception:
            trending_locations = []
        
        return {
            "trending_locations": trending_locations,
            "trending_scores": [loc["trending_score"] for loc in trending_locations],
        }


# Singleton instance
_business_analytics_service: Optional[BusinessAnalyticsService] = None


def get_business_analytics_service() -> BusinessAnalyticsService:
    """Get or create BusinessAnalyticsService singleton."""
    global _business_analytics_service
    if _business_analytics_service is None:
        _business_analytics_service = BusinessAnalyticsService()
    return _business_analytics_service








