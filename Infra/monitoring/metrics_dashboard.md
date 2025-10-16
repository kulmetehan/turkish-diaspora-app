# Metrics Dashboard (TDA-20, MVP)

This dashboard defines the initial 5+ KPIs using SQL over the existing schema.

## KPIs

1) New Candidates / Week (last 8 weeks)
- Source: locations (state='CANDIDATE', first_seen_at)
- SQL: see Backend/app/services/metrics_service.py (kpi_new_candidates_per_week)

2) Conversion Rate to VERIFIED (14 days cohort)
- Source: locations (first_seen_at >= NOW()-14d; state='VERIFIED')
- Rationale: simple cohort conversion

3) Task Error Rate (last 60 minutes)
- Source: tasks (status/is_success) OR ai_logs fallback with action_type LIKE worker./bot./task.
- Threshold: ALERT at ≥10%

4) API Latency (last 60 minutes)
- Source: ai_logs JSON fields (duration_ms in validated_output/raw_response/meta)
- Display p50/avg/max

5) Google API 429 Count (last 60 minutes)
- Source: ai_logs error markers (429 in error_message or raw_response.statusCode)
- Threshold: ALERT at ≥5 (default)

## Widgets (suggested)

- Time series: New CANDIDATEs per week
- Single value + sparkline: Conversion rate (14d)
- Single value: Error rate (1h), with red/amber/green thresholds
- Single value row: API latency (p50/avg/max)
- Single value: Google 429 count (1h)

## Notes
- Output is JSON-friendly for log collectors; ideal stepping stone to Prometheus/Grafana in V2.
- Keep costs low: no extra infra required at MVP stage.
