-- 069_prefer_event_category.sql
-- Updates events_public view to prefer event_category over category_key.
-- This ensures that verification category (event_category) takes priority over enrichment category (category_key).

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
    ec.event_category,  -- event-specific category from verification
    ec.created_at,
    ec.updated_at,
    -- Prefer event_category over category_key for public API
    COALESCE(ec.event_category, er.category_key) AS category_key,
    er.summary_ai,
    er.confidence_score,
    er.language_code,
    COALESCE(
        extract_city_key_from_location(ec.location_text),
        CASE
            WHEN ec.country = 'netherlands' OR ec.country = 'nederland'
            THEN es.city_key
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
  AND ec.state = 'published'
  AND (
    (ec.country IS NOT NULL AND (ec.country = 'netherlands' OR ec.country = 'nederland'))
    OR
    (ec.country IS NULL AND ec.lat IS NULL AND ec.lng IS NULL
     AND NOT is_location_blocked(ec.location_text))
  );

COMMENT ON VIEW public.events_public IS 'Public events view. Shows only published events (state = published) that are Netherlands events (country = netherlands or nederland) for geocoded events. For non-geocoded events, only blocks clearly invalid patterns (e.g., "Washington, Netherlands"). Foreign cities are allowed until geocoding bot processes them. City_key only uses source city_key when country is explicitly Netherlands (not NULL) to avoid wrong assignments for foreign events or ungeocoded events. Category_key prefers event_category (from verification) over category_key (from enrichment).';


