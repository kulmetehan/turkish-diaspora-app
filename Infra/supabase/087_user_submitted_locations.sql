-- 087_user_submitted_locations.sql
-- User-submitted location requests table

CREATE TABLE IF NOT EXISTS public.user_submitted_locations (
    id BIGSERIAL PRIMARY KEY,
    -- Location data (voor review)
    name TEXT NOT NULL,
    address TEXT,
    lat NUMERIC(10, 7) NOT NULL,
    lng NUMERIC(10, 7) NOT NULL,
    category TEXT NOT NULL,  -- Kan custom categorie zijn
    -- User info
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    is_owner BOOLEAN NOT NULL DEFAULT false,  -- Is gebruiker de eigenaar?
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    reviewed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,  -- Admin
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT,
    -- Created location reference (na approval)
    created_location_id BIGINT REFERENCES public.locations(id) ON DELETE SET NULL,
    -- Timestamps
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_submitted_locations_user ON public.user_submitted_locations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_submitted_locations_status ON public.user_submitted_locations(status);
CREATE INDEX IF NOT EXISTS idx_user_submitted_locations_location ON public.user_submitted_locations(created_location_id) WHERE created_location_id IS NOT NULL;

-- Comments
COMMENT ON TABLE public.user_submitted_locations IS 'User-submitted location requests. After admin approval, locations are created with state CANDIDATE_MANUAL.';
COMMENT ON COLUMN public.user_submitted_locations.is_owner IS 'If true, user becomes location owner after approval.';
COMMENT ON COLUMN public.user_submitted_locations.created_location_id IS 'Reference to created location after approval.';
COMMENT ON COLUMN public.user_submitted_locations.status IS 'Submission status: pending (awaiting review), approved (location created), rejected (denied).';







