-- 045_add_event_coordinates.sql
-- Adds lat/lng columns to event tables and updates events_public view to expose coordinates

-- Add coordinates to event_raw
ALTER TABLE IF EXISTS public.event_raw
    ADD COLUMN IF NOT EXISTS lat NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS lng NUMERIC(10, 7);

-- Add coordinates to events_candidate
ALTER TABLE IF EXISTS public.events_candidate
    ADD COLUMN IF NOT EXISTS lat NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS lng NUMERIC(10, 7);

-- Add indexes for geographic queries
CREATE INDEX IF NOT EXISTS event_raw_coordinates_idx
    ON public.event_raw (lat, lng)
    WHERE lat IS NOT NULL AND lng IS NOT NULL;

CREATE INDEX IF NOT EXISTS events_candidate_coordinates_idx
    ON public.events_candidate (lat, lng)
    WHERE lat IS NOT NULL AND lng IS NOT NULL;

-- Update events_public view to include coordinates
-- IMPORTANT: Add new columns at the END to maintain view compatibility
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
    es.city_key,
    ec.lat,
    ec.lng
FROM public.events_candidate ec
JOIN public.event_raw er ON er.id = ec.event_raw_id
LEFT JOIN public.event_sources es ON es.id = ec.event_source_id
WHERE er.processing_state = 'enriched';

COMMENT ON COLUMN public.event_raw.lat IS 'Latitude coordinate from geocoding (NULL if not geocoded yet)';
COMMENT ON COLUMN public.event_raw.lng IS 'Longitude coordinate from geocoding (NULL if not geocoded yet)';
COMMENT ON COLUMN public.events_candidate.lat IS 'Latitude coordinate from geocoding (NULL if not geocoded yet)';
COMMENT ON COLUMN public.events_candidate.lng IS 'Longitude coordinate from geocoding (NULL if not geocoded yet)';

