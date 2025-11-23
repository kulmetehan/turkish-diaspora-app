from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_admin_events_metrics_endpoint_structure():
    response = client.get("/api/v1/admin/metrics/events")
    assert response.status_code in (200, 503)

    if response.status_code == 200:
        payload = response.json()
        assert "events_per_day_last_7d" in payload
        assert "sources" in payload
        assert "total_events_last_30d" in payload
        assert "enrichment" in payload

        enrichment = payload["enrichment"]
        assert "total" in enrichment
        assert "enriched" in enrichment
        assert "pending" in enrichment
        assert "errors" in enrichment

        sources = payload["sources"]
        if sources:
            first = sources[0]
            assert "source_id" in first
            assert "source_key" in first
            assert "events_last_24h" in first

