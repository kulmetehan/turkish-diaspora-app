-- 028_gamification.sql
-- XP, streaks, and badges

-- User XP and streaks
CREATE TABLE IF NOT EXISTS public.user_streaks (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    current_streak_days INTEGER DEFAULT 0,
    longest_streak_days INTEGER DEFAULT 0,
    last_active_at TIMESTAMPTZ,
    total_xp INTEGER DEFAULT 0,
    daily_xp INTEGER DEFAULT 0, -- Resets daily
    daily_xp_cap INTEGER DEFAULT 200,
    last_xp_reset_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_streaks_last_active ON public.user_streaks(last_active_at);

-- XP log (optional, for audit/debugging)
CREATE TABLE IF NOT EXISTS public.user_xp_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    client_id UUID, -- For anonymous users before migration
    xp_amount INTEGER NOT NULL,
    source TEXT NOT NULL, -- 'check_in', 'reaction', 'note', 'poll_response', 'favorite'
    source_id BIGINT, -- Reference to check_ins.id, location_notes.id, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_xp_log_user_id ON public.user_xp_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_xp_log_client_id ON public.user_xp_log(client_id, created_at DESC);

-- Badges
CREATE TYPE badge_type AS ENUM (
    'explorer_city', -- 10 unique locations in city
    'early_adopter', -- First 1000 users in city
    'poll_master', -- 100 polls answered
    'super_supporter', -- 50 notes written
    'local_guide', -- 10 notes with positive feedback
    'streak_7', -- 7 day streak
    'streak_30', -- 30 day streak
    'check_in_100' -- 100 check-ins total
);

CREATE TABLE IF NOT EXISTS public.user_badges (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    badge_type badge_type NOT NULL,
    city_key TEXT, -- For city-specific badges
    earned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, badge_type, city_key)
);

CREATE INDEX IF NOT EXISTS idx_user_badges_user_id ON public.user_badges(user_id, earned_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_badges_type ON public.user_badges(badge_type);

COMMENT ON TABLE public.user_streaks IS 'XP and streak tracking per user';
COMMENT ON TABLE public.user_xp_log IS 'Audit log of all XP awards (optional, can be pruned)';
COMMENT ON TABLE public.user_badges IS 'Badges earned by users';




















