-- 100_add_last_seen_to_profiles.sql
-- Add last_seen_at column to user_profiles
-- Note: This column is calculated from activity_stream, not automatically updated

ALTER TABLE public.user_profiles 
ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_user_profiles_last_seen ON public.user_profiles(last_seen_at);

COMMENT ON COLUMN public.user_profiles.last_seen_at IS 'Last seen timestamp calculated from activity_stream (privacy-friendly, not auto-updated)';








