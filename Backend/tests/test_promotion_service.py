# Backend/tests/test_promotion_service.py
"""
Tests for promotion service.
"""
import pytest
from datetime import datetime, timedelta, timezone
from services.promotion_service import (
    get_promotion_service,
    get_promotion_price,
    calculate_promotion_dates,
)


def test_get_promotion_price_defaults():
    """Test default pricing when env vars not set."""
    # Test location trending
    assert get_promotion_price("location_trending", 7) == 5000
    assert get_promotion_price("location_trending", 14) == 9000
    assert get_promotion_price("location_trending", 30) == 15000
    
    # Test location feed
    assert get_promotion_price("location_feed", 7) == 3000
    assert get_promotion_price("location_feed", 14) == 5500
    assert get_promotion_price("location_feed", 30) == 9000
    
    # Test news
    assert get_promotion_price("news", 7) == 2000
    assert get_promotion_price("news", 14) == 3500
    assert get_promotion_price("news", 30) == 5500


def test_calculate_promotion_dates():
    """Test promotion date calculation."""
    starts_at, ends_at = calculate_promotion_dates(7)
    
    assert isinstance(starts_at, datetime)
    assert isinstance(ends_at, datetime)
    assert ends_at > starts_at
    
    duration = ends_at - starts_at
    assert duration.days == 7


@pytest.mark.asyncio
async def test_create_location_promotion_invalid_location():
    """Test that creating promotion for unclaimed location fails."""
    service = get_promotion_service()
    
    with pytest.raises(ValueError, match="Location not claimed"):
        await service.create_location_promotion(
            business_account_id=1,
            location_id=999999,  # Non-existent location
            promotion_type="trending",
            duration_days=7,
        )


@pytest.mark.asyncio
async def test_create_news_promotion():
    """Test creating news promotion."""
    service = get_promotion_service()
    
    promotion = await service.create_news_promotion(
        business_account_id=1,
        title="Test News",
        content="Test content",
        url=None,
        image_url=None,
        duration_days=7,
    )
    
    assert promotion["id"] > 0
    assert promotion["title"] == "Test News"
    assert promotion["status"] == "pending"
    assert promotion["price_cents"] == 2000  # Default price for 7 days














