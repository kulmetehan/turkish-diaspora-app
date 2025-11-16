from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple

import pytest

# Target module
from services import coverage_service as cov


@pytest.mark.asyncio
async def test_get_city_coverage_summary_sql_aggregation(monkeypatch):
    """
    Minimal sanity test that verifies SQL-aggregated overpass_calls metrics are merged by cell_id
    and returned in the expected summary/cells shape.
    The DB layer is mocked to avoid integration dependencies.
    """

    # Keep reference to original fetch in case needed
    # from services.db_service import fetch as real_fetch

    async def fake_fetch(sql: str, *params: Any):
        # overpass_calls aggregation query path
        if "FROM overpass_calls" in sql and "GROUP BY cell_id" in sql:
            # params: (cell_ids: List[str], from_date, to_date)
            cell_ids: List[str] = list(params[0]) if params and isinstance(params[0], (list, tuple)) else []
            results = []
            # Return metrics for first two cells if present
            now = datetime.now(timezone.utc)
            for i, cid in enumerate(cell_ids[:2]):
                results.append(
                    {
                        "cell_id": cid,
                        "total_calls": 10 + i,
                        "successful_calls": 8 + i,
                        "error_429": 1,
                        "error_other": 1,
                        "first_seen_at": now,
                        "last_seen_at": now,
                    }
                )
            return results

        # locations coverage path: return empty to simplify
        if "FROM locations" in sql:
            return []

        # default empty
        return []

    # Monkeypatch the fetch used inside coverage_service
    monkeypatch.setattr(cov, "fetch", fake_fetch, raising=True)

    # Call function under test
    data = await cov.get_city_coverage_summary(city="rotterdam", district=None, from_date=None, to_date=None)

    # Basic shape assertions
    assert isinstance(data, dict)
    assert "cells" in data and isinstance(data["cells"], list)
    assert "summary" in data and isinstance(data["summary"], dict)

    cells = data["cells"]
    summary = data["summary"]

    # There should be at least as many cells as grid points for Rotterdam; we don't assert exact number.
    assert len(cells) > 0

    # Our fake returns totals for the first two grid cell_ids only.
    total_calls_counted = sum(int(c.get("call_count", 0)) for c in cells)
    # Expect 10 + 11 = 21 total calls from the two mocked cells
    assert total_calls_counted >= 21

    # Summary should reflect at least the counted calls
    assert int(summary.get("totalCalls", 0)) >= 21


