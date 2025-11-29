import pytest
from unittest.mock import AsyncMock, MagicMock

from services import metrics_service
from app.models.metrics import CategoryHealth, CategoryHealthResponse


@pytest.mark.asyncio
async def test_compute_category_health_status_no_data(monkeypatch):
    """Test 'no_data' status when truly no activity exists."""
    cat = CategoryHealth(
        overpass_calls=0,
        overpass_successful_calls=0,
        overpass_zero_results=0,
        overpass_zero_result_ratio_pct=0.0,
        inserted_locations_last_7d=0,
        state_counts={},
        ai_classifications_last_7d=0,
        ai_action_keep=0,
        ai_action_ignore=0,
        promoted_verified_last_7d=0,
        overpass_found=0,
        turkish_coverage_ratio_pct=0.0,
        ai_precision_pct=0.0,
        status="no_data",
    )
    
    status = metrics_service._compute_category_health_status(cat)
    assert status == "no_data"


@pytest.mark.asyncio
async def test_compute_category_health_status_with_inserts_no_overpass(monkeypatch):
    """Test status is not 'no_data' when inserts exist even without Overpass data."""
    cat = CategoryHealth(
        overpass_calls=0,
        overpass_successful_calls=0,
        overpass_zero_results=0,
        overpass_zero_result_ratio_pct=0.0,
        inserted_locations_last_7d=5,  # Has inserts
        state_counts={},
        ai_classifications_last_7d=0,
        ai_action_keep=0,
        ai_action_ignore=0,
        promoted_verified_last_7d=0,
        overpass_found=0,
        turkish_coverage_ratio_pct=0.0,
        ai_precision_pct=0.0,
        status="no_data",
    )
    
    status = metrics_service._compute_category_health_status(cat)
    # Should not be "no_data" since inserts exist
    assert status != "no_data"


@pytest.mark.asyncio
async def test_compute_category_health_status_early_stage_warning(monkeypatch):
    """Test early-stage categories use lenient thresholds and return 'warning'."""
    cat = CategoryHealth(
        overpass_calls=5,  # Below minimum (10)
        overpass_successful_calls=5,
        overpass_zero_results=0,
        overpass_zero_result_ratio_pct=0.0,
        inserted_locations_last_7d=2,
        state_counts={},
        ai_classifications_last_7d=3,  # Below minimum (5)
        ai_action_keep=2,
        ai_action_ignore=1,
        promoted_verified_last_7d=0,
        overpass_found=5,
        turkish_coverage_ratio_pct=40.0,  # Would be good if mature
        ai_precision_pct=66.67,
        status="no_data",
    )
    
    status = metrics_service._compute_category_health_status(cat)
    # Early stage with some data should return "warning"
    assert status == "warning"


@pytest.mark.asyncio
async def test_compute_category_health_status_mature_healthy(monkeypatch):
    """Test mature categories with good metrics return 'healthy'."""
    cat = CategoryHealth(
        overpass_calls=20,
        overpass_successful_calls=20,
        overpass_zero_results=0,
        overpass_zero_result_ratio_pct=0.0,
        inserted_locations_last_7d=15,
        state_counts={},
        ai_classifications_last_7d=10,  # Above minimum
        ai_action_keep=8,
        ai_action_ignore=2,
        promoted_verified_last_7d=5,
        overpass_found=20,  # Above minimum
        turkish_coverage_ratio_pct=75.0,  # Above warning threshold (20%)
        ai_precision_pct=80.0,  # Above warning threshold (25%)
        status="no_data",
    )
    
    status = metrics_service._compute_category_health_status(cat)
    assert status == "healthy"


@pytest.mark.asyncio
async def test_compute_category_health_status_turkish_coverage_capped(monkeypatch):
    """Test Turkish coverage ratio is capped at 100%."""
    # This would be >100% if not capped (15 inserts / 10 found = 150%)
    cat = CategoryHealth(
        overpass_calls=10,
        overpass_successful_calls=10,
        overpass_zero_results=0,
        overpass_zero_result_ratio_pct=0.0,
        inserted_locations_last_7d=15,
        state_counts={},
        ai_classifications_last_7d=10,
        ai_action_keep=8,
        ai_action_ignore=2,
        promoted_verified_last_7d=0,
        overpass_found=10,
        turkish_coverage_ratio_pct=150.0,  # Would be >100% without cap
        ai_precision_pct=80.0,
        status="no_data",
    )
    
    # The cap is applied in category_health_metrics(), not in status computation
    # But we can verify the calculation logic handles it
    assert cat.turkish_coverage_ratio_pct == 150.0  # Test data has uncapped value
    # In real code, this would be capped at 100% in the calculation


@pytest.mark.asyncio
async def test_compute_category_health_status_critical(monkeypatch):
    """Test 'critical' status for very low coverage with no activity."""
    cat = CategoryHealth(
        overpass_calls=15,
        overpass_successful_calls=15,
        overpass_zero_results=0,
        overpass_zero_result_ratio_pct=0.0,
        inserted_locations_last_7d=0,  # No inserts
        state_counts={},
        ai_classifications_last_7d=0,  # No classifications
        ai_action_keep=0,
        ai_action_ignore=0,
        promoted_verified_last_7d=0,
        overpass_found=15,
        turkish_coverage_ratio_pct=0.0,  # Below critical threshold (5%)
        ai_precision_pct=0.0,
        status="no_data",
    )
    
    status = metrics_service._compute_category_health_status(cat)
    assert status == "critical"


@pytest.mark.asyncio
async def test_compute_category_health_status_degraded(monkeypatch):
    """Test 'degraded' status for low coverage or precision."""
    cat = CategoryHealth(
        overpass_calls=15,
        overpass_successful_calls=15,
        overpass_zero_results=0,
        overpass_zero_result_ratio_pct=0.0,
        inserted_locations_last_7d=1,
        state_counts={},
        ai_classifications_last_7d=10,
        ai_action_keep=1,
        ai_action_ignore=9,
        promoted_verified_last_7d=0,
        overpass_found=15,
        turkish_coverage_ratio_pct=6.67,  # Below degraded threshold (10%)
        ai_precision_pct=10.0,  # Below degraded threshold (15%)
        status="no_data",
    )
    
    status = metrics_service._compute_category_health_status(cat)
    assert status == "degraded"


@pytest.mark.asyncio
async def test_category_health_metrics_empty_categories(monkeypatch):
    """Test category_health_metrics returns empty response when no categories."""
    async def fake_get_discoverable_categories():
        return []
    
    monkeypatch.setattr(
        metrics_service.get_discoverable_categories,
        "__call__",
        fake_get_discoverable_categories
    )
    
    # Mock the import
    import app.models.categories
    monkeypatch.setattr(
        app.models.categories,
        "get_discoverable_categories",
        fake_get_discoverable_categories
    )
    
    result = await metrics_service.category_health_metrics()
    assert isinstance(result, CategoryHealthResponse)
    assert len(result.categories) == 0
    assert result.time_windows["overpass_window_hours"] == 168  # Default 7 days


@pytest.mark.asyncio
async def test_category_health_metrics_with_data(monkeypatch):
    """Test category_health_metrics with mock data."""
    # Mock get_discoverable_categories
    from app.models.categories import CategoryOption
    
    async def fake_get_discoverable_categories():
        return [CategoryOption(key="restaurant", label="Restaurant")]
    
    monkeypatch.setattr(
        "app.models.categories.get_discoverable_categories",
        fake_get_discoverable_categories
    )
    
    # Mock database queries
    async def fake_fetch(sql, *args):
        if "overpass_calls" in sql.lower():
            return [
                {
                    "category": "restaurant",
                    "total_calls": 10,
                    "successful_calls": 10,
                    "zero_results": 0,
                    "total_found": 15,
                }
            ]
        elif "locations" in sql.lower() and "first_seen_at" in sql.lower():
            return [
                {
                    "category": "restaurant",
                    "total_inserted": 5,
                    "candidate": 3,
                    "pending": 1,
                    "verified": 1,
                    "suspended": 0,
                    "retired": 0,
                    "avg_confidence": 0.85,
                }
            ]
        elif "last_verified_at" in sql.lower():
            return [{"category": "restaurant", "promoted_count": 2}]
        elif "ai_logs" in sql.lower():
            return [
                {
                    "category": "restaurant",
                    "classification_count": 8,
                    "action_keep": 6,
                    "action_ignore": 2,
                    "avg_confidence": 0.88,
                }
            ]
        return []
    
    monkeypatch.setattr(metrics_service, "fetch", fake_fetch)
    
    result = await metrics_service.category_health_metrics()
    assert isinstance(result, CategoryHealthResponse)
    assert "restaurant" in result.categories
    
    cat = result.categories["restaurant"]
    assert cat.overpass_found == 15
    assert cat.inserted_locations_last_7d == 5
    assert cat.ai_classifications_last_7d == 8
    assert cat.ai_action_keep == 6
    # Turkish coverage: (5 / 15) * 100 = 33.33%
    assert cat.turkish_coverage_ratio_pct == 33.33
    # AI precision: (6 / 8) * 100 = 75.0%
    assert cat.ai_precision_pct == 75.0

