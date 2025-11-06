"""
Tests for CORS configuration and preflight handling.

This test suite verifies:
1. OPTIONS preflight requests return correct CORS headers
2. GET requests with Origin header return correct CORS headers
3. CORS headers are present for /api/v1/locations and /count endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_options_preflight_locations():
    """Test OPTIONS preflight request for /api/v1/locations returns correct CORS headers."""
    response = client.options(
        "/api/v1/locations",
        headers={
            "Origin": "https://kulmetehan.github.io",
            "Access-Control-Request-Method": "GET",
        },
    )
    
    assert response.status_code == 200 or response.status_code == 204
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "https://kulmetehan.github.io"
    assert "access-control-allow-methods" in response.headers
    assert "GET" in response.headers["access-control-allow-methods"]


def test_get_locations_with_origin():
    """Test GET request to /api/v1/locations with Origin header returns CORS headers."""
    response = client.get(
        "/api/v1/locations?limit=10",
        headers={
            "Origin": "https://kulmetehan.github.io",
        },
    )
    
    # Should return 200 (even if no data) or 503 (if DB unavailable)
    assert response.status_code in [200, 503]
    
    # If successful, should have CORS headers
    if response.status_code == 200:
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "https://kulmetehan.github.io"


def test_get_count_with_origin():
    """Test GET request to /api/v1/locations/count with Origin header returns CORS headers."""
    response = client.get(
        "/api/v1/locations/count",
        headers={
            "Origin": "https://kulmetehan.github.io",
        },
    )
    
    # Should return 200 (even if count is 0) or 503 (if DB unavailable)
    assert response.status_code in [200, 503]
    
    # If successful, should have CORS headers
    if response.status_code == 200:
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "https://kulmetehan.github.io"
        # Should return JSON with count
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)


def test_options_preflight_count():
    """Test OPTIONS preflight request for /api/v1/locations/count returns correct CORS headers."""
    response = client.options(
        "/api/v1/locations/count",
        headers={
            "Origin": "https://kulmetehan.github.io",
            "Access-Control-Request-Method": "GET",
        },
    )
    
    assert response.status_code == 200 or response.status_code == 204
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "https://kulmetehan.github.io"


def test_cors_headers_present_for_allowed_origin():
    """Test that CORS headers are present for allowed origins."""
    allowed_origins = [
        "https://kulmetehan.github.io",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    
    for origin in allowed_origins:
        response = client.get(
            "/api/v1/locations?limit=1",
            headers={"Origin": origin},
        )
        
        if response.status_code == 200:
            assert "access-control-allow-origin" in response.headers
            assert response.headers["access-control-allow-origin"] == origin


def test_cors_headers_not_present_for_disallowed_origin():
    """Test that CORS headers are not present (or set to null) for disallowed origins."""
    response = client.get(
        "/api/v1/locations?limit=1",
        headers={"Origin": "https://evil.com"},
    )
    
    # Should still return response, but CORS headers should not allow the origin
    assert response.status_code in [200, 503]
    
    # If CORS header is present, it should not be the disallowed origin
    if "access-control-allow-origin" in response.headers:
        assert response.headers["access-control-allow-origin"] != "https://evil.com"


def test_head_root_endpoint():
    """Test HEAD request to root endpoint returns 200."""
    response = client.head("/")
    assert response.status_code == 200


def test_get_health_endpoint():
    """Test GET /health returns 200 with ok: true."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"ok": True}

