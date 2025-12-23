-- 070_user_activity_summary.sql
-- User Activity Summary Table
-- Pre-aggregated activity metrics per user for gamification queries
-- This table serves as a cache to avoid expensive real-time calculations

CREATE TABLE IF NOT EXISTS public.user_activity_summary (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    last_4_weeks_active_days INTEGER DEFAULT 0,
    last_activity_date TIMESTAMPTZ,
    total_söz_count INTEGER DEFAULT 0,
    total_check_in_count INTEGER DEFAULT 0,
    total_poll_response_count INTEGER DEFAULT 0,
    city_key TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_user_activity_summary_city_key ON public.user_activity_summary(city_key);
CREATE INDEX IF NOT EXISTS idx_user_activity_summary_updated_at ON public.user_activity_summary(updated_at);

-- Table and column comments
COMMENT ON TABLE public.user_activity_summary IS 'Pre-aggregated user activity metrics for gamification queries. Data is calculated from check_ins, location_notes, and poll_responses tables.';
COMMENT ON COLUMN public.user_activity_summary.user_id IS 'Primary key, references auth.users. One summary record per user.';
COMMENT ON COLUMN public.user_activity_summary.last_4_weeks_active_days IS 'Number of unique days with activity in the last 4 weeks (calculated from check_ins, location_notes, poll_responses).';
COMMENT ON COLUMN public.user_activity_summary.last_activity_date IS 'Most recent activity timestamp from any activity type.';
COMMENT ON COLUMN public.user_activity_summary.total_söz_count IS 'Total count of location_notes (user-generated notes/söz) for this user.';
COMMENT ON COLUMN public.user_activity_summary.total_check_in_count IS 'Total count of check_ins for this user.';
COMMENT ON COLUMN public.user_activity_summary.total_poll_response_count IS 'Total count of poll_responses for this user.';
COMMENT ON COLUMN public.user_activity_summary.city_key IS 'Denormalized city_key from user_profiles for query performance (e.g., rotterdam, amsterdam).';
COMMENT ON COLUMN public.user_activity_summary.updated_at IS 'Timestamp when this summary was last updated.';



