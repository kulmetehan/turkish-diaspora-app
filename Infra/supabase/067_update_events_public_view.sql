-- 067_update_events_public_view.sql
-- Updates events_public view to include image_url from event_raw.
-- This migration adds image_url support for event cards in the frontend.
-- Uses DROP/CREATE to avoid column rename conflicts.

DROP VIEW IF EXISTS public.events_public CASCADE;

CREATE VIEW public.events_public AS
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
    er.image_url,  -- Event poster/flyer image URL
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

COMMENT ON VIEW public.events_public IS 'Public events view. Shows only published events (state = published) that are Netherlands events (country = netherlands or nederland) for geocoded events. For non-geocoded events, only blocks clearly invalid patterns (e.g., "Washington, Netherlands"). Foreign cities are allowed until geocoding bot processes them. City_key only uses source city_key when country is explicitly Netherlands (not NULL) to avoid wrong assignments for foreign events or ungeocoded events. Includes image_url from event_raw for event poster/flyer images.';



