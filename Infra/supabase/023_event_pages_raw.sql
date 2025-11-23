-- 023_event_pages_raw.sql
-- Create raw HTML storage for AI event extraction.

CREATE TABLE IF NOT EXISTS public.event_pages_raw (
    id BIGSERIAL PRIMARY KEY,
    event_source_id BIGINT NOT NULL REFERENCES public.event_sources(id),
    page_url TEXT NOT NULL,
    http_status INTEGER,
    response_headers JSONB,
    response_body TEXT NOT NULL,
    content_hash CHAR(40) NOT NULL,
    processing_state TEXT NOT NULL DEFAULT 'pending',
    processing_errors JSONB,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS event_pages_raw_source_hash_idx
    ON public.event_pages_raw (event_source_id, content_hash);

CREATE INDEX IF NOT EXISTS event_pages_raw_state_idx
    ON public.event_pages_raw (processing_state, fetched_at);

COMMENT ON TABLE public.event_pages_raw IS 'Raw HTML pages fetched for AI-powered event extraction.';
COMMENT ON COLUMN public.event_pages_raw.content_hash IS 'sha1 hash of source_id + page_url + response_body for dedupe.';
COMMENT ON COLUMN public.event_pages_raw.processing_state IS 'pending|extracted|error_fetch|error_extract';


