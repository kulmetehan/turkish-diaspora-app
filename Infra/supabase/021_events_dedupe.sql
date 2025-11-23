-- 021_events_dedupe.sql
-- Adds duplicate tracking fields to events_candidate for cross-source dedupe.

ALTER TABLE IF EXISTS public.events_candidate
    ADD COLUMN IF NOT EXISTS duplicate_of_id BIGINT REFERENCES public.events_candidate (id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS duplicate_score DOUBLE PRECISION;

CREATE INDEX IF NOT EXISTS events_candidate_duplicate_idx
    ON public.events_candidate (duplicate_of_id, state, start_time_utc DESC);

COMMENT ON COLUMN public.events_candidate.duplicate_of_id IS 'Self-reference when this candidate is a duplicate of another canonical event.';
COMMENT ON COLUMN public.events_candidate.duplicate_score IS 'Similarity score (0-1) capturing why this row was marked duplicate.';

-- Ensure events_public only exposes canonical (non-duplicate) events.
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
WHERE er.processing_state = 'enriched'
  AND ec.duplicate_of_id IS NULL;



