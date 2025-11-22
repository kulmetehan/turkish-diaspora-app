-- 014_news_location_tags.sql
-- Adds deterministic tagging outputs to raw_ingested_news.

ALTER TABLE IF EXISTS public.raw_ingested_news
    ADD COLUMN IF NOT EXISTS location_tag TEXT,
    ADD COLUMN IF NOT EXISTS location_context JSONB;

