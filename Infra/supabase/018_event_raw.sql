-- 018_event_raw.sql
-- Defines raw event ingest storage aligned with ES-0.2 Event Scraper Framework.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'event_raw_format'
    ) THEN
        CREATE TYPE public.event_raw_format AS ENUM ('html', 'rss', 'json');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.event_raw (
    id BIGSERIAL PRIMARY KEY,
    event_source_id BIGINT NOT NULL REFERENCES public.event_sources(id),
    title TEXT,
    description TEXT,
    location_text TEXT,
    venue TEXT,
    event_url TEXT,
    image_url TEXT,
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    detected_format event_raw_format NOT NULL,
    ingest_hash CHAR(40) NOT NULL,
    raw_payload JSONB NOT NULL,
    processing_state TEXT NOT NULL DEFAULT 'pending',
    processing_errors JSONB,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS event_raw_source_hash_idx
    ON public.event_raw (event_source_id, ingest_hash);

CREATE INDEX IF NOT EXISTS event_raw_source_idx
    ON public.event_raw (event_source_id);

CREATE INDEX IF NOT EXISTS event_raw_start_at_idx
    ON public.event_raw (start_at DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS event_raw_processing_state_idx
    ON public.event_raw (processing_state);

COMMENT ON TABLE public.event_raw IS 'Raw event payloads discovered by EventScraperBot.';
COMMENT ON COLUMN public.event_raw.ingest_hash IS 'sha1 dedupe hash constructed from source + url + datetime.';
COMMENT ON COLUMN public.event_raw.detected_format IS 'Input format used for parsing (html/rss/json).';
COMMENT ON COLUMN public.event_raw.raw_payload IS 'Original parsed payload (HTML node snapshot, feed entry, or JSON object).';




