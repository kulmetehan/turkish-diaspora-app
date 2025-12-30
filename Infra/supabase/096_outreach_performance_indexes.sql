-- 096_outreach_performance_indexes.sql
-- Performance indexes for outreach contacts queries
-- Optimizes queries that join outreach_contacts with locations and outreach_emails

-- Index for outreach_emails lookups by location_id and created_at
-- Used in DISTINCT ON queries to get latest email status per location
CREATE INDEX IF NOT EXISTS idx_outreach_emails_location_created 
    ON public.outreach_emails(location_id, created_at DESC);

COMMENT ON INDEX idx_outreach_emails_location_created IS 'Optimizes queries that fetch latest email status per location using DISTINCT ON. Used in outreach contacts listing endpoint.';

