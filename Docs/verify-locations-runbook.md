---
title: Verify & Surface Locations Runbook
status: active
last_updated: 2025-11-04
scope: runbook
owners: [tda-core]
---

# Verify & Surface Locations — Runbook

Runbook for the `verify_locations.py` worker responsible for promoting high-confidence locations from `CANDIDATE/PENDING_VERIFICATION` to `VERIFIED` and ensuring they surface in the frontend.

## Overview

- Worker module: `Backend/app/workers/verify_locations.py`
- Inputs: `locations` table rows with `state IN ('CANDIDATE','PENDING_VERIFICATION')`
- Services used: `ClassifyService`, `validate_classification_payload`, `update_location_classification`, `audit_service`
- Output: Updated `locations` row (`state`, `category`, `confidence_score`, `last_verified_at`) plus audit log entry in `ai_logs`

## Requirements

- Valid `DATABASE_URL`
- `OPENAI_API_KEY` (required for non-dry runs)
- `SUPABASE_JWT_SECRET` + `ALLOWED_ADMIN_EMAILS` (for admin API calls)
- Optional threshold tweak via `CLASSIFY_MIN_CONF`

## CLI usage

```bash
cd Backend
source .venv/bin/activate

# Default run (limit 200, real writes)
python -m app.workers.verify_locations --limit 200 --dry-run 0

# Dry run (safe for local testing)
python -m app.workers.verify_locations --limit 50 --dry-run 1

# Large batch with chunking (6 slices)
python -m app.workers.verify_locations --limit 1200 --chunks 6 --chunk-index 0 --dry-run 0
```

### Flags

| Flag | Default | Description |
| --- | --- | --- |
| `--limit` | `200` | Max number of rows to process (per execution). |
| `--offset` | `0` | Legacy pagination support. Normally managed via chunking. |
| `--chunks` / `--chunk-index` | `1` / `0` | Split workload into even slices; useful for parallel GitHub Action matrix runs. |
| `--dry-run` | `0` | When `1`, performs classification/validation but skips writes & audit logs. |
| `--min-confidence` | `0.8` | Override classification confidence threshold when promoting. |
| `--model` | default | Override OpenAI model name. |
| `--city`, `--source` | optional | Accepted for future filtering; currently informational (fetch query does not filter yet). |
| `--log-json` | `0` | Emit JSON logs (helpful for log aggregation). |

## Worker flow

1. Fetch candidate rows (`state IN ('CANDIDATE','PENDING_VERIFICATION')`) sorted by `first_seen_at`.
2. For each row:
   - Call `ClassifyService.classify` (OpenAI) to obtain action/category/confidence.
   - Validate JSON via `validate_classification_payload`.
   - Apply classification via `update_location_classification`, respecting no-downgrade rules.
   - When writing, append audit entry with action, category, confidence.
   - On error, stamp `last_verified_at` to avoid hot loops and log exception.
3. Print `[PROMOTE]`, `[SKIP]`, `[ERROR]` lines summarising outcomes.
4. Return aggregated stats (processed/promo/skip/error).

## Verification queries

```sql
-- Recently promoted locations
SELECT id, name, category, source, state, confidence_score, last_verified_at
FROM locations
WHERE state = 'VERIFIED'
ORDER BY last_verified_at DESC
LIMIT 50;

-- State distribution
SELECT state, COUNT(*)
FROM locations
GROUP BY state
ORDER BY COUNT(*) DESC;

-- OSM-specific promotions
SELECT id, name, category, confidence_score
FROM locations
WHERE source = 'OSM_OVERPASS'
  AND state = 'VERIFIED'
ORDER BY last_verified_at DESC
LIMIT 25;
```

## API smoke test

The frontend consumes `GET /api/v1/locations` (no special parameters required). The endpoint automatically returns:

- All `VERIFIED` rows with `confidence_score >= 0.80`
- High-confidence (`>=0.90`) `PENDING_VERIFICATION`/`CANDIDATE` rows for surfacing

```bash
curl -s "http://127.0.0.1:8000/api/v1/locations?limit=50" | jq '.[0:5]'
```

Ensure Supabase admin auth remains functional by calling the who-am-I endpoint via the frontend helper:

```ts
import { whoAmI } from "@/lib/api";
whoAmI().then(console.log);
```

Expected response:

```json
{ "ok": true, "admin_email": "admin@example.com" }
```

## Metrics & dashboards

- `Infra/monitoring/metrics_dashboard.sql` tracks `conversion_rate_verified_14d`, error rates, latency.
- Verify that `/api/v1/admin/metrics/snapshot` reflects recent promotions (requires Supabase admin JWT).

## Troubleshooting

| Issue | Mitigation |
| --- | --- |
| Dry run succeeds but writes fail | Ensure `OPENAI_API_KEY` is set and not rate-limited; check Postgres permissions. |
| No promotions happening | Review `confidence_score` distribution (`min-confidence` too high?) and audit reasons (`ai_logs`). |
| Supabase who-am-I returning 401/403 | Verify JWT secret, email allowlist, and Supabase session. |
| Frontend still shows old data | Clear frontend cache, ensure API base URL is correct, confirm worker summary shows promotions (`[PROMOTE]`). |
| Chunked run processes 0 rows | Ensure `--limit` is divisible by chunks and dataset has enough candidates; run monitor bot to refresh stale records. |

## References

- Worker source: [`Backend/app/workers/verify_locations.py`](../Backend/app/workers/verify_locations.py)
- API router: [`Backend/api/routers/locations.py`](../Backend/api/routers/locations.py)
- Metrics snapshot: [`Backend/services/metrics_service.py`](../Backend/services/metrics_service.py)
- Classification helpers: [`Backend/services/classify_service.py`](../Backend/services/classify_service.py), [`Backend/services/ai_validation.py`](../Backend/services/ai_validation.py)
- Main runbook: [`Docs/runbook.md`](./runbook.md)
