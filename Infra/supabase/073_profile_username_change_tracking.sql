-- 073_profile_username_change_tracking.sql
-- Add tracking for username changes (1x per month limit)

ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS last_username_change TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_user_profiles_last_username_change 
ON public.user_profiles(last_username_change);

COMMENT ON COLUMN public.user_profiles.last_username_change IS 
'Timestamp of last username change. Users can change username max 1x per month.';

