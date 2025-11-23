# ES-0.9 — AI-Powered Event Extraction

## Overview
ES-0.9 introduces a parallel ingest lane that targets organizer sites whose markup is difficult to parse with static selectors. The lane fetches complete HTML pages, stores them as immutable artifacts, and sends them to OpenAI for structured extraction before handing off to the existing normalization → enrichment → publication pipeline.

```
event_sources (ai-enabled)
    │
    ├─ EventPageFetcherBot ──► event_pages_raw (pending)
    │
    └─ EventAIExtractorBot ──► event_raw (processing_state=pending)
            └─ EventNormalizationBot ──► events_candidate
                    └─ EventEnrichmentBot ──► events_public
```

## Data model additions
- `event_pages_raw`: Stores full HTML payloads, response headers, dedupe hash, and processing state (`pending`, `extracted`, `error_fetch`, `error_extract`). Every stored row references an `event_source_id` so downstream workers can recover metadata (city, selectors, etc.).
- `EventPageRaw` Pydantic models and `event_pages_raw_service` provide insert/fetch/state helpers modeled after `event_raw_service`.

## Workers
### `event_page_fetcher_bot`
- Allow-listed sources (`AI_PAGE_SOURCE_KEYS`, currently `sahmeran_events`, `ajda_events`, `ediz_events`) are fetched over HTTP (with retries handled by httpx).
- The bot writes a row per source run to `event_pages_raw`, capturing status, headers, and HTML. Fetch failures are recorded with `processing_state='error_fetch'` plus a serialized error payload.
- Counters in `worker_runs` include `pages_fetched`, `pages_inserted`, `pages_deduped`, `fetch_errors`.

### `event_ai_extractor_bot`
- Loads `pending` pages FIFO and chunks large HTML bodies (default 16 kB per chunk) to stay within model limits.
- Each chunk is processed by `EventExtractionService`, which wraps `OpenAIService.generate_json` with a strict schema (`ExtractedEventsPayload`).
- Extracted events are deduped by `(title, start_at, event_url)` before creating `EventRawCreate` objects (hash computed with the same logic as the scraper). Inserts reuse the standard `insert_event_raw`, so dedupe + downstream workers behave identically to selector-based ingest.
- Pages are marked `extracted` on success or `error_extract` with diagnostic JSON on failure.
- Counters include `pages_processed`, `pages_failed`, `events_extracted_total`, `events_created_new`, `events_skipped_existing`.

## Running the pipeline locally
```
cd Backend
.venv/bin/python -m app.workers.event_page_fetcher_bot --limit 1 --source-key sahmeran_events
.venv/bin/python -m app.workers.event_ai_extractor_bot --limit 5 --chunk-size 16000
.venv/bin/python -m app.workers.event_normalization_bot --limit 50
.venv/bin/python -m app.workers.event_enrichment_bot --limit 50
```

After the enrichment run, `/api/v1/events?city=rotterdam&limit=5` should list the AI-extracted rows.

## Current AI page sources
- `sahmeran_events` — https://sahmeran.nl/events
- `ajda_events` — https://ajda.nl/events-list/
- `ediz_events` — https://edizevents.nl/agenda/

All three go through the same fetcher + extractor bots before entering normalization/enrichment.

## Onboarding a new AI source
1. Add/confirm the source row in `event_sources` with a reliable `list_url`.
2. Set `selectors` to at least `{"format": "ai_page"}`.
3. Add the source key to `AI_PAGE_SOURCE_KEYS` in both AI workers.
4. Run the two new workers locally to validate:
   - Inspect `event_pages_raw` (e.g., `SELECT id, page_url, processing_state FROM event_pages_raw ORDER BY fetched_at DESC LIMIT 5;`).
   - Inspect `event_raw` for new rows referencing the same `event_source_id`.
5. Trigger `event_normalization_bot` + `event_enrichment_bot` to ensure the events flow through to `events_candidate`/`events_public`.

## Observability & troubleshooting
- `worker_runs` entries exist for both new bots (`bot=event_page_fetcher`, `bot=event_ai_extractor`).
- `event_pages_raw.processing_state` surfaces fetch vs. extraction failures; `processing_errors` contains structured JSON with the root cause.
- AI calls are logged via `ai_logs` with `action_type="events.extract_from_html"`.
- Use `/api/v1/admin/events/raw?processing_state=pending` to confirm AI-created rows are awaiting normalization if the pipeline stalls.


