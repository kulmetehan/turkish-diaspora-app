-- 012_news_classification.sql
-- N2.1 News Classification Pipeline
-- Adds AI classification columns to raw_ingested_news and links ai_logs to news items.

-- Raw news classification outputs (nullable to avoid breaking existing rows)
ALTER TABLE IF EXISTS public.raw_ingested_news
    ADD COLUMN IF NOT EXISTS relevance_diaspora DOUBLE PRECISION;

ALTER TABLE IF EXISTS public.raw_ingested_news
    ADD COLUMN IF NOT EXISTS relevance_nl DOUBLE PRECISION;

ALTER TABLE IF EXISTS public.raw_ingested_news
    ADD COLUMN IF NOT EXISTS relevance_tr DOUBLE PRECISION;

ALTER TABLE IF EXISTS public.raw_ingested_news
    ADD COLUMN IF NOT EXISTS relevance_geo DOUBLE PRECISION;

ALTER TABLE IF EXISTS public.raw_ingested_news
    ADD COLUMN IF NOT EXISTS topics JSONB;

ALTER TABLE IF EXISTS public.raw_ingested_news
    ADD COLUMN IF NOT EXISTS classified_at TIMESTAMPTZ;

ALTER TABLE IF EXISTS public.raw_ingested_news
    ADD COLUMN IF NOT EXISTS classified_by TEXT;

-- ai_logs now optionally references news_id (in addition to location_id)
ALTER TABLE IF EXISTS public.ai_logs
    ADD COLUMN IF NOT EXISTS news_id BIGINT REFERENCES public.raw_ingested_news(id);


