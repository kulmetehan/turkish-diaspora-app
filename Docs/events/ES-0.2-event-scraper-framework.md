# ES-0.2 — Event Scraper Framework

## Overview

The Event Scraper framework ingests diaspora event listings from HTML, RSS, or JSON endpoints and stores normalized payloads in `event_raw`. It mirrors the news ingest patterns (selectors-driven config, dedupe hashes, worker_runs integration) while respecting the admin-managed `event_sources` table.

```
event_sources (admin UI) ──> EventScraperBot (HTTP fetch, parsing, dedupe) ──> event_raw ──> dashboards & future enrichment workers
```

## Selector Schema

`event_sources.selectors` now requires a typed payload with `format` describing how to parse the response. Backward-compatible keys (`list`, `title`, `date`) are normalized automatically.

### HTML

```json
{
  "format": "html",
  "item_selector": ".event-card",
  "title_selector": ".event-card__title",
  "url_selector": ".event-card__title@href",
  "date_selector": ".event-card__date",
  "description_selector": ".event-card__excerpt",
  "venue_selector": ".event-card__venue"
}
```

- CSS selectors can append `@attribute` to read attributes (e.g. `a@href`, `img@src`). Use `@text` to force plain text.
- Optional selectors: `description_selector`, `location_selector`, `venue_selector`, `image_selector`.

### RSS / Atom

```json
{
  "format": "rss",
  "item_path": "entries",
  "title_path": "title",
  "url_path": "link",
  "start_path": "published",
  "description_path": "summary"
}
```

Paths support dot-notation (e.g. `content.0.value`). Unspecified keys fall back to standard RSS properties.

### JSON

```json
{
  "format": "json",
  "items_path": "data.events",
  "title_key": "name",
  "url_key": "url",
  "start_key": "start_at",
  "description_key": "summary",
  "location_key": "location",
  "venue_key": "venue"
}
```

`items_path` supports `$.` prefixes and positional indices. Each key is optional except `items_path`.

## Database Schema (`Infra/supabase/018_event_raw.sql`)

`event_raw` stores normalized rows with dedupe and processing metadata:

| Column | Description |
|--------|-------------|
| `event_source_id` | FK to `event_sources` |
| `title` / `description` / `location_text` / `venue` | Normalized metadata |
| `event_url` / `image_url` | Absolute URLs (relative paths resolved with `list_url`/`base_url`) |
| `start_at` / `end_at` | ISO timestamps (converted to UTC) |
| `detected_format` | Enum `html|rss|json` |
| `ingest_hash` | `sha1(source_id|url|start_at|title)` to dedupe |
| `raw_payload` | JSON snapshot of the parsed node/entry |
| `processing_state` / `processing_errors` | Future enrichment stages |
| `fetched_at` / `created_at` | Audit timestamps |

Indexes:
- `(event_source_id, ingest_hash)` unique dedupe constraint.
- Filters on `event_source_id`, `start_at`, `processing_state`.

## Worker: `EventScraperBot`

CLI usage:

```bash
cd Backend
python -m app.workers.event_scraper_bot --limit 5
```

counters written to `worker_runs`:
- `total_sources`, `processed_sources`, `skipped_sources`
- `inserted_items`, `total_items`, `error_sources`

Per-source telemetry:
- `last_run_at`, `last_success_at`, `last_error_at`, `last_error` updated via `mark_event_source_run`.
- Interval enforcement uses `interval_minutes` + `last_run_at`.

### GitHub Actions Automation

- Workflow: `.github/workflows/tda_event_scraper.yml`
- Triggers:
  - `schedule: "*/30 * * * *"` (every 30 minutes, aligned with news ingest cadence)
  - `workflow_dispatch` for manual re-runs from the Actions tab
- Each run performs:
  - Checkout + Python 3.11.9 setup + cached pip install (`Backend/requirements.txt`)
  - Executes `python -m app.workers.event_scraper_bot` inside `Backend/`
  - Env vars: `DATABASE_URL`, `PYTHONPATH=.` and `PYTHONUNBUFFERED=1` (same as other backend workers)
- Concurrency group: `tda-event-scraper` to prevent overlapping cron executions.

You can still run the worker manually via `/api/v1/admin/workers/run` with `bot=event_scraper` for ad-hoc jobs; the GitHub Action covers the continuous ingest schedule.

## Metrics & Observability

`/api/v1/admin/metrics/events` exposes:

- `events_per_day_last_7d` — counts from `event_raw` grouped by day.
- `sources[]` — per-source totals, last success/error timestamps, and last 24h counts.
- `total_events_last_30d`.

Frontend (`/admin/event-sources`) now displays a snapshot card with totals and top sources.

Logging uses Structlog events:

- `event_scraper_source_success`
- `event_scraper_fetch_failed`
- `event_scraper_parse_failed`
- `event_scraper_source_skipped`

## Future Work

- AI-based enrichment (`event_raw.processing_state` promotion).
- Admin UI for selector validation preview.
- Add alerts/dashboards that watch the `/api/v1/admin/metrics/events` payload for ingestion failures.

