-- 065_fix_events_public_state_filter.sql
-- Fix events_public view to filter by state = 'published'
-- Problem: events_public view was showing all events with processing_state = 'enriched',
-- regardless of their state (candidate/verified/published/rejected). This meant admin
-- dashboard actions (verify/publish/reject) had no effect on frontend visibility.
-- Solution: Add state = 'published' filter to events_public view so only published
-- events appear on the frontend.

-- Update events_public view: add state filter for published events only
CREATE OR REPLACE VIEW public.events_public AS
SELECT
    ec.id,
    ec.event_source_id,
    ec.event_raw_id,
    ec.title,
    ec.description,
    ec.start_time_utc,
    ec.end_time_utc,
    ec.location_text,
    ec.url,
    ec.source_key,
    ec.ingest_hash,
    ec.state,
    ec.created_at,
    ec.updated_at,
    er.category_key,
    er.summary_ai,
    er.confidence_score,
    er.language_code,
    -- Extract city_key from location_text first
    -- Only use source city_key as fallback when country is explicitly Netherlands
    -- For NULL country or foreign countries, don't use source city_key to avoid wrong assignments
    COALESCE(
        extract_city_key_from_location(ec.location_text),
        CASE 
            -- Use source city_key only if country is explicitly Netherlands (not NULL)
            WHEN ec.country = 'netherlands' OR ec.country = 'nederland' 
            THEN es.city_key
            -- For NULL country or foreign countries, don't use source city_key
            ELSE NULL
        END
    ) AS city_key,
    ec.lat,
    ec.lng,
    ec.country
FROM public.events_candidate ec
JOIN public.event_raw er ON er.id = ec.event_raw_id
LEFT JOIN public.event_sources es ON es.id = ec.event_source_id
WHERE er.processing_state = 'enriched'
  AND ec.duplicate_of_id IS NULL
  AND ec.state = 'published'  -- Only show published events on frontend
  AND (
    -- For geocoded events: filter by country = 'netherlands' (accept both English and Dutch spelling)
    (ec.country IS NOT NULL AND (ec.country = 'netherlands' OR ec.country = 'nederland'))
    OR
    -- For non-geocoded events: only block clearly invalid patterns
    -- Allow standalone foreign cities to pass through until geocoding
    (ec.country IS NULL AND ec.lat IS NULL AND ec.lng IS NULL 
     AND NOT is_location_blocked(ec.location_text))
  );

COMMENT ON VIEW public.events_public IS 'Public events view. Shows only published events (state = published) that are Netherlands events (country = netherlands or nederland) for geocoded events. For non-geocoded events, only blocks clearly invalid patterns (e.g., "Washington, Netherlands"). Foreign cities are allowed until geocoding bot processes them. City_key only uses source city_key when country is explicitly Netherlands (not NULL) to avoid wrong assignments for foreign events or ungeocoded events.';

