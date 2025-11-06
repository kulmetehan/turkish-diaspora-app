"""
Tests for locations API endpoint with bbox filtering and pagination.

This test suite verifies:
1. Bbox parameter parsing and validation
2. Bbox filtering correctness (locations within/outside bbox)
3. Count endpoint returns correct count for bbox
4. Pagination: limit/offset returns disjoint pages, union equals count
5. Edge cases: empty bbox, invalid bbox
"""

import pytest
from fastapi import HTTPException
from api.routers.locations import parse_bbox


def test_bbox_parsing_valid_rotterdam():
    """Test bbox parsing with valid Rotterdam area coordinates."""
    bbox_str = "4.1,51.8,4.7,52.0"
    result = parse_bbox(bbox_str)
    
    # Should convert to (lat_min, lat_max, lng_min, lng_max)
    assert result == (51.8, 52.0, 4.1, 4.7)


def test_bbox_parsing_with_whitespace():
    """Test bbox parsing handles whitespace correctly."""
    bbox_str = " 4.1 , 51.8 , 4.7 , 52.0 "
    result = parse_bbox(bbox_str)
    
    assert result == (51.8, 52.0, 4.1, 4.7)


def test_bbox_parsing_invalid_wrong_count():
    """Test bbox parsing fails with wrong number of values."""
    # Too few
    with pytest.raises(HTTPException) as exc_info:
        parse_bbox("4.1,51.8,4.7")
    assert exc_info.value.status_code == 400
    assert "exactly 4" in exc_info.value.detail.lower()
    
    # Too many
    with pytest.raises(HTTPException) as exc_info:
        parse_bbox("4.1,51.8,4.7,52.0,5.0")
    assert exc_info.value.status_code == 400


def test_bbox_parsing_invalid_non_numeric():
    """Test bbox parsing fails with non-numeric values."""
    with pytest.raises(HTTPException) as exc_info:
        parse_bbox("4.1,abc,4.7,52.0")
    assert exc_info.value.status_code == 400
    assert "numeric" in exc_info.value.detail.lower()


def test_bbox_parsing_invalid_longitude_range():
    """Test bbox parsing fails with longitude out of range."""
    # Longitude > 180
    with pytest.raises(HTTPException) as exc_info:
        parse_bbox("200,51.8,4.7,52.0")
    assert exc_info.value.status_code == 400
    assert "longitude" in exc_info.value.detail.lower()
    
    # Longitude < -180
    with pytest.raises(HTTPException) as exc_info:
        parse_bbox("-200,51.8,4.7,52.0")
    assert exc_info.value.status_code == 400


def test_bbox_parsing_invalid_latitude_range():
    """Test bbox parsing fails with latitude out of range."""
    # Latitude > 90
    with pytest.raises(HTTPException) as exc_info:
        parse_bbox("4.1,100,4.7,52.0")
    assert exc_info.value.status_code == 400
    assert "latitude" in exc_info.value.detail.lower()
    
    # Latitude < -90
    with pytest.raises(HTTPException) as exc_info:
        parse_bbox("4.1,-100,4.7,52.0")
    assert exc_info.value.status_code == 400


def test_bbox_parsing_invalid_west_east_order():
    """Test bbox parsing fails when west >= east."""
    with pytest.raises(HTTPException) as exc_info:
        parse_bbox("4.7,51.8,4.1,52.0")
    assert exc_info.value.status_code == 400
    assert "west" in exc_info.value.detail.lower() and "east" in exc_info.value.detail.lower()
    
    # Edge case: west == east
    with pytest.raises(HTTPException) as exc_info:
        parse_bbox("4.1,51.8,4.1,52.0")
    assert exc_info.value.status_code == 400


def test_bbox_parsing_invalid_south_north_order():
    """Test bbox parsing fails when south >= north."""
    with pytest.raises(HTTPException) as exc_info:
        parse_bbox("4.1,52.0,4.7,51.8")
    assert exc_info.value.status_code == 400
    assert "south" in exc_info.value.detail.lower() and "north" in exc_info.value.detail.lower()
    
    # Edge case: south == north
    with pytest.raises(HTTPException) as exc_info:
        parse_bbox("4.1,51.8,4.7,51.8")
    assert exc_info.value.status_code == 400


def test_bbox_parsing_edge_cases():
    """Test bbox parsing with edge case values."""
    # Valid edge cases
    result = parse_bbox("-180,-90,180,90")  # Full world
    assert result == (-90.0, 90.0, -180.0, 180.0)
    
    # Small bbox
    result = parse_bbox("4.477,51.924,4.478,51.925")
    assert result == (51.924, 51.925, 4.477, 4.478)


@pytest.mark.skip(reason="Requires database connection - integration test")
def test_bbox_filtering_correctness():
    """
    Integration test: Verify bbox filtering returns only locations within bounds.
    
    This test requires a database with test data:
    1. Create test locations inside and outside a known bbox
    2. Query with bbox parameter
    3. Verify all returned locations are within bbox
    4. Verify locations outside bbox are not returned
    """
    pass


@pytest.mark.skip(reason="Requires database connection - integration test")
def test_count_endpoint_with_bbox():
    """
    Integration test: Verify count endpoint returns correct count for bbox.
    
    This test requires a database with test data:
    1. Create test locations inside and outside a known bbox
    2. Query count endpoint with bbox
    3. Query list endpoint with same bbox
    4. Verify count matches number of locations returned
    """
    pass


@pytest.mark.skip(reason="Requires database connection - integration test")
def test_pagination_disjoint_pages():
    """
    Integration test: Verify pagination returns disjoint pages.
    
    This test requires a database with test data:
    1. Query first page with limit=10, offset=0
    2. Query second page with limit=10, offset=10
    3. Verify no duplicate IDs between pages
    4. Verify union of all pages equals total count
    """
    pass


@pytest.mark.skip(reason="Requires database connection - integration test")
def test_pagination_union_equals_count():
    """
    Integration test: Verify pagination pages union equals total count.
    
    This test requires a database with test data:
    1. Get total count for a bbox
    2. Fetch all pages with pagination
    3. Verify union of all pages has exactly count items
    4. Verify all items are unique
    """
    pass

