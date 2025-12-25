-- 080_location_claim_flags.sql
-- Location State Uitbreiden
-- Add claim-related flags to locations table
-- Part of claim-consent-outreach-implementation-plan (Stap 2.4)

-- 1. Add is_claimable column
ALTER TABLE public.locations
ADD COLUMN IF NOT EXISTS is_claimable BOOLEAN NOT NULL DEFAULT true;

-- 2. Add claimed_status column (syncs with token_location_claims.claim_status)
ALTER TABLE public.locations
ADD COLUMN IF NOT EXISTS claimed_status TEXT;

-- 3. Add removed_by_owner column
ALTER TABLE public.locations
ADD COLUMN IF NOT EXISTS removed_by_owner BOOLEAN NOT NULL DEFAULT false;

-- 4. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_locations_is_claimable ON public.locations(is_claimable) WHERE is_claimable = true;
CREATE INDEX IF NOT EXISTS idx_locations_claimed_status ON public.locations(claimed_status) WHERE claimed_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_locations_removed_by_owner ON public.locations(removed_by_owner) WHERE removed_by_owner = true;

-- 5. Add column comments for documentation
COMMENT ON COLUMN public.locations.is_claimable IS 'Whether this location can be claimed by owners. Defaults to true.';
COMMENT ON COLUMN public.locations.claimed_status IS 'Claim status synced from token_location_claims.claim_status. Values: unclaimed, claimed_free, expired, removed.';
COMMENT ON COLUMN public.locations.removed_by_owner IS 'Whether this location was removed by the owner. No hard deletes, only state updates.';

