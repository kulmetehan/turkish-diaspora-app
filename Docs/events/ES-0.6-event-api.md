# ES-0.6 — Public Event API

## Overview

Expose a read-only `/api/v1/events` endpoint that lists *published* diaspora events.
Published = normalized candidate rows whose source payloads passed AI enrichment
(`event_raw.processing_state = 'enriched'`). Only upcoming events (start time in
the future) are returned by default.

Back-end storage additions:

- `event_sources.city_key` (optional) to map sources to cities.
- Supporting indexes on `event_raw(category_key, processing_state)` and
  `events_candidate(event_raw_id)`.
- View `events_public` joining `events_candidate`, `event_raw`, and `event_sources`.

## Endpoint

`GET /api/v1/events`

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `city` | `string?` | Optional city key from `Infra/config/cities.yml` (`rotterdam`, `den_haag`, …). |
| `date_from` | `YYYY-MM-DD?` | Inclusive UTC start date. |
| `date_to` | `YYYY-MM-DD?` | Inclusive UTC end date (must be >= `date_from`). |
| `categories` | `string[]?` | Repeated category keys (`community`, `religion`, `culture`, `business`, `education`, `sports`, `other`). |
| `limit` | `int` | Page size (default `20`, max `100`). |
| `offset` | `int` | Page offset (default `0`). |

Rules:

- If no date filters are provided, the service defaults to `start_time_utc >= NOW()`
  to show upcoming events only.
- Unknown city/category keys return `HTTP 400`.

### Response Shape

```
{
  "items": [
    {
      "id": 42,
      "title": "Rotterdam Community Meetup",
      "description": "Networking event…",
      "start_time_utc": "2025-01-12T18:00:00Z",
      "end_time_utc": "2025-01-12T21:00:00Z",
      "city_key": "rotterdam",
      "category_key": "community",
      "location_text": "Rotterdam Centrum",
      "url": "https://example.com/meetup",
      "source_key": "rotterdam_culture",
      "summary_ai": "Short AI-generated summary.",
      "updated_at": "2025-01-05T10:30:00Z"
    }
  ],
  "total": 128,
  "limit": 20,
  "offset": 0
}
```

## Implementation Notes

- Router: `Backend/api/routers/events.py`
  - Validates inputs, normalizes city/category keys, enforces pagination limits.
- Service: `Backend/services/events_public_service.py`
  - Queries `events_public`, applies filters, paginates, and returns DTOs.
- Response models: `Backend/app/models/events_public.py`
  - Mirrors `NewsListResponse` with `items/total/limit/offset`.
- Documentation + tests ensure parity with locations/news endpoints.

## Testing

- `Backend/tests/test_events_api.py` covers:
  - Happy path serialization.
  - City/category normalization.
  - Validation errors (unknown city/category, invalid date range).

