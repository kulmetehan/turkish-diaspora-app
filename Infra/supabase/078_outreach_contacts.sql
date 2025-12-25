-- 078_outreach_contacts.sql
-- Outreach Contacts System
-- Database schema for discovered contact information for locations
-- Part of pre-claim outreach implementation plan (Fase 5.1)

-- 1. Create outreach_contacts table
CREATE TABLE IF NOT EXISTS public.outreach_contacts (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('osm', 'website', 'google', 'social')),
    confidence_score INTEGER NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 100),
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(location_id, email) -- One contact per location-email combination
);

-- 2. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_outreach_contacts_location ON public.outreach_contacts(location_id);
CREATE INDEX IF NOT EXISTS idx_outreach_contacts_email ON public.outreach_contacts(email);
CREATE INDEX IF NOT EXISTS idx_outreach_contacts_source ON public.outreach_contacts(source);
CREATE INDEX IF NOT EXISTS idx_outreach_contacts_confidence ON public.outreach_contacts(confidence_score) WHERE confidence_score >= 50;

-- 3. Add table and column comments for documentation
COMMENT ON TABLE public.outreach_contacts IS 'Discovered contact information for locations. Used for outreach email discovery. One entry per location-email combination.';
COMMENT ON COLUMN public.outreach_contacts.location_id IS 'Location for which contact was discovered.';
COMMENT ON COLUMN public.outreach_contacts.email IS 'Discovered email address. UNIQUE constraint with location_id ensures one entry per location-email combination.';
COMMENT ON COLUMN public.outreach_contacts.source IS 'Source of contact discovery: osm (OSM tags), website (website scraping), google (Google Places API), social (social media bio).';
COMMENT ON COLUMN public.outreach_contacts.confidence_score IS 'Confidence score (0-100) for the discovered contact. Higher scores indicate more reliable sources.';
COMMENT ON COLUMN public.outreach_contacts.discovered_at IS 'Timestamp when contact was discovered.';

