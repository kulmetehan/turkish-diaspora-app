-- 067_update_events_public_view.sql
-- Updates events_public view to include event_category from events_candidate.

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
    ec.event_category,  -- NEW: event-specific category
    ec.created_at,
    ec.updated_at,
    er.category_key,  -- Keep for backward compat (location category from enrichment)
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



