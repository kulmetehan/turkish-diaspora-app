-- 013_news_location_mentions.sql
-- Adds location_mentions JSONB column for AI-provided raw detections.

ALTER TABLE IF EXISTS public.raw_ingested_news
    ADD COLUMN IF NOT EXISTS location_mentions JSONB NOT NULL DEFAULT '[]'::jsonb;


