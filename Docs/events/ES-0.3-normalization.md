# ES-0.3 — Event Normalization Pipeline

## Overview

The normalization pipeline promotes raw scraper output stored in `event_raw` into a canonical dataset (`events_candidate`). Each record is sanitized (title/description/location/url) and all timestamps are persisted in UTC, ready for downstream QA and publishing.

```
event_sources
   │
   ├─ EventScraperBot ──► event_raw (processing_state=pending)
   │
   └─ EventNormalizationBot ──► events_candidate + processing_state=normalized/error_norm
```

## Schema

`Infra/supabase/019_events_candidate.sql` introduces `events_candidate` with:

- `event_source_id` / `event_raw_id` FKs (with cascade on raw deletes)
- Required fields: `title`, `start_time_utc`, `source_key`, `ingest_hash`
- Optional fields: `description`, `end_time_utc`, `location_text`, `url`
- `state` defaults to `candidate` (room for future promotion)
- `UNIQUE (event_source_id, ingest_hash)` prevents duplicate inserts per source
- Indexes on `start_time_utc` (sorting/filtering) and `state`

## Normalization Rules

Implemented in `Backend/services/event_normalization_service.py`:

- **Title**: required; trims whitespace/HTML and falls back to `raw_payload.title`.
- **Description**: strips HTML tags; tries `description`, `raw_payload.description`, `raw_payload.summary`.
- **Times**: missing `start_at` → `EventNormalizationError`. All datetimes coerced to UTC (naive inputs treated as UTC).
- **Location text**: combines `location_text`, `venue`, or payload hints (comma-separated unique parts).
- **URL**: `_normalize_url` ensures canonical `https://domain/path` form; invalid URLs stored as `NULL`.
- **State**: `candidate` by default to mirror future verify/publish flow.

Errors raise `EventNormalizationError` with a short code (e.g. `missing_start_time`), which is persisted in `event_raw.processing_errors`.

## Worker

`Backend/app/workers/event_normalization_bot.py`:

- Fetches pending `event_raw` rows (`processing_state='pending'`) FIFO.
- Loads `EventSource` metadata (cached per run) and calls `normalize_event`.
- Inserts into `events_candidate` via `insert_event_candidate`. Dedupe hits still mark the row as processed.
- Updates `event_raw.processing_state`:
  - `normalized` on success
  - `error_norm` on validation/processing failures (details in `processing_errors`)
- Emits counters: `fetched`, `normalized`, `errors`.

Run locally:

```bash
cd Backend
python -m app.workers.event_normalization_bot --limit 100
```

The worker is available via `POST /api/v1/admin/workers/run` (`bot=event_normalization`) and orchestrated/scheduled just like other bots.



