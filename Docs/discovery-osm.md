---
title: OSM Discovery Provider
status: active
last_updated: 2025-11-04
scope: backend
owners: [tda-core]
---

# OSM Discovery Provider

Technical overview of the Overpass (OSM) provider used by `discovery_bot` and `services/osm_service.py`.

## Responsibilities

- Build Overpass QL queries from category/tag definitions.
- **Strictly respect Overpass public usage guidelines** (≤10k queries/day, ≤1GB/day, max 1 concurrent request per endpoint).
- Enforce per-endpoint rate limiting with semaphores and minimum delays.
- Implement robust retry with exponential backoff for transient errors.
- Rotate across multiple mirrors to handle outages (optional fallback).
- Normalize JSON payloads to the internal `locations` schema.
- Record telemetry in `overpass_calls` with categorized error messages for monitoring.

## Environment variables

### Overpass API Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `OVERPASS_USER_AGENT` | `TurkishDiasporaApp/1.0 (contact: …)` | Must contain a real contact email per OSM policy. |
| `OVERPASS_ENDPOINTS` | (see below) | Comma-separated list of Overpass API endpoints. If not set, uses default public endpoints. |
| `OVERPASS_PRIMARY_ENDPOINT` | (none) | Optional override to use a specific primary endpoint. |
| `OVERPASS_REQUEST_TIMEOUT_SECONDS` | `45` | HTTP timeout per request (also used in `[timeout:...]` query directive). |
| `OVERPASS_MAX_CONCURRENT_PER_ENDPOINT` | `1` | Maximum concurrent requests per endpoint (enforced via semaphore). **Must be 1** for public Overpass servers. |
| `OVERPASS_MIN_DELAY_SECONDS` | `8` | Minimum delay between requests to the same endpoint (enforces ≤1 request per 8s for public usage guidelines). |
| `OVERPASS_MAX_RETRIES` | `2` | Maximum retry attempts for transient errors (timeout, 5xx, 429, network disconnects). |
| `OVERPASS_BACKOFF_BASE_SECONDS` | `2` | Base delay for exponential backoff (retry delay = base * 2^attempt + jitter). |
| `OVERPASS_BACKOFF_JITTER_FRACTION` | `0.3` | Jitter fraction applied to backoff delay (prevents thundering herd). |
| `OVERPASS_ENABLE_ENDPOINT_FALLBACK` | `false` | If `true`, automatically rotate to next endpoint on repeated failures within a run. |

### Legacy Configuration (still supported for backward compatibility)

| Variable | Default | Description |
| --- | --- | --- |
| `OVERPASS_TIMEOUT_S` | `30` | Legacy alias for `OVERPASS_REQUEST_TIMEOUT_SECONDS` (lower priority). |
| `DISCOVERY_RATE_LIMIT_QPS` | `0.15` | Legacy token bucket rate limiter (superseded by per-endpoint semaphore + delay). |
| `DISCOVERY_SLEEP_BASE_S` | `3.0` | Legacy fixed sleep (superseded by `OVERPASS_MIN_DELAY_SECONDS`). |
| `DISCOVERY_SLEEP_JITTER_PCT` | `0.20` | Legacy jitter (superseded by `OVERPASS_BACKOFF_JITTER_FRACTION`). |
| `DISCOVERY_BACKOFF_SERIES` | `20,60,180,420` | Legacy backoff series (superseded by exponential backoff). |

### Discovery Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `DISCOVERY_MAX_RESULTS` | `25` | Maximum elements returned per request. |
| `MAX_SUBDIVIDE_DEPTH` | `2` | Quadtree depth for subdividing dense grids. |
| `DISCOVERY_MAX_CONSECUTIVE_OVERPASS_FAILURES` | `10` | Circuit breaker: stop Overpass calls if N consecutive failures. |
| `DISCOVERY_MAX_OVERPASS_ERROR_RATIO` | `0.8` | Circuit breaker: stop Overpass calls if error ratio exceeds this (0.0-1.0). |
| `OSM_TURKISH_HINTS` | `true` | Adds keyword filters for Turkish phrases to Overpass query. |
| `OSM_LOG_QUERIES` / `OSM_TRACE` | `false` / `0` | Verbose debugging. Disable in production. |

## Default Endpoint Pool

If `OVERPASS_ENDPOINTS` is not set, the service uses these default public Overpass mirrors:

1. `https://overpass-api.de/api/interpreter`
2. `https://z.overpass-api.de/api/interpreter`
3. `https://overpass.kumi.systems/api/interpreter`
4. `https://overpass.openstreetmap.ru/api/interpreter`

## Rate Limiting & Concurrency Control

The service implements **industry-grade Overpass safety mechanisms**:

1. **Per-endpoint semaphore**: Enforces `OVERPASS_MAX_CONCURRENT_PER_ENDPOINT` (default: 1) globally across all service instances.
2. **Minimum delay enforcement**: Tracks last request timestamp per endpoint and enforces `OVERPASS_MIN_DELAY_SECONDS` (default: 8s) between requests.
3. **Retry with exponential backoff**: Automatically retries transient errors (timeout, 5xx, 429, network disconnects) up to `OVERPASS_MAX_RETRIES` times with exponential backoff.
4. **Error categorization**: Standardized error message prefixes (`TIMEOUT:`, `RATE_LIMIT:`, `SERVER_5XX:`, `DISCONNECT:`) for better metrics analysis.

These mechanisms ensure compliance with Overpass public usage guidelines: **≤10,000 queries/day** and **≤1GB/day** per endpoint.

## Circuit Breaker

DiscoveryBot includes a **circuit breaker** to protect Overpass from overload:

- **Consecutive failures threshold**: If `DISCOVERY_MAX_CONSECUTIVE_OVERPASS_FAILURES` consecutive calls fail, the run stops making Overpass calls (but continues processing already-found results).
- **Error ratio threshold**: If error ratio exceeds `DISCOVERY_MAX_OVERPASS_ERROR_RATIO`, the run stops making Overpass calls.

When triggered, the run is marked as **degraded** in `discovery_runs` with counters tracking total/failed Overpass calls.

## Mirror Rotation & Fallback

The service supports endpoint rotation for resilience:

- **Manual rotation**: Call `_rotate_endpoint()` to manually switch to the next endpoint.
- **Automatic fallback** (if `OVERPASS_ENABLE_ENDPOINT_FALLBACK=true`): On repeated failures, automatically rotate to the next endpoint in the pool.

For public Overpass usage, endpoint fallback is **disabled by default** to avoid spreading load across mirrors unnecessarily.

## Normalization steps

- Parse response JSON, falling back to safe defaults for atypical payloads.
- Convert elements into a canonical dict (`place_id`, `name`, `lat`, `lng`, `category`, etc.).
- Insert records as `CANDIDATE` state, skipping duplicates based on `place_id` or fuzzy `(name, lat, lng)` matching.
- Log each call in `overpass_calls` with status code, duration, endpoint, and preview snippet.

## Telemetry

`overpass_calls` schema (summary):

```sql
SELECT endpoint,
       COUNT(*) AS total,
       SUM(CASE WHEN status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success,
       SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) AS server_errors
FROM overpass_calls
WHERE ts >= NOW() - INTERVAL '24 hours'
GROUP BY endpoint;
```

Use this table to monitor mirror health, latency, and success rates. Combine with alert bot thresholds to catch repeated failures.

## Local testing

```bash
cd Backend
source .venv/bin/activate
python -m app.workers.discovery_bot \
  --city rotterdam \
  --categories bakery \
  --limit 10 \
  --dry-run
```

Check worker output for `[NEW]`, `[SKIP]`, or `[RETRY]` messages and adjust env vars as necessary.

## Related docs

- `Docs/discovery-config.md` — category/tag definitions.
- `Docs/osm-discovery-improvements.md` — tuning notes and production lessons.
- `Docs/automation.md` — GitHub Actions schedules for discovery runs.
