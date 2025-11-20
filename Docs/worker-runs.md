---
title: Worker Run Tracking
status: active
last_updated: 2025-11-13
scope: operations
owners: [tda-core]
---

# Worker Runs — TDA-143

The `worker_runs` table is the canonical audit log for long-running jobs triggered by the admin UI or CLI. Each entry tracks the life cycle of a worker invocation and feeds live progress to `/api/v1/admin/metrics/snapshot`.

## Table schema

```
worker_runs (
    id UUID PRIMARY KEY,
    bot TEXT,                 -- discovery | classify | verify | monitor
    city TEXT NULL,           -- optional city key (e.g. rotterdam)
    category TEXT NULL,       -- optional category key (e.g. bakery)
    status TEXT,              -- pending | running | finished | failed
    progress INTEGER,         -- 0–100 (%)
    counters JSONB,           -- worker-specific summary payload
    error_message TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
)
```

### Status flow

1. **pending** — row inserted by `/api/v1/admin/workers/run`.
2. **running** — worker accepted the job and stamped `started_at`.
3. **finished** — worker completed successfully, progress forced to `100`.
4. **failed** — worker raised an exception; `error_message` captures the last failure.

Progress updates are clamped to `0–99` during execution; the final transition to `finished` sets `progress = 100`.

## Creating a run

### Admin UI / API

```
POST /api/v1/admin/workers/run
{
  "bot": "discovery",
  "city": "rotterdam",
  "category": "bakery"
}
```

The endpoint validates bot/city/category keys against `Infra/config/*.yml` and returns the generated `run_id`. The admin dashboard exposes dropdowns and a “Run worker” button that calls this API and automatically starts polling every 5 seconds while the run is active.

### CLI

Workers accept an optional `--worker-run-id` flag. When provided, the worker updates the corresponding row instead of running anonymously.

```bash
# Create a run via API (see above) and copy the returned UUID
RUN_ID=00000000-0000-0000-0000-000000000000

# Discovery example with progress reporting
python -m app.workers.discovery_bot --city rotterdam --worker-run-id "$RUN_ID"

# Verification example
python -m app.workers.verify_locations --limit 200 --worker-run-id "$RUN_ID"
```

If the flag is omitted, the worker behaves exactly as before (no writes to `worker_runs`).

## Monitoring progress

- The admin metrics dashboard renders active runs with live progress bars (0–100%).
- Polling frequency automatically increases to 5 seconds while any run is `pending` or `running`, and reverts to 60 seconds when the queue is idle.
- On success the worker stores summary counters (inserted/promoted etc.) in `worker_runs.counters` for quick inspection.
- On failure the worker writes the exception message to `error_message` and keeps the last reported percentage.

## Cleanup guidelines

- Retain `worker_runs` history for observability; schedule archival only after confirming downstream analytics do not depend on it.
- Failed runs can be retried by triggering a new `POST /admin/workers/run` without mutating the old record.

Keep this document updated as new workers adopt run tracking or additional metadata is added.













