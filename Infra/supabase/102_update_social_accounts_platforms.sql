-- 102_update_social_accounts_platforms.sql
-- Update social accounts platform constraint to support new platforms
-- Removes old platforms (twitter, linkedin, website) and adds new ones (snapchat, whatsapp)
-- Keeps tiktok as it was already supported

-- Drop the existing platform check constraint
ALTER TABLE public.user_social_accounts DROP CONSTRAINT IF EXISTS user_social_accounts_platform_check;

-- Add new constraint with updated platforms
ALTER TABLE public.user_social_accounts ADD CONSTRAINT user_social_accounts_platform_check CHECK (
    platform IN ('facebook', 'instagram', 'snapchat', 'youtube', 'whatsapp', 'tiktok')
);

COMMENT ON CONSTRAINT user_social_accounts_platform_check ON public.user_social_accounts IS 
    'Restricts platform values to: facebook, instagram, snapchat, youtube, whatsapp, tiktok';

