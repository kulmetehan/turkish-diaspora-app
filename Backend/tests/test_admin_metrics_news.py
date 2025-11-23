from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_admin_news_metrics_endpoint_structure():
    response = client.get("/api/v1/admin/metrics/news")
    assert response.status_code in (200, 503)

    if response.status_code == 200:
        payload = response.json()
        assert "items_per_day_last_7d" in payload
        assert "items_by_source_last_24h" in payload
        assert "items_by_feed_last_24h" in payload
        assert "errors" in payload

        errors = payload["errors"]
        assert "ingest_errors_last_24h" in errors
        assert "classify_errors_last_24h" in errors
        assert "pending_items_last_24h" in errors


