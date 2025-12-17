-- Migration: Update ediz_events source to point to ediz.nl instead of edizevents.nl
-- Ediz.nl is a one-page website with events in a carousel
-- Location is on the main page, but start times are on detail pages (ticket links)

UPDATE public.event_sources
SET
    base_url = 'https://ediz.nl',
    list_url = 'https://ediz.nl',
    updated_at = NOW()
WHERE key = 'ediz_events';

-- Verify the update
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.event_sources
        WHERE key = 'ediz_events'
        AND base_url = 'https://ediz.nl'
        AND list_url = 'https://ediz.nl'
    ) THEN
        RAISE EXCEPTION 'Failed to update ediz_events source';
    END IF;
END $$;

COMMENT ON TABLE public.event_sources IS 'Updated ediz_events to point to ediz.nl (2025-01-XX)';









