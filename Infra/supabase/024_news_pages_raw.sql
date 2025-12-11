-- 024_news_pages_raw.sql
-- Create raw HTML storage for AI news extraction.

CREATE TABLE IF NOT EXISTS public.news_pages_raw (
    id BIGSERIAL PRIMARY KEY,
    news_source_key TEXT NOT NULL,
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

CREATE UNIQUE INDEX IF NOT EXISTS news_pages_raw_source_hash_idx
    ON public.news_pages_raw (news_source_key, content_hash);

CREATE INDEX IF NOT EXISTS news_pages_raw_state_idx
    ON public.news_pages_raw (processing_state, fetched_at);

CREATE INDEX IF NOT EXISTS news_pages_raw_source_key_idx
    ON public.news_pages_raw (news_source_key);

COMMENT ON TABLE public.news_pages_raw IS 'Raw HTML pages fetched for AI-powered news article extraction.';
COMMENT ON COLUMN public.news_pages_raw.news_source_key IS 'Source key identifier from news_sources.yml config (e.g., scrape_turksemedia_nl).';
COMMENT ON COLUMN public.news_pages_raw.content_hash IS 'sha1 hash of news_source_key + page_url + response_body for dedupe.';
COMMENT ON COLUMN public.news_pages_raw.processing_state IS 'pending|extracted|error_fetch|error_extract';


