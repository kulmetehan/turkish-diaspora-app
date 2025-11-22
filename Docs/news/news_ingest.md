# NewsIngestBot

## Overview

NewsIngestBot is the RSS ingestion worker for the Turkish Diaspora App. It reads every source defined in `configs/news_sources.yml`, downloads the feed, normalizes entries (title, body, timestamps, author, image hints), and stores the raw payloads in `raw_ingested_news`. Each feed is tracked in `news_source_state`, enabling per-source refresh windows, retry backoff, and observability.

## Data flow

1. `app.models.news_sources` loads `configs/news_sources.yml`, enforcing required fields and exposing optional metadata (`region`, `refresh_minutes`).
2. `NewsIngestService` (in `Backend/services/news_ingest_service.py`) gates each feed via `news_source_state.next_refresh_at`. Sources still cooling down are skipped.
3. Eligible sources are fetched concurrently (`httpx.AsyncClient` + bounded semaphore) and parsed with `feedparser`.
4. Each entry becomes a normalized dict with:
   - `ingest_hash = sha1(source_key|link|published_at)` for dedupe.
   - Canonical metadata (title, summary/content, author, language, category, region, published_at).
   - JSONB snapshot of the original entry for downstream processing (summaries, sentiment, geopolitics).
5. Inserts use `ON CONFLICT (source_key, ingest_hash) DO NOTHING`, guaranteeing idempotency across retries and automation runs.
6. `news_source_state` is updated on success (reset failures, set `next_refresh_at = now + refresh_minutes`). Failures increment `consecutive_failures` and push `next_refresh_at` out using a capped exponential multiplier.

## Scheduling & automation

- GitHub Actions: `.github/workflows/tda_news_ingest.yml` runs every 30 minutes (and supports manual workflow_dispatch). It installs backend deps and executes `python -m app.workers.news_ingest_bot`.
- Render Cron / background worker: run the same command with `DATABASE_URL` (and optional `NEWS_INGEST_TIMEOUT_S`, `NEWS_INGEST_MAX_CONCURRENCY`) in the worker environment. Keep the job cadence aligned with GitHub Actions to avoid over-fetching.

## Manual operation

```bash
cd Backend
python -m app.workers.news_ingest_bot --limit 5
```

- `--limit` (optional) caps the number of sources processed for smoke tests.
- Use `NEWS_INGEST_TIMEOUT_S` / `NEWS_INGEST_MAX_CONCURRENCY` env vars to temporarily tune HTTP behavior without code changes.
- Results are recorded in `worker_runs` (counters include `total_sources`, `total_inserted`, `failed_feeds`, `degraded`).

## Downstream consumers

The `processing_state` column in `raw_ingested_news` stays `pending` until future stories (summaries, sentiment tagging, geopolitics) promote items through the pipeline. Those workers should use the same dedupe hash and update `processing_state` + `processing_errors` as they act on each row.

## N1.3 – RSS Normalization Engine

N1.3 introduced a dedicated normalization layer so feed parsing is decoupled from persistence:

- **Module:** `Backend/services/rss_normalization.py`
- **Model:** `Backend/app/models/news_normalized.py::NormalizedNewsItem`
- **Supported formats:** RSS 2.0 and Atom (with graceful fallbacks for unknown feeds)
- **Canonical fields:** `title`, `url`, `snippet`, `source`, `published_at`, `raw_metadata`
- **Error handling:** each entry failure raises `RSSNormalizationError`, is logged as `news_ingest_normalization_error`, and the ingest run continues

`NewsIngestService.ingest_source()` now calls `normalize_feed_entries()` to transform raw feedparser output into normalized items before mapping them to `raw_ingested_news`. This keeps dedupe hashes and DB schema unchanged while allowing future pipelines to reuse the same canonical model.

## N2.1 – News Classification Worker

- Worker: `python -m app.workers.news_classify_bot --limit 100`
- States:
  - `processing_state='pending'` → awaiting classification (ingest default)
  - `processing_state='classified'` → AI scores stored (`relevance_*`, `topics`, `classified_at`, `classified_by`)
  - `processing_state='error_ai'` → AI failure, details captured in `processing_errors`
- AI logging: every call writes to `ai_logs` with `action_type="news.classify"` and the associated `news_id`.
- Counters stored in `worker_runs.counters`:
  - `total` — rows attempted in the batch
  - `classified` — successfully scored rows
  - `errors` — rows that fell back to `error_ai`

## N5.1 – News Metrics Endpoint

The consolidation effort adds a dedicated admin endpoint that surfaces end-to-end news pipeline metrics without changing the main `/admin/metrics/snapshot` payload.

- **Endpoint:** `GET /api/v1/admin/metrics/news`
- **Purpose:** Validate that ingest → classify → feed distribution operates as expected, and quickly spot stalled sources or AI regressions.
- **Payload:**
  - `items_per_day_last_7d`: list of `{ "date": "YYYY-MM-DD", "count": <int> }` grouped by `published_at` for classified rows.
  - `items_by_source_last_24h`: list of `{ "label": "<source_name or key>", "count": <int> }` for the last 24 hours.
  - `items_by_feed_last_24h`: counts per feed (`diaspora`, `nl`, `tr`, `local`, `origin`, `geo`) using the existing `FeedType` rules and AI thresholds.
  - `errors`: `{ "ingest_errors_last_24h": <int>, "classify_errors_last_24h": <int>, "pending_items_last_24h": <int> }`, derived from `raw_ingested_news.processing_state` and `ai_logs`.

Example (truncated):

```json
{
  "items_per_day_last_7d": [
    { "date": "2025-11-15", "count": 42 },
    { "date": "2025-11-16", "count": 58 }
  ],
  "items_by_source_last_24h": [
    { "label": "anadolu_ajansi", "count": 21 },
    { "label": "nos", "count": 17 }
  ],
  "items_by_feed_last_24h": [
    { "label": "diaspora", "count": 33 },
    { "label": "nl", "count": 18 },
    { "label": "tr", "count": 12 }
  ],
  "errors": {
    "ingest_errors_last_24h": 3,
    "classify_errors_last_24h": 1,
    "pending_items_last_24h": 5
  }
}
```

### Operational notes

- The endpoint only reads `raw_ingested_news`, `news_source_state`, and `ai_logs`; no schema changes are required.
- If metrics queries become hot, consider adding a future partial index on `(action_type, created_at)` for `ai_logs` (tracked as technical debt, no migration in this story).
- Frontend admin dashboards can consume this payload directly for charts/tables without re-deriving feed logic.

