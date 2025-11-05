"""
Admin discovery KPIs endpoint.

Returns daily aggregates from discovery_runs table for monitoring discovery
performance and growth sustainability.
"""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Query
import json

from services.db_service import fetch


router = APIRouter(
    prefix="/admin/discovery",
    tags=["admin-discovery"],
)


@router.get("/kpis")
async def get_discovery_kpis(
    days: int = Query(
        default=30,
        ge=1,
        le=90,
        description="Number of days to aggregate (1-90)",
    ),
) -> Dict[str, Any]:
    """
    Get discovery KPIs aggregated by day.
    
    Returns daily aggregates from discovery_runs table:
    - inserted: new locations inserted
    - deduped_fuzzy: fuzzy duplicates found (updated existing)
    - updated_existing: existing records updated via soft-dedupe
    - deduped_place_id: strict place_id duplicates skipped
    - discovered: total locations discovered
    - failed: failed insert/update operations
    
    Aggregated over the last N days (default 30).
    """
    sql = """
        SELECT
            DATE(started_at) AS day,
            SUM((counters->>'inserted')::int) AS inserted,
            SUM((counters->>'deduped_fuzzy')::int) AS deduped_fuzzy,
            SUM((counters->>'updated_existing')::int) AS updated_existing,
            SUM((counters->>'deduped_place_id')::int) AS deduped_place_id,
            SUM((counters->>'discovered')::int) AS discovered,
            SUM((counters->>'failed')::int) AS failed
        FROM discovery_runs
        WHERE started_at >= NOW() - (($1::int || ' days')::interval)
          AND finished_at IS NOT NULL
        GROUP BY DATE(started_at)
        ORDER BY day DESC
    """
    
    try:
        rows = await fetch(sql, days)
        daily_data: List[Dict[str, Any]] = []
        
        for row in rows:
            d = dict(row)
            daily_data.append({
                "day": str(d.get("day")),
                "inserted": int(d.get("inserted") or 0),
                "deduped_fuzzy": int(d.get("deduped_fuzzy") or 0),
                "updated_existing": int(d.get("updated_existing") or 0),
                "deduped_place_id": int(d.get("deduped_place_id") or 0),
                "discovered": int(d.get("discovered") or 0),
                "failed": int(d.get("failed") or 0),
            })
        
        # Calculate totals
        totals = {
            "inserted": sum(d.get("inserted", 0) for d in daily_data),
            "deduped_fuzzy": sum(d.get("deduped_fuzzy", 0) for d in daily_data),
            "updated_existing": sum(d.get("updated_existing", 0) for d in daily_data),
            "deduped_place_id": sum(d.get("deduped_place_id", 0) for d in daily_data),
            "discovered": sum(d.get("discovered", 0) for d in daily_data),
            "failed": sum(d.get("failed", 0) for d in daily_data),
        }
        
        return {
            "days": days,
            "daily": daily_data,
            "totals": totals,
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "days": days,
            "daily": [],
            "totals": {},
        }

