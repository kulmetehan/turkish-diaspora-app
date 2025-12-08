-- 037_google_business_sync.sql
-- Google Business sync infrastructure (EPIC-3)

-- Add optional Google Business fields to locations table
ALTER TABLE public.locations 
ADD COLUMN IF NOT EXISTS google_business_id TEXT,
ADD COLUMN IF NOT EXISTS google_business_metadata JSONB;

CREATE INDEX IF NOT EXISTS idx_locations_google_business_id ON public.locations(google_business_id) WHERE google_business_id IS NOT NULL;

-- Google Business sync tracking table
CREATE TABLE IF NOT EXISTS public.google_business_sync (
    id BIGSERIAL PRIMARY KEY,
    business_account_id BIGINT NOT NULL REFERENCES public.business_accounts(id) ON DELETE CASCADE,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    google_business_id TEXT NOT NULL, -- Google Business Profile ID
    access_token_encrypted TEXT, -- Encrypted access token
    refresh_token_encrypted TEXT, -- Encrypted refresh token
    token_expires_at TIMESTAMPTZ,
    sync_status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'synced', 'error', 'disconnected'
    last_synced_at TIMESTAMPTZ,
    sync_error TEXT,
    sync_metadata JSONB, -- Additional sync information
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(location_id) -- One sync per location
);

CREATE INDEX IF NOT EXISTS idx_google_business_sync_account ON public.google_business_sync(business_account_id);
CREATE INDEX IF NOT EXISTS idx_google_business_sync_location ON public.google_business_sync(location_id);
CREATE INDEX IF NOT EXISTS idx_google_business_sync_status ON public.google_business_sync(sync_status);
CREATE INDEX IF NOT EXISTS idx_google_business_sync_google_id ON public.google_business_sync(google_business_id);

-- Update locations.google_business_id when sync is created/updated
CREATE OR REPLACE FUNCTION update_location_google_business_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.sync_status = 'synced' THEN
        UPDATE public.locations
        SET google_business_id = NEW.google_business_id
        WHERE id = NEW.location_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_location_google_business_id_trigger
    AFTER INSERT OR UPDATE OF sync_status, google_business_id ON public.google_business_sync
    FOR EACH ROW
    WHEN (NEW.sync_status = 'synced')
    EXECUTE FUNCTION update_location_google_business_id();

COMMENT ON TABLE public.google_business_sync IS 'Tracks Google Business sync status and OAuth tokens';
COMMENT ON COLUMN public.locations.google_business_id IS 'Google Business Profile ID if synced';
COMMENT ON COLUMN public.locations.google_business_metadata IS 'Additional Google Business data (hours, photos, etc.)';







