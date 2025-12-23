-- 069_auto_create_user_profile.sql
-- Automatic User Profile Creation
-- Note: Cannot create trigger on auth.users (Supabase managed table)
-- Instead, profile creation happens in application code

-- Helper function to create user profile (can be called from application code)
CREATE OR REPLACE FUNCTION public.ensure_user_profile(user_uuid UUID)
RETURNS void AS $$
BEGIN
  INSERT INTO public.user_profiles (id, created_at, updated_at)
  VALUES (user_uuid, NOW(), NOW())
  ON CONFLICT (id) DO NOTHING;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.ensure_user_profile(UUID) IS 'Creates a user_profiles record if it does not exist. Safe to call multiple times.';

