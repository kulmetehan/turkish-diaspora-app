# ES-0.4 — Event AI Enrichment

## Overview

ES-0.4 introduces an AI worker that enriches `event_raw` rows after the scraper inserts them. Each event now receives:

- `language_code` (`nl`, `tr`, `en`, or `other`)
- `category_key` (community, religion, culture, business, education, sports, other)
- `summary_ai` (≤1 000 chars)
- `confidence_score` (0–1, logged in both the table and `ai_logs`)
- `enriched_at` / `enriched_by`
- Structured audit trail in `ai_logs` with the new `event_raw_id` column.

## Database Changes

- `Infra/supabase/019_event_enrichment.sql` adds the enrichment columns to `event_raw`, constrains `processing_state` to `pending|enriched|error`, and links `ai_logs.event_raw_id`.
- `Infra/config/event_categories.yml` is the canonical taxonomy; the loader falls back to a baked-in set if the file is missing.

### Processing States

| State     | Meaning                                                |
|-----------|--------------------------------------------------------|
| pending   | Newly scraped rows awaiting AI enrichment              |
| enriched  | Successfully enriched rows ready for downstream usage  |
| error     | AI call failed or payload invalid; inspect `processing_errors` |

## EventEnrichmentService

Path: `Backend/services/event_enrichment_service.py`

- Uses `OpenAIService.generate_json(..., action_type="events.enrich", event_raw_id=<id>)`.
- Schema defined in `app/models/event_enrichment.py` (`EventEnrichmentResult`).
- Prompt pulls title, description, venue, location, URL, and start/end timestamps.
- Categories normalized via `services/event_categories_service`.
- Exceptions bubble up so the worker can flag the row as `processing_state='error'`.

## Worker: `event_enrichment_bot`

- CLI: `python -m app.workers.event_enrichment_bot --limit 50 [--model gpt-4.1-mini]`
- Lifecycle managed via `worker_runs` (bot=`event_enrichment`).
- Flow:
  1. Fetch `pending` rows via `fetch_pending_event_raw`.
  2. Call `EventEnrichmentService.enrich_event`.
  3. Persist output with `apply_event_enrichment` (sets `processing_state='enriched'`).
  4. On failure, call `mark_event_enrichment_error` (records `processing_errors` JSON).
- All AI calls appear in `ai_logs` with `action_type="events.enrich"` and the new `event_raw_id`.

## Observability

- `/api/v1/admin/metrics/events` now reports enrichment totals, error counts, average confidence, and top categories.
- `/api/v1/admin/events/raw` exposes paginated enriched rows for admin review with filters for `processing_state`, `event_source_id`, and `category_key`.

## Runbook Notes

1. Verify event categories in `Infra/config/event_categories.yml` before deploying to production.
2. Ensure `OPENAI_API_KEY` is configured for the worker execution environment.
3. Enrichment worker is idempotent; rerunning processes only rows in `pending`.
4. Watch `ai_logs` for `action_type="events.enrich"` to debug prompts or model drift.



