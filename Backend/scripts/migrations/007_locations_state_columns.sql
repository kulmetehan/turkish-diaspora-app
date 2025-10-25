-- Ensure locations has automation-friendly columns
ALTER TABLE IF EXISTS locations
    ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ NULL;

ALTER TABLE IF EXISTS locations
    ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ NULL;

ALTER TABLE IF EXISTS locations
    ADD COLUMN IF NOT EXISTS is_retired BOOLEAN DEFAULT FALSE;


