-- 077_token_location_claims.sql
-- Token-based Location Claims System
-- Database schema for token-based location claims (fallback for non-authenticated users)
-- Part of pre-claim outreach implementation plan (Fase 4)

-- 1. Create ENUM type for token claim status
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'token_claim_status') THEN
        CREATE TYPE token_claim_status AS ENUM (
            'unclaimed',     -- Nog niet geclaimed
            'claimed_free',   -- Geclaimed, gratis periode actief
            'expired',        -- Gratis periode verlopen
            'removed'         -- Verwijderd door eigenaar
        );
    END IF;
END$$;

-- 2. Create token_location_claims table
CREATE TABLE IF NOT EXISTS public.token_location_claims (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    claim_token TEXT NOT NULL UNIQUE, -- Unique token for token-based access
    claim_status token_claim_status NOT NULL DEFAULT 'unclaimed',
    claimed_by_email TEXT, -- Email of user who claimed (no login required)
    claimed_at TIMESTAMPTZ, -- Timestamp when location was claimed
    free_until TIMESTAMPTZ, -- End of free period (einde gratis periode)
    removed_at TIMESTAMPTZ, -- Timestamp when location was removed by owner
    removal_reason TEXT, -- Optional reason for removal
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(location_id) -- One claim per location
);

-- 3. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_token_claims_location ON public.token_location_claims(location_id);
CREATE INDEX IF NOT EXISTS idx_token_claims_token ON public.token_location_claims(claim_token);
CREATE INDEX IF NOT EXISTS idx_token_claims_status ON public.token_location_claims(claim_status);
CREATE INDEX IF NOT EXISTS idx_token_claims_email ON public.token_location_claims(claimed_by_email) WHERE claimed_by_email IS NOT NULL;

-- 4. Add table and column comments for documentation
COMMENT ON TABLE public.token_location_claims IS 'Token-based location claims for non-authenticated users (fallback for outreach emails). Uses unique tokens per location for claim actions without login requirement.';
COMMENT ON COLUMN public.token_location_claims.location_id IS 'Location being claimed. UNIQUE constraint ensures one claim per location.';
COMMENT ON COLUMN public.token_location_claims.claim_token IS 'Unique cryptographically secure token for token-based access. Used in URLs like /claim/{token}.';
COMMENT ON COLUMN public.token_location_claims.claim_status IS 'Claim status: unclaimed (not yet claimed), claimed_free (claimed, free period active), expired (free period expired), removed (removed by owner).';
COMMENT ON COLUMN public.token_location_claims.claimed_by_email IS 'Email address of user who claimed the location (no login required for token-based claims).';
COMMENT ON COLUMN public.token_location_claims.claimed_at IS 'Timestamp when location was claimed via token.';
COMMENT ON COLUMN public.token_location_claims.free_until IS 'End timestamp of free period. After this date, claim_status should be updated to expired.';
COMMENT ON COLUMN public.token_location_claims.removed_at IS 'Timestamp when location was removed by owner (via token-based remove action).';
COMMENT ON COLUMN public.token_location_claims.removal_reason IS 'Optional reason for removal (provided by owner).';

