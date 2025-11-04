---
title: Metrics Dashboard (TDA-20)
status: active
last_updated: 2025-11-04
scope: observability
owners: [tda-data]
---

# Metrics Dashboard (TDA-20)

Defines the KPIs surfaced by `/api/v1/admin/metrics/snapshot` and the SQL required to power the admin dashboard.

## Snapshot shape

The metrics endpoint returns `MetricsSnapshot` (see `Backend/services/metrics_service.py`):

```json
{
  "city_progress": {
    "rotterdam": {
      "verified_count": 0,
      "candidate_count": 0,
      "coverage_ratio": 0.0,
      "growth_weekly": 0.0
    }
  },
  "quality": {
    "conversion_rate_verified_14d": 0.0,
    "task_error_rate_60m": 0.0,
    "google429_last60m": 0
  },
  "discovery": {
    "new_candidates_per_week": 0
  },
  "latency": {
    "p50_ms": 0,
    "avg_ms": 0,
    "max_ms": 0
  },
  "weekly_candidates": []
}
```

## KPI definitions

1. **Conversion rate (14d)** — `locations` promoted to `VERIFIED` within 14 days vs. total new records.
2. **Task error rate (60m)** — Percentage of `ai_logs` with failure or error message over the last hour.
3. **Google 429 count (60m)** — Legacy metric; counts 429-like errors in `ai_logs` (still useful for historical comparison).
4. **Discovery new candidates per week** — Count of `locations` with `state='CANDIDATE'` grouped by ISO week.
5. **City progress (Rotterdam)** — Verified vs. candidate totals inside city bounding box, coverage ratio, week-over-week growth based on `last_verified_at`.
6. **Latency** — Duration statistics (ms) read from `validated_output`/`raw_response` JSON in `ai_logs` over 60 minutes.

## Core SQL snippets

See `Backend/services/metrics_service.py` for query details. The dashboard can reuse these queries directly if building SQL-based widgets.

- `quality` metrics: `_conversion_rate_14d`, `_task_error_rate`, `_google429_bursts`
- `latency`: `_latency_stats`
- `discovery`: `_weekly_candidates_series`
- `city_progress`: `_rotterdam_progress` (`Infra/config/cities.yml` fed into bounding box helper)

## Dashboard suggestions

| Widget | Query |
| --- | --- |
| New candidates (timeseries) | `weekly_candidates` array | 
| Conversion rate (single value + trend) | `_conversion_rate_14d` | 
| Error rate (traffic light) | `_task_error_rate(60)` | 
| Latency (p50/avg/max) | `_latency_stats(60)` | 
| City progress table | `_rotterdam_progress` |

## Maintenance

- Update bounding boxes in `Infra/config/cities.yml` when expanding to new cities; reflect changes in metrics service.
- Keep alert thresholds in sync with dashboard expectations (`ALERT_ERR_RATE_THRESHOLD`, `ALERT_GOOGLE429_THRESHOLD`).
- Validate metrics after schema changes by running `python -m app.services.metrics_service` (add temporary CLI if needed) or hitting the endpoint locally.
