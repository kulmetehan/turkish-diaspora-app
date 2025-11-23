## ES-0.7 — Event Sources & Selector Schema

### Overview

The events ingest stack promotes raw scraper output (`event_raw`) through normalization, enrichment, and finally to the public API. Every source is defined in `event_sources` with a JSONB `selectors` payload that tells `EventScraperService` how to parse the upstream site. This document summarizes the supported selector schema and the steps required to onboard a new source.

### Selector schema

#### Common keys

| Key | Type | Notes |
| --- | ---- | ----- |
| `format` | `html` \| `rss` \| `json` \| `json_ld` | Determines the parser. Defaults to `html`. |
| `timezone` | string | Optional IANA zone used when timestamps are naive. |
| `datetime_format` | string | Optional human-friendly format (`DD MMMM YYYY HH:mm` etc.); converted to `strptime`. |
| `locale` | string | Currently used for Dutch month name normalization (`nl_NL`). |

#### HTML (`format: "html"`)

| Key | Required | Description |
| --- | --- | --- |
| `item_selector` | ✅ | CSS selector that returns the repeating card/container node. |
| `title_selector` | ✅ | CSS selector relative to the item node. |
| `url_selector` | Optional | CSS selector (`.cta@href`) supporting `selector@attr`. |
| `date_selector` | Optional but recommended | Extracts the date portion. |
| `time_selector` | Optional | Combined with `date_selector` before parsing. |
| `description_selector`, `location_selector`, `image_selector`, `venue_selector` | Optional | Additional metadata. |

Tips:

- Use stable classes (`.mec-event-article`) rather than generated IDs.
- `time_selector` enables “date + time” parsing even when plugins split the values.

#### JSON API (`format: "json"`)

Existing keys remain unchanged:

- `items_path`, `title_key`, `url_key`, `start_key`, `description_key`, `location_key`, `venue_key`, `image_key`.
- `timezone`, `datetime_format`, and `locale` are now honored for JSON rows as well.

#### JSON-LD (`format: "json_ld"`)

| Key | Required | Description |
| --- | --- | --- |
| `script_selector` | Optional (default `script[type='application/ld+json']`) | Limits which scripts to parse. |
| `json_items_path` | Optional (default root) | Path such as `$.@graph`. |
| `json_type_filter` | Optional (default `Event`) | Filters objects by `@type`. |
| `json_title_field`, `json_url_field`, `json_start_field`, `json_end_field`, `json_location_field`, `json_image_field`, `json_description_field` | Optional, default to sensible schema.org fields. |

JSON-LD rows are inserted with `detected_format="json"` for compatibility with the existing enum.

### Adding a new source

1. **Inspect the site**
   - Prefer server-rendered HTML. If the page is JS-only, look for a JSON API (`/wp-json/`, `/api/events`) or JSON-LD blocks.
   - Capture CSS selectors for the repeating card and each data field. Verify the HTML in desktop and mobile layouts.
2. **Update event_sources**
   - Add a row via an SQL migration (preferred) or the admin API.
   - Fill `city_key`, `interval_minutes`, and the selectors JSON.
   - For HTML, include `time_selector`, `datetime_format`, `locale`, and `timezone` when parsing non-ISO date strings (e.g., Dutch month names).
3. **Deploy migrations**
   - Run `psql`/Supabase migrations so workers can discover the new source.
4. **Run the workers locally (or via GitHub Actions)**
   ```bash
   cd Backend
   .venv/bin/python -m app.workers.event_scraper_bot --limit 20
   .venv/bin/python -m app.workers.event_normalization_bot --limit 200
   .venv/bin/python -m app.workers.event_enrichment_bot --limit 200
   ```
   Use `required_permissions=['all','network']` inside Cursor if the sandbox blocks `.env` access.
5. **Verify ingestion**
   ```sql
   -- event_raw status
   SELECT processing_state, COUNT(*) FROM event_raw GROUP BY 1;

   -- normalized candidates
   SELECT COUNT(*) FROM events_candidate;

   -- public view sample
   SELECT title, city_key, start_time_utc FROM events_public ORDER BY start_time_utc LIMIT 5;
   ```
   Then hit `/api/v1/events?limit=5` (optionally filter `city=rotterdam`).
6. **Monitoring**
   - `worker_runs` stores counters (`inserted_items`, `errors`) for each bot.
   - `event_sources.last_success_at/last_error` shows per-source health.

### Current sources (post-upgrade)

| Key | Site | Format | Notes |
| --- | ---- | ------ | ----- |
| `sahmeran_events` | sahmeran.nl/events | HTML | JetEngine cards, ISO datetime in `<time datetime>`. |
| `ahoy_events` | ahoy.nl/agenda | HTML (JSON-LD fallback ready) | Agenda cards with `<time>` nodes. |
| `ajda_events` | ajda.nl/events-list/ | HTML | Modern Events Calendar; uses Dutch month names + split time fields. |
| `ediz_events` | edizevents.nl/agenda/ | HTML | Elementor cards; timezone hint ensures correct UTC conversion. |

These rows live in `Infra/supabase/017_event_sources.sql` and will be replayed via migrations.

### Verification checklist

1. Run the three workers with `--limit` flags (scraper → normalization → enrichment).
2. Watch worker logs for `event_scraper_source_success` and `event_enrichment_success`.
3. Inspect DB counts (`event_raw`, `events_candidate`, `events_public`).
4. Call `/api/v1/events` (and filter by `city` / `date` to confirm indexing).
5. If selectors stop matching, inspect the site, update the JSON, and re-run the pipeline.

