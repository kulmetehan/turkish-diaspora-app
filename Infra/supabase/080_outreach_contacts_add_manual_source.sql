-- 080_outreach_contacts_add_manual_source.sql
-- Add 'manual' source type to outreach_contacts table
-- Allows admin-created contacts to be marked with source='manual'

-- Drop existing CHECK constraint
ALTER TABLE public.outreach_contacts
DROP CONSTRAINT IF EXISTS outreach_contacts_source_check;

-- Recreate CHECK constraint with 'manual' included
ALTER TABLE public.outreach_contacts
ADD CONSTRAINT outreach_contacts_source_check
CHECK (source IN ('osm', 'website', 'google', 'social', 'manual'));

-- Update comment to reflect new source type
COMMENT ON COLUMN public.outreach_contacts.source IS 'Source of contact discovery: osm (OSM tags), website (website scraping), google (Google Places API), social (social media bio), manual (admin-created).';

