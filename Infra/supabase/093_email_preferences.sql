-- 093_email_preferences.sql
-- Email preferences and unsubscribe functionality

CREATE TABLE IF NOT EXISTS public.email_preferences (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL, -- For outreach emails without user_id
    weekly_digest BOOLEAN NOT NULL DEFAULT true,
    outreach_emails BOOLEAN NOT NULL DEFAULT true,
    transactional_emails BOOLEAN NOT NULL DEFAULT true,
    unsubscribed_at TIMESTAMPTZ, -- NULL = not unsubscribed
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraint: either user_id or email must be provided
    CONSTRAINT check_identity CHECK (
        (user_id IS NOT NULL) OR (email IS NOT NULL AND email != '')
    ),
    
    -- Unique constraint: one preference per user or email
    CONSTRAINT unique_user_email UNIQUE (user_id, email)
);

CREATE INDEX IF NOT EXISTS idx_email_preferences_user_id ON public.email_preferences(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_email_preferences_email ON public.email_preferences(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_email_preferences_unsubscribed ON public.email_preferences(unsubscribed_at) WHERE unsubscribed_at IS NOT NULL;

COMMENT ON TABLE public.email_preferences IS 'Email preferences and unsubscribe status for users and outreach emails';
COMMENT ON COLUMN public.email_preferences.unsubscribed_at IS 'Timestamp when user unsubscribed. NULL = not unsubscribed';

