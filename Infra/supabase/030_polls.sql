-- 030_polls.sql
-- Polls system

CREATE TYPE poll_type AS ENUM ('single_choice', 'multi_choice');
CREATE TYPE poll_status AS ENUM ('draft', 'active', 'closed');

CREATE TABLE IF NOT EXISTS public.polls (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    question TEXT NOT NULL,
    poll_type poll_type NOT NULL DEFAULT 'single_choice',
    status poll_status NOT NULL DEFAULT 'draft',
    targeting_city_key TEXT, -- NULL = global
    targeting_category_key TEXT, -- NULL = all categories
    is_sponsored BOOLEAN DEFAULT false,
    business_account_id BIGINT, -- For sponsored polls (Fase 3)
    starts_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ends_at TIMESTAMPTZ,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- Admin/editor
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_polls_status ON public.polls(status, starts_at DESC);
CREATE INDEX IF NOT EXISTS idx_polls_city ON public.polls(targeting_city_key, status) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS public.poll_options (
    id BIGSERIAL PRIMARY KEY,
    poll_id BIGINT NOT NULL REFERENCES public.polls(id) ON DELETE CASCADE,
    option_text TEXT NOT NULL,
    display_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(poll_id, display_order)
);

CREATE INDEX IF NOT EXISTS idx_poll_options_poll_id ON public.poll_options(poll_id, display_order);

CREATE TABLE IF NOT EXISTS public.poll_responses (
    id BIGSERIAL PRIMARY KEY,
    poll_id BIGINT NOT NULL REFERENCES public.polls(id) ON DELETE CASCADE,
    option_id BIGINT NOT NULL REFERENCES public.poll_options(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    client_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_in_activity_stream BOOLEAN DEFAULT false,
    -- Explicit identity key (filled by trigger)
    identity_key TEXT,
    CONSTRAINT poll_responses_identity_check CHECK (
        (user_id IS NOT NULL) OR (client_id IS NOT NULL)
    )
);

-- Trigger function for poll responses
CREATE OR REPLACE FUNCTION set_poll_response_identity()
RETURNS TRIGGER AS $$
BEGIN
    NEW.identity_key := COALESCE(NEW.user_id::text, NEW.client_id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_poll_response_identity
    BEFORE INSERT OR UPDATE ON public.poll_responses
    FOR EACH ROW
    EXECUTE FUNCTION set_poll_response_identity();

CREATE INDEX IF NOT EXISTS idx_poll_responses_poll_id ON public.poll_responses(poll_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_poll_responses_option_id ON public.poll_responses(option_id);
CREATE INDEX IF NOT EXISTS idx_poll_responses_user_id ON public.poll_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_poll_responses_client_id ON public.poll_responses(client_id);
CREATE INDEX IF NOT EXISTS idx_poll_responses_processed ON public.poll_responses(processed_in_activity_stream) WHERE processed_in_activity_stream = false;

-- Unique index for single_choice polls (enforced in application layer for poll_type check)
-- Note: This index applies to all polls, but application must check poll_type = 'single_choice' before insert
CREATE UNIQUE INDEX IF NOT EXISTS idx_poll_responses_unique_single 
    ON public.poll_responses(poll_id, identity_key);

-- Aggregated poll stats (updated by worker)
CREATE TABLE IF NOT EXISTS public.poll_stats (
    poll_id BIGINT PRIMARY KEY REFERENCES public.polls(id) ON DELETE CASCADE,
    total_responses INTEGER DEFAULT 0,
    option_counts JSONB NOT NULL DEFAULT '{}'::jsonb, -- {option_id: count, ...}
    city_breakdown JSONB, -- {city_key: count, ...}
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.polls IS 'Poll definitions (admin-created)';
COMMENT ON TABLE public.poll_options IS 'Options for each poll';
COMMENT ON TABLE public.poll_responses IS 'User responses to polls';
COMMENT ON TABLE public.poll_stats IS 'Aggregated poll statistics (updated by worker)';
COMMENT ON INDEX idx_poll_responses_unique_single IS 'Unique constraint: one response per user/client per poll. Application must enforce poll_type = single_choice check.';

















