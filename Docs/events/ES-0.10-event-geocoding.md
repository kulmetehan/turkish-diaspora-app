# ES-0.10 — Event Geocoding

## Overview

Event geocoding converts location text (e.g., "Theater Zuidplein, Grote Zaal, Gooilandsingel 95, 3083 DP Rotterdam") into geographic coordinates (`lat`, `lng`) and country information. This enables events to be displayed on the map in the frontend.

Geocoding happens after normalization (ES-0.3) and AI enrichment (ES-0.4), and is a prerequisite for events to appear in the public API with map coordinates.

## Pipeline Position

```
event_raw (processing_state=enriched)
   │
   └─ EventGeocodingBot ──► events_candidate (lat, lng, country)
                              │
                              └─► events_public view (filters by country='netherlands')
```

## Database Schema

The `events_candidate` table includes:

- `lat` (DECIMAL) — Latitude coordinate
- `lng` (DECIMAL) — Longitude coordinate  
- `country` (TEXT) — Normalized country name (lowercase English, e.g., "netherlands", "belgium")

Events without coordinates (`lat IS NULL AND lng IS NULL`) are not displayed on the map in the frontend.

## Geocoding Service

**Path**: `Backend/services/nominatim_service.py`

The `NominatimService` uses the OpenStreetMap Nominatim API to geocode addresses.

### Features

1. **Rate Limiting**: Enforces 1 request/second to comply with Nominatim usage policy
2. **Europe Bounds Validation**: Only accepts coordinates within Europe bounds:
   - Latitude: 35.0 to 72.0
   - Longitude: -10.0 to 40.0
3. **Country Blocking**: Blocks events from USA, Canada, Mexico (too far from Netherlands)
4. **Country Normalization**: Converts country names to English (e.g., "nederland" → "netherlands")
5. **City-Country Validation**: Validates known cities against expected countries (e.g., "Stuttgart" should be "germany", not "netherlands")

### Fallback Strategy

If the initial geocoding query fails, the service automatically tries simplified versions of the address:

1. **Original address** (first attempt)
2. **Simplified address** (removes venue/room names like "Grote Zaal", "Rode Zaal")
3. **Street + Postcode + City** (extracts essential address parts)
4. **Postcode + City** (minimal address)

**Example**:
- Original: `"Theater Zuidplein, Grote Zaal, Gooilandsingel 95, 3083 DP Rotterdam"`
- Simplified: `"Theater Zuidplein, Gooilandsingel 95, 3083 DP Rotterdam"` (removes "Grote Zaal")
- Fallback: `"Gooilandsingel 95, 3083 DP Rotterdam"`
- Final fallback: `"3083 DP Rotterdam"`

This fallback strategy significantly improves geocoding success rates for addresses that include venue-specific details (room names, hall names) that Nominatim may not recognize.

### Address Simplification

The `_simplify_address_for_geocoding()` function:

- Removes common venue/room patterns:
  - `", Grote Zaal"`, `", Rode Zaal"`, `", Kleine Zaal"` (hall names)
  - `", X Zaal"` (any hall name pattern)
  - `"| ANTWERPEN, IKON"` (parts after `|` separator)
- Extracts postcode patterns: `\d{4}\s*[A-Z]{2}` (e.g., "3083 DP")
- Generates progressively simpler queries until one succeeds

## Worker: `event_geocoding_bot`

**Path**: `Backend/app/workers/event_geocoding_bot.py`

### Responsibilities

1. Fetches events from `events_candidate` where `lat IS NULL AND lng IS NULL`
2. Normalizes location text (removes incorrect country suffixes, e.g., "Hannover Netherlands" → "Hannover")
3. Calls `NominatimService.geocode()` with fallback strategy
4. Updates `events_candidate` with `lat`, `lng`, and `country`
5. Logs all geocoding attempts and results

### Location Normalization

Before geocoding, the bot normalizes location text:

- **Foreign City Detection**: Detects known foreign cities (Hannover, Stuttgart, Offenbach, etc.)
- **Country Suffix Removal**: Removes incorrect "Netherlands" suffixes from foreign cities
- **City Key Detection**: Attempts to detect city from location text for logging purposes

**Example**: `"Hannover Netherlands"` → `"Hannover"` (prevents wrong geocoding to Netherlands)

### Usage

```bash
cd Backend
source .venv/bin/activate
python -m app.workers.event_geocoding_bot --limit 50
```

**Parameters**:
- `--limit`: Maximum number of events to geocode (default: 50)
- `--worker-run-id`: Optional UUID of existing worker run

### Output

The worker logs:
- `event_geocoding_success`: Successfully geocoded event with coordinates and country
- `event_geocoding_failed`: Failed geocoding (all fallback attempts exhausted)
- `event_geocoding_error`: Exception during geocoding
- `geocoding_success_with_fallback`: Success using a fallback query (indicates which attempt succeeded)

**Counters**:
- `total`: Number of events processed
- `geocoded`: Successfully geocoded events
- `errors`: Failed geocoding attempts

## Events Public View

The `events_public` SQL view filters events based on geocoding status:

```sql
-- Events with coordinates in Netherlands
(ec.country IS NOT NULL AND (ec.country = 'netherlands' OR ec.country = 'nederland'))

-- OR events without coordinates that are not blocked
OR (ec.country IS NULL AND ec.lat IS NULL AND ec.lng IS NULL AND NOT is_location_blocked(ec.location_text))
```

This means:
- **Geocoded events in Netherlands**: Always visible
- **Geocoded events outside Netherlands**: Filtered out (not shown in public API)
- **Ungeocoded events**: Only visible if location is not blocked

## Frontend Integration

**Path**: `Frontend/src/components/events/EventMapView.tsx`

The frontend:
1. Filters events using `eventHasCoordinates()` (checks for valid `lat`/`lng` as numbers)
2. Converts events to `LocationMarker` format
3. Computes map center:
   - **Single event**: Centers on event with zoom 14
   - **Multiple events**: Computes average center with zoom 12
4. Passes markers to `MapView` component for rendering

Events without coordinates show a message: *"Er zijn nog geen events met bekende kaartlocaties."*

## Troubleshooting

### Events Not Appearing on Map

1. **Check geocoding status**:
   ```sql
   SELECT id, title, location_text, lat, lng, country
   FROM events_candidate
   WHERE id = <event_id>;
   ```

2. **Verify events_public view**:
   ```sql
   SELECT id, title, lat, lng, country
   FROM events_public
   WHERE start_time_utc >= NOW()
     AND lat IS NOT NULL AND lng IS NOT NULL;
   ```

3. **Check API response**: Verify `/api/v1/events` returns `lat`/`lng` as numbers (not strings)

4. **Frontend console**: Check browser console for `[EventMapView]` debug logs

### Geocoding Failures

Common reasons for geocoding failures:

1. **No Nominatim results**: Address too vague or not in OSM database
   - **Solution**: Try manual geocoding or improve address in source data

2. **Out of bounds**: Coordinates outside Europe (e.g., "Houston" → USA)
   - **Expected**: These events are intentionally blocked

3. **Blocked country**: Event in USA/Canada/Mexico
   - **Expected**: These events are intentionally blocked

4. **Address too specific**: Includes venue-specific details Nominatim doesn't recognize
   - **Solution**: Fallback strategy should handle this automatically

### Improving Geocoding Success Rate

1. **Run geocoding bot regularly**: Process new events as they're added
   ```bash
   python -m app.workers.event_geocoding_bot --limit 200
   ```

2. **Monitor logs**: Check for patterns in failed geocoding (e.g., specific venue names)
   ```bash
   # Check recent geocoding failures
   grep "event_geocoding_failed" logs/worker.log | tail -20
   ```

3. **Manual correction**: For important events, manually update coordinates in database:
   ```sql
   UPDATE events_candidate
   SET lat = 52.1029379, lng = 5.0830494, country = 'netherlands'
   WHERE id = <event_id>;
   ```

## Environment Configuration

No special environment variables are required for geocoding. The service uses:
- Default Nominatim endpoint: `https://nominatim.openstreetmap.org/search`
- Rate limit: 1 request/second (enforced automatically)
- User agent: `TurkishDiasporaApp/1.0 (contact: m.kul@lamarka.nl)`

Optional overrides (in `Backend/.env`):
- `NOMINATIM_TIMEOUT_S`: Request timeout (default: 5 seconds)
- `NOMINATIM_RATE_LIMIT_DELAY`: Minimum delay between requests (default: 1.0 second)
- `NOMINATIM_USER_AGENT`: Custom user agent string

## Related Documentation

- **ES-0.3**: Event Normalization (prepares location_text)
- **ES-0.4**: Event AI Enrichment (enriches event metadata)
- **ES-0.6**: Public Event API (exposes geocoded events)
- **Docs/discovery-osm.md**: OSM integration patterns (similar rate limiting)

## Implementation History

- **2025-12-13**: Added fallback strategy for address simplification
  - Improves geocoding success rate for addresses with venue-specific details
  - Automatically tries simplified versions if initial query fails
  - Logs which fallback attempt succeeded for debugging
