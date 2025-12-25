-- 076_authenticated_location_claims.sql
-- Authenticated Location Claims System
-- Database schema for authenticated location claims and location owners
-- Part of pre-claim outreach implementation plan (Fase 3)

-- 1. Create ENUM type for authenticated claim status
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'authenticated_claim_status') THEN
        CREATE TYPE authenticated_claim_status AS ENUM (
            'pending',    -- Wachtend op admin approval
            'approved',   -- Toegekend, gebruiker is owner
            'rejected'    -- Afgewezen
        );
    END IF;
END$$;

-- 2. Extend user_role ENUM to include location_owner
-- Note: ALTER TYPE ... ADD VALUE cannot be used in a transaction block in some PostgreSQL versions
-- This may need to be run separately if it fails
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'location_owner' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role')
    ) THEN
        ALTER TYPE user_role ADD VALUE 'location_owner';
    END IF;
END $$;

-- 3. Create authenticated_location_claims table
CREATE TABLE IF NOT EXISTS public.authenticated_location_claims (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status authenticated_claim_status NOT NULL DEFAULT 'pending',
    google_business_link TEXT, -- Optioneel, van gebruiker
    logo_url TEXT, -- Optioneel, van gebruiker, voor preview
    logo_storage_path TEXT, -- Optioneel, definitieve opslag na approval
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- Admin die reviewed
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT, -- Optioneel, reden voor afwijzing
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(location_id) -- One claim per location
);

-- 4. Create location_owners table
CREATE TABLE IF NOT EXISTS public.location_owners (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    google_business_link TEXT, -- Definitief, na approval
    logo_url TEXT, -- Definitief, na approval
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(location_id) -- One owner per location
);

-- 5. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_authenticated_claims_location ON public.authenticated_location_claims(location_id);
CREATE INDEX IF NOT EXISTS idx_authenticated_claims_user ON public.authenticated_location_claims(user_id);
CREATE INDEX IF NOT EXISTS idx_authenticated_claims_status ON public.authenticated_location_claims(status);
CREATE INDEX IF NOT EXISTS idx_location_owners_location ON public.location_owners(location_id);
CREATE INDEX IF NOT EXISTS idx_location_owners_user ON public.location_owners(user_id);

-- 6. Add table and column comments for documentation
COMMENT ON TABLE public.authenticated_location_claims IS 'Location claiming requests by authenticated users (primary flow for outreach emails). Requires login but no business account. Admin approval required.';
COMMENT ON COLUMN public.authenticated_location_claims.location_id IS 'Location being claimed. UNIQUE constraint ensures one claim per location.';
COMMENT ON COLUMN public.authenticated_location_claims.user_id IS 'User making the claim request. Must be authenticated.';
COMMENT ON COLUMN public.authenticated_location_claims.status IS 'Claim status: pending (awaiting admin approval), approved (user is now owner), rejected (claim denied).';
COMMENT ON COLUMN public.authenticated_location_claims.google_business_link IS 'Optional Google Business profile link provided by user during claim submission.';
COMMENT ON COLUMN public.authenticated_location_claims.logo_url IS 'Optional logo URL for preview (temporary, during review process).';
COMMENT ON COLUMN public.authenticated_location_claims.logo_storage_path IS 'Optional logo storage path (definitive storage location after approval).';
COMMENT ON COLUMN public.authenticated_location_claims.reviewed_by IS 'Admin user who reviewed and approved/rejected the claim.';
COMMENT ON COLUMN public.authenticated_location_claims.rejection_reason IS 'Optional reason for claim rejection (shown to user).';

COMMENT ON TABLE public.location_owners IS 'Definitive location ownership data after authenticated claim approval. One entry per location, created when claim is approved.';
COMMENT ON COLUMN public.location_owners.location_id IS 'Location owned by user. UNIQUE constraint ensures one owner per location.';
COMMENT ON COLUMN public.location_owners.user_id IS 'User who owns the location (after claim approval).';
COMMENT ON COLUMN public.location_owners.google_business_link IS 'Definitive Google Business profile link (copied from authenticated_location_claims after approval).';
COMMENT ON COLUMN public.location_owners.logo_url IS 'Definitive logo URL (moved from temp storage after approval).';
COMMENT ON COLUMN public.location_owners.claimed_at IS 'Timestamp when claim was approved and ownership was granted.';

