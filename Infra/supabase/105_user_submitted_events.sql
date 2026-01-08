-- 105_user_submitted_events.sql
-- User-submitted event requests table

CREATE TABLE IF NOT EXISTS public.user_submitted_events (
    id BIGSERIAL PRIMARY KEY,
    -- Event data (voor review)
    title TEXT NOT NULL,
    description TEXT,
    start_time_utc TIMESTAMPTZ NOT NULL,
    end_time_utc TIMESTAMPTZ,
    location_text TEXT,
    lat NUMERIC(10, 8),
    lng NUMERIC(11, 8),
    url TEXT,
    category_key TEXT,
    -- User info
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    reviewed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,  -- Admin
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT,
    -- Created event reference (na approval)
    created_event_id BIGINT REFERENCES public.events_candidate(id) ON DELETE SET NULL,
    -- Timestamps
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_submitted_events_user ON public.user_submitted_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_submitted_events_status ON public.user_submitted_events(status);
CREATE INDEX IF NOT EXISTS idx_user_submitted_events_start_time ON public.user_submitted_events(start_time_utc);
CREATE INDEX IF NOT EXISTS idx_user_submitted_events_event ON public.user_submitted_events(created_event_id) WHERE created_event_id IS NOT NULL;

-- Comments
COMMENT ON TABLE public.user_submitted_events IS 'User-submitted event requests. After admin approval, events are created via event_raw → events_candidate pipeline.';
COMMENT ON COLUMN public.user_submitted_events.created_event_id IS 'Reference to created events_candidate after approval.';
COMMENT ON COLUMN public.user_submitted_events.status IS 'Submission status: pending (awaiting review), approved (event created), rejected (denied).';

