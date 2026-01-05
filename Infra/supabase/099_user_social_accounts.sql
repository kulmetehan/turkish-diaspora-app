-- 099_user_social_accounts.sql
-- User Social Accounts Table
-- Allows users to link their social media profiles

CREATE TABLE IF NOT EXISTS public.user_social_accounts (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    username TEXT NOT NULL,
    url TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, platform),
    CONSTRAINT user_social_accounts_platform_check CHECK (
        platform IN ('instagram', 'twitter', 'linkedin', 'tiktok', 'facebook', 'youtube', 'website')
    )
);

CREATE INDEX IF NOT EXISTS idx_user_social_accounts_user_id ON public.user_social_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_social_accounts_platform ON public.user_social_accounts(platform);

COMMENT ON TABLE public.user_social_accounts IS 'User social media account links for profile display';



