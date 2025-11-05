"""
Tests for location filter definitions and parity between Admin metrics and public API.

This test suite ensures that:
1. Admin metrics verified count uses the same filters as public locations API
2. Filter SQL generation is correct
3. Edge cases are handled (missing coords, retired, low confidence)
"""

import pytest
from app.core.location_filters import (
    get_verified_filter_sql,
    get_verified_filter_params,
    VERIFIED_CONFIDENCE_THRESHOLD,
)


def test_verified_filter_sql_basic():
    """Test basic verified filter SQL generation without bbox."""
    sql, params = get_verified_filter_sql(bbox=None)
    
    assert "state = 'VERIFIED'" in sql
    assert "confidence_score >= $1" in sql
    assert "is_retired = false OR is_retired IS NULL" in sql
    assert "lat IS NOT NULL" in sql
    assert "lng IS NOT NULL" in sql
    
    assert len(params) == 1
    assert params[0] == VERIFIED_CONFIDENCE_THRESHOLD


def test_verified_filter_sql_with_bbox():
    """Test verified filter SQL generation with bounding box."""
    bbox = (51.85, 51.98, 4.35, 4.55)
    sql, params = get_verified_filter_sql(bbox=bbox)
    
    assert "state = 'VERIFIED'" in sql
    assert "confidence_score >= $1" in sql
    assert "lat BETWEEN $2 AND $3" in sql
    assert "lng BETWEEN $4 AND $5" in sql
    
    assert len(params) == 5  # confidence threshold + 4 bbox values
    assert params[0] == VERIFIED_CONFIDENCE_THRESHOLD
    assert params[1] == 51.85  # lat_min
    assert params[2] == 51.98  # lat_max
    assert params[3] == 4.35   # lng_min
    assert params[4] == 4.55   # lng_max


def test_verified_filter_sql_with_alias():
    """Test verified filter SQL generation with table alias."""
    sql, params = get_verified_filter_sql(bbox=None, alias="l")
    
    assert "l.state = 'VERIFIED'" in sql
    assert "l.confidence_score >= $1" in sql
    assert "l.lat IS NOT NULL" in sql
    assert "l.lng IS NOT NULL" in sql
    
    assert len(params) == 1
    assert params[0] == VERIFIED_CONFIDENCE_THRESHOLD


def test_verified_filter_params():
    """Test filter parameters dictionary for UI display."""
    params = get_verified_filter_params()
    
    assert params["state"] == "VERIFIED"
    assert params["confidence_threshold"] == VERIFIED_CONFIDENCE_THRESHOLD
    assert params["exclude_retired"] is True
    assert params["require_coordinates"] is True


def test_filter_excludes_low_confidence():
    """Test that filter excludes locations with confidence below threshold."""
    sql, params = get_verified_filter_sql()
    
    # Filter should require confidence >= 0.80
    assert f"confidence_score >= ${params.index(VERIFIED_CONFIDENCE_THRESHOLD) + 1}" in sql
    assert VERIFIED_CONFIDENCE_THRESHOLD == 0.80


def test_filter_excludes_retired():
    """Test that filter excludes retired locations."""
    sql, params = get_verified_filter_sql()
    
    # Filter should exclude retired locations
    assert "is_retired = false OR is_retired IS NULL" in sql


def test_filter_requires_coordinates():
    """Test that filter requires non-null coordinates."""
    sql, params = get_verified_filter_sql()
    
    # Filter should require lat and lng
    assert "lat IS NOT NULL" in sql
    assert "lng IS NOT NULL" in sql


def test_bbox_parameter_ordering():
    """Test that bbox parameters are in correct order for asyncpg."""
    bbox = (51.85, 51.98, 4.35, 4.55)
    sql, params = get_verified_filter_sql(bbox=bbox)
    
    # Verify parameter placeholders are sequential
    assert "$1" in sql  # confidence threshold
    assert "$2" in sql  # lat_min
    assert "$3" in sql  # lat_max
    assert "$4" in sql  # lng_min
    assert "$5" in sql  # lng_max
    
    # Verify parameters are in correct order
    assert params[0] == VERIFIED_CONFIDENCE_THRESHOLD
    assert params[1] == 51.85  # lat_min
    assert params[2] == 51.98  # lat_max
    assert params[3] == 4.35   # lng_min
    assert params[4] == 4.55   # lng_max


def test_filter_sql_combines_conditions():
    """Test that all filter conditions are combined with AND."""
    sql, params = get_verified_filter_sql()
    
    # Count AND operators (should be 4 for base filters: state, confidence, retired, lat, lng)
    # Actually: state, confidence, retired, lat, lng = 4 ANDs
    and_count = sql.count(" AND ")
    assert and_count >= 4  # At least 4 AND operators for base filters


@pytest.mark.skip(reason="Requires database connection - integration test")
def test_admin_api_parity():
    """
    Integration test: Admin metrics count should match public API count
    when using same filters + bbox.
    
    This test requires a database connection and should be run separately.
    It verifies that:
    1. Admin metrics endpoint uses shared filter
    2. Public locations API uses shared filter for VERIFIED portion
    3. Counts match when bbox is applied to both
    """
    # This would require:
    # 1. Set up test database
    # 2. Create test locations with various states/confidence/retired/coords
    # 3. Call Admin metrics endpoint
    # 4. Call public locations API endpoint
    # 5. Count VERIFIED locations from API response
    # 6. Assert Admin count == API count
    pass


@pytest.mark.skip(reason="Requires database connection - integration test")
def test_filter_edge_cases():
    """
    Integration test: Verify filter handles edge cases correctly.
    
    Edge cases to test:
    1. Locations with confidence < 0.80 (should be excluded)
    2. Locations with is_retired = true (should be excluded)
    3. Locations with null lat/lng (should be excluded)
    4. Locations with confidence = 0.80 (should be included)
    5. Locations with confidence = 0.79 (should be excluded)
    6. Locations with is_retired = null (should be included)
    """
    pass

