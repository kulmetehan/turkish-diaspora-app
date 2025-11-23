# ES-0.5 — Events Dashboard

## Overview

ES-0.5 introduces the first end-to-end admin workflow for diaspora events. Admins can now review normalized `events_candidate` rows, filter by source/state, and promote them through the `candidate → verified → published` lifecycle (or reject them outright). The UI mirrors the existing Worker Dashboard styling so operators have a consistent experience across admin surfaces.

```
event_sources
   │
   ├─ EventScraperBot ──► event_raw (processing_state=pending|enriched|error)
   │
   └─ EventNormalizationBot ──► events_candidate (state=candidate|verified|published|rejected)
```

## Backend Changes

- **Schema guard**: `Infra/supabase/020_events_candidate_state_machine.sql` adds a check constraint ensuring `events_candidate.state` stays within the supported states (`candidate`, `verified`, `published`, `rejected`).
- **Services**:
  - `services/event_candidate_service.list_event_candidates(...)` handles filtering/pagination.
  - `services/event_candidate_service.update_event_candidate_state(...)` enforces valid transitions and structured logging.
- **Admin API** (`/api/v1/admin/events`):
  - `GET /candidates` — list candidates filtered by state/source/search (admin auth required).
  - `POST /candidates/{id}/verify`, `/publish`, `/reject` — promote or reject an event candidate.

Invalid transitions (e.g., `published → verified`) return HTTP 400; missing records return 404.

## Frontend Changes

- New route `/admin/events` (guarded by `RequireAdmin`) with the **Admin Events Dashboard** page.
- Features:
  - Worker Dashboard–style filters (state dropdown, source dropdown, search input).
  - Table view with status badges, source info, and context.
  - Inline actions (Verify, Publish, Reject) with toast feedback, respecting server-side validation.
  - Pagination controls with 25-item pages.

Implementation highlights:

- `AdminEventsTable` component encapsulates the table UI.
- New `apiAdmin` helpers power listing and promotion actions.
- Vitest suites cover helper serialization and page behavior (rendering + action button invocation).

## State Machine

| From       | Allowed To                  |
|------------|-----------------------------|
| candidate  | verified, published, rejected |
| verified   | published, rejected         |
| published  | rejected                    |
| rejected   | — (manual SQL reset if needed) |

> Note: Allowing `published → rejected` provides a lightweight “unpublish” valve without resurrecting the candidate.

## Future Considerations

- Bulk actions (multi-select verify/publish) once event volumes grow.
- Surfacing audit trail entries (e.g., referencing `ai_logs`) next to each promotion.
- Resolving the legacy `event_raw.processing_state` check constraint mismatch (`normalized/error_norm` vs `pending/enriched/error`).
- Public-facing event exposure once published rows are ready for end-users.

