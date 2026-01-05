-- Migration 100: Add music content type to feed_curated_content
-- Extends feed_curated_content to support storing Spotify tracks

-- Update the check constraint to include 'music' as a valid content_type
ALTER TABLE public.feed_curated_content
    DROP CONSTRAINT IF EXISTS feed_curated_content_content_type_check;

ALTER TABLE public.feed_curated_content
    ADD CONSTRAINT feed_curated_content_content_type_check
    CHECK (content_type IN ('news', 'events', 'location_stats', 'music'));

-- Update comment to reflect new content type
COMMENT ON COLUMN public.feed_curated_content.content_type IS 'Type of curated content: news, events, location_stats, music';

