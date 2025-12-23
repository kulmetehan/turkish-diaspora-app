-- 066_add_event_category.sql
-- Adds event_category column to events_candidate table for event-specific categories.

ALTER TABLE public.events_candidate
ADD COLUMN IF NOT EXISTS event_category TEXT;

CREATE INDEX IF NOT EXISTS events_candidate_event_category_idx
ON public.events_candidate(event_category);

COMMENT ON COLUMN public.events_candidate.event_category IS 
'Event-specific category: club, theater, concert, or familie. Separate from location categories.';



