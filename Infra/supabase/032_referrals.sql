-- 032_referrals.sql
-- Referral program for user acquisition (EPIC-1.5)

CREATE TABLE IF NOT EXISTS public.referral_codes (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    code TEXT NOT NULL UNIQUE, -- 8-character alphanumeric code
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    uses_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id) -- One referral code per user
);

CREATE INDEX IF NOT EXISTS idx_referral_codes_code ON public.referral_codes(code);
CREATE INDEX IF NOT EXISTS idx_referral_codes_user_id ON public.referral_codes(user_id);

CREATE TABLE IF NOT EXISTS public.referrals (
    id BIGSERIAL PRIMARY KEY,
    referrer_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, -- User who referred
    referred_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, -- User who was referred
    code TEXT NOT NULL, -- Referral code used
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Track if XP bonus has been awarded
    referrer_xp_awarded BOOLEAN NOT NULL DEFAULT false,
    referred_xp_awarded BOOLEAN NOT NULL DEFAULT false,
    UNIQUE(referred_id) -- One referral per referred user
);

CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON public.referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred_id ON public.referrals(referred_id);
CREATE INDEX IF NOT EXISTS idx_referrals_code ON public.referrals(code);

COMMENT ON TABLE public.referral_codes IS 'User referral codes for sharing with others';
COMMENT ON TABLE public.referrals IS 'Tracks referral relationships between users';
COMMENT ON COLUMN public.referral_codes.code IS '8-character alphanumeric unique referral code';
COMMENT ON COLUMN public.referrals.referrer_xp_awarded IS 'Whether referrer has received XP bonus';
COMMENT ON COLUMN public.referrals.referred_xp_awarded IS 'Whether referred user has received welcome bonus';













