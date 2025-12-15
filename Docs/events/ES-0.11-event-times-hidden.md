# ES-0.11 — Event Times Temporarily Hidden in UI

## Status
**Active** — Event times are currently hidden in the frontend UI

## Overview

Event times (`start_time_utc` and `end_time_utc`) are still extracted and stored by the backend pipeline, but they are **not displayed** in the frontend UI. Only event dates are shown to users.

## Reason

The AI extraction of event times from detail pages is not yet reliable enough. Many events have unclear or incorrect start times because:

1. Event times are often not present on the initial scraped listing page
2. When the system scrapes the detail page behind the event URL, the AI extraction of times frequently fails or produces incorrect results
3. Multiple events have unclear start times that would confuse users

## Current Behavior

### Backend
- ✅ Event times are still extracted by `event_ai_extractor_bot.py`
- ✅ Times are stored in `event_raw.start_at` and `event_raw.end_at`
- ✅ Times are exposed via the API in `start_time_utc` and `end_time_utc` fields
- ✅ The pipeline continues to work normally

### Frontend
- ✅ Only dates are displayed (e.g., "Mon 15 Jan" or "Mon 15 Jan – Tue 16 Jan")
- ✅ Times are hidden in:
  - `EventCard` component
  - `EventDetailOverlay` component
  - Admin pages (for consistency)

## Implementation Details

The change is implemented in `Frontend/src/components/events/eventFormatters.ts`:

- `formatEventDateRange()` function now only returns date strings
- All time formatting logic has been temporarily disabled
- Function includes documentation explaining why times are hidden

## Related Files

- `Frontend/src/components/events/eventFormatters.ts` - Date formatting function
- `Frontend/src/components/events/EventCard.tsx` - Uses `formatEventDateRange()`
- `Frontend/src/components/events/EventDetailOverlay.tsx` - Uses `formatEventDateRange()`
- `Frontend/src/pages/AdminEventsPage.tsx` - Admin page showing dates only
- `Backend/app/workers/event_ai_extractor_bot.py` - Extracts event times (still active)

## Future Work

Once the AI extraction of event times from detail pages improves:

1. Re-enable time display in `formatEventDateRange()`
2. Test with real events to ensure times are accurate
3. Update this documentation to reflect the change

## Rollback

If needed, to re-enable time display:

1. Restore the original time formatting logic in `formatEventDateRange()`
2. Restore `toLocaleString()` in `AdminEventsPage.tsx` (currently uses `toLocaleDateString()`)
3. Update or remove this documentation





