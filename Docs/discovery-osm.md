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
- Respect rate limits via token bucket throttling and exponential backoff.
- Rotate across multiple mirrors to handle outages.
- Normalize JSON payloads to the internal `locations` schema.
- Record telemetry in `overpass_calls` for monitoring.

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `OVERPASS_USER_AGENT` | `TurkishDiasporaApp/1.0 (contact: …)` | Must contain a real contact email per OSM policy. |
| `DISCOVERY_RATE_LIMIT_QPS` | `0.15` | Global QPS budget enforced by token bucket. |
| `DISCOVERY_SLEEP_BASE_S` | `3.0` | Base delay between calls. |
| `DISCOVERY_SLEEP_JITTER_PCT` | `0.20` | Jitter percentage applied to sleep. |
| `DISCOVERY_BACKOFF_SERIES` | `20,60,180,420` | Seconds to wait after repeated failures. |
| `OVERPASS_TIMEOUT_S` | `30` | HTTP timeout per request. |
| `DISCOVERY_MAX_RESULTS` | `25` | Maximum elements returned per request. |
| `MAX_SUBDIVIDE_DEPTH` | `2` | Quadtree depth for subdividing dense grids. |
| `OSM_TURKISH_HINTS` | `true` | Adds keyword filters for Turkish phrases to Overpass query. |
| `OSM_LOG_QUERIES` / `OSM_TRACE` | `false` / `0` | Verbose debugging. Disable in production. |

## Mirror rotation

The service cycles through the following mirrors:

1. `https://overpass-api.de/api/interpreter`
2. `https://z.overpass-api.de/api/interpreter`
3. `https://overpass.kumi.systems/api/interpreter`
4. `https://overpass.openstreetmap.ru/api/interpreter`

On failure, the client rotates to the next mirror and applies backoff according to `DISCOVERY_BACKOFF_SERIES`.

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
