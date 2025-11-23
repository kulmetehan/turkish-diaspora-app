-- 020_events_public_api.sql
-- Adds city metadata for event sources, supporting indexes, and a canonical
-- view that powers the public /api/v1/events endpoint.

ALTER TABLE IF EXISTS public.event_sources
    ADD COLUMN IF NOT EXISTS city_key TEXT;

CREATE INDEX IF NOT EXISTS event_sources_city_key_idx
    ON public.event_sources (city_key);

CREATE INDEX IF NOT EXISTS event_raw_category_processing_state_idx
    ON public.event_raw (category_key, processing_state);

CREATE INDEX IF NOT EXISTS events_candidate_event_raw_id_idx
    ON public.events_candidate (event_raw_id);

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
    es.city_key
FROM public.events_candidate ec
JOIN public.event_raw er ON er.id = ec.event_raw_id
LEFT JOIN public.event_sources es ON es.id = ec.event_source_id
WHERE er.processing_state = 'enriched';

