-- 019_events_candidate.sql
-- Stores normalized event candidates produced by the normalization pipeline (ES-0.3).

CREATE TABLE IF NOT EXISTS public.events_candidate (
    id BIGSERIAL PRIMARY KEY,
    event_source_id BIGINT NOT NULL REFERENCES public.event_sources (id),
    event_raw_id BIGINT NOT NULL REFERENCES public.event_raw (id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    start_time_utc TIMESTAMPTZ NOT NULL,
    end_time_utc TIMESTAMPTZ,
    location_text TEXT,
    url TEXT,
    source_key TEXT NOT NULL,
    ingest_hash TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'candidate',
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

CREATE UNIQUE INDEX IF NOT EXISTS events_candidate_source_hash_idx
    ON public.events_candidate (event_source_id, ingest_hash);

CREATE INDEX IF NOT EXISTS events_candidate_start_time_idx
    ON public.events_candidate (start_time_utc DESC);

CREATE INDEX IF NOT EXISTS events_candidate_state_idx
    ON public.events_candidate (state);

COMMENT ON TABLE public.events_candidate IS 'Normalized event candidates ready for downstream publication.';
COMMENT ON COLUMN public.events_candidate.state IS 'State machine placeholder (candidate, verified, rejected, etc.).';




