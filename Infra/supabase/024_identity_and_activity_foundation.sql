-- 024_identity_and_activity_foundation.sql
-- Identity & Activity Foundation Tables
-- Extends Supabase auth.users with profiles and privacy settings

-- User profiles (extends auth.users)
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    avatar_url TEXT,
    city_key TEXT, -- e.g., 'rotterdam', 'amsterdam'
    language_pref TEXT DEFAULT 'nl', -- 'nl', 'tr', 'en'
    privacy_hide_from_leaderboards BOOLEAN DEFAULT false,
    privacy_opt_in_analytics BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_city_key ON public.user_profiles(city_key);

-- Privacy settings (separate table for extensibility)
CREATE TABLE IF NOT EXISTS public.privacy_settings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    allow_location_tracking BOOLEAN DEFAULT true,
    allow_push_notifications BOOLEAN DEFAULT false,
    allow_email_digest BOOLEAN DEFAULT false,
    data_retention_consent BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Client ID telemetry (optional, for analytics on anonymous users)
CREATE TABLE IF NOT EXISTS public.client_id_sessions (
    client_id UUID PRIMARY KEY,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- Set when migrated
    migrated_at TIMESTAMPTZ,
    activity_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_client_id_sessions_user_id ON public.client_id_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_client_id_sessions_last_seen ON public.client_id_sessions(last_seen_at);

COMMENT ON TABLE public.user_profiles IS 'Extended user profiles for authenticated users';
COMMENT ON TABLE public.privacy_settings IS 'Privacy preferences per user';
COMMENT ON TABLE public.client_id_sessions IS 'Telemetry for anonymous client_id sessions';









