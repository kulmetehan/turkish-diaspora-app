-- 019_event_enrichment.sql
-- Adds AI enrichment fields to event_raw and links ai_logs to event rows.

ALTER TABLE IF EXISTS public.event_raw
    ADD COLUMN IF NOT EXISTS language_code TEXT,
    ADD COLUMN IF NOT EXISTS category_key TEXT,
    ADD COLUMN IF NOT EXISTS summary_ai TEXT,
    ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS enriched_by TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'event_raw_processing_state_check'
    ) THEN
        ALTER TABLE public.event_raw
            ADD CONSTRAINT event_raw_processing_state_check
            CHECK (processing_state IN ('pending', 'enriched', 'error'));
    END IF;
END
$$;

ALTER TABLE IF EXISTS public.ai_logs
    ADD COLUMN IF NOT EXISTS event_raw_id BIGINT REFERENCES public.event_raw(id) ON DELETE SET NULL;


