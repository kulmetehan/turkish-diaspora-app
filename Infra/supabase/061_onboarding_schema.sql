-- 061_onboarding_schema.sql
-- Onboarding Flow Schema Extensions
-- Adds fields to user_profiles for onboarding flow and extends badge_type enum

-- 1. Extend user_profiles table with onboarding fields
ALTER TABLE user_profiles
ADD COLUMN IF NOT EXISTS first_run BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS onboarding_version TEXT DEFAULT 'v1.0',
ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS home_city TEXT,
ADD COLUMN IF NOT EXISTS home_region TEXT,
ADD COLUMN IF NOT EXISTS memleket TEXT[],
ADD COLUMN IF NOT EXISTS gender TEXT CHECK (gender IN ('male', 'female', 'prefer_not_to_say'));

-- 2. Extend badge_type enum with nieuwkomer badge
-- Note: ALTER TYPE ... ADD VALUE cannot be used in a transaction block in some PostgreSQL versions
-- This may need to be run separately if it fails
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'nieuwkomer' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'badge_type')
    ) THEN
        ALTER TYPE badge_type ADD VALUE 'nieuwkomer';
    END IF;
END $$;

-- 3. Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_profiles_first_run ON user_profiles(first_run);
CREATE INDEX IF NOT EXISTS idx_user_profiles_onboarding_completed ON user_profiles(onboarding_completed);

-- Comments for documentation
COMMENT ON COLUMN user_profiles.first_run IS 'True if user has not completed onboarding yet';
COMMENT ON COLUMN user_profiles.onboarding_completed IS 'True if user has completed onboarding flow';
COMMENT ON COLUMN user_profiles.onboarding_version IS 'Version of onboarding flow completed (for A/B testing)';
COMMENT ON COLUMN user_profiles.onboarding_completed_at IS 'Timestamp when onboarding was completed';
COMMENT ON COLUMN user_profiles.home_city IS 'User home city (e.g., Rotterdam)';
COMMENT ON COLUMN user_profiles.home_region IS 'User home region (e.g., Zuid-Holland)';
COMMENT ON COLUMN user_profiles.memleket IS 'Array of Turkish provinces (roots)';
COMMENT ON COLUMN user_profiles.gender IS 'User gender preference for addressing';

