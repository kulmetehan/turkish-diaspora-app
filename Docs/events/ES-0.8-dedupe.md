# ES-0.8 — Event Duplicate Detection

## Overview

ES-0.8 introduces a cross-source dedupe layer for events. After `event_normalization_bot`
inserts a candidate, `event_dedupe_service.run_dedupe()` compares the new row with
canonical candidates (same city + time window) and sets `events_candidate.duplicate_of_id`
and `duplicate_score` when a high-confidence match is detected. Canonical rows (where
`duplicate_of_id IS NULL`) are the only ones exposed via `events_public`.

## Scoring

- **Title similarity (60%)** — fuzzy ratio via `SequenceMatcher`.
- **Location similarity (20%)** — same fuzzy metric on `location_text`.
- **Time proximity (20%)** — linear decay over a configurable ±48h window.
- **Optional AI boost** — if enabled via `EVENT_DEDUPE_AI_ENABLED`, GPT evaluates
  borderline matches and blends the score with `AI_WEIGHT`.
- Thresholds can be tuned via env vars (`EVENT_DEDUPE_*`).

## Pipeline & Logging

- `event_normalization_bot` now tracks counters: `dedupe_checked`, `dedupe_marked_duplicate`,
  `dedupe_canonical`, `dedupe_errors`.
- `metrics_service.generate_event_metrics_snapshot()` reports canonical vs duplicates in the
  new `dedupe` block plus the recent duplicate count.
- `worker_runs` payloads show dedupe counters per normalization run.

## Admin Experience

- `/api/v1/admin/events/candidates` accepts `duplicates_only` and `canonical_only` filters
  and returns duplicate metadata (`duplicate_of_id`, `duplicate_score`, `has_duplicates`).
- New endpoint `/api/v1/admin/events/candidates/{id}/duplicates` returns a canonical + its
  merged duplicates.
- Admin UI exposes a “Duplicates” filter, badges for canonical/duplicate rows, and a
  “View duplicates” modal for canonical chains.

## Public API

- `events_public` view filters out duplicates (`duplicate_of_id IS NULL`), ensuring
  `/api/v1/events` surfaces a single canonical record per real-world event.


