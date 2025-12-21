-- 062_onboarding_responses.sql
-- Onboarding Responses Table for Anonymous Users
-- Stores onboarding data for users identified by client_id (anonymous users)
-- Authenticated users store this data in user_profiles table

-- Create onboarding_responses table for anonymous users
CREATE TABLE IF NOT EXISTS onboarding_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    home_city TEXT,
    home_region TEXT,
    home_city_key TEXT,  -- CityKey for news preferences (e.g., "rotterdam")
    memleket TEXT[],
    gender TEXT CHECK (gender IN ('male', 'female', 'prefer_not_to_say')),
    onboarding_version TEXT DEFAULT 'v1.0',
    completed_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(client_id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_onboarding_responses_client_id ON onboarding_responses(client_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_responses_completed_at ON onboarding_responses(completed_at);
CREATE INDEX IF NOT EXISTS idx_onboarding_responses_created_at ON onboarding_responses(created_at);

-- Comments for documentation
COMMENT ON TABLE onboarding_responses IS 'Stores onboarding responses for anonymous users identified by client_id';
COMMENT ON COLUMN onboarding_responses.client_id IS 'Client ID (UUID) from X-Client-Id header for anonymous users';
COMMENT ON COLUMN onboarding_responses.home_city IS 'User home city name (e.g., Rotterdam)';
COMMENT ON COLUMN onboarding_responses.home_region IS 'User home region (e.g., Zuid-Holland)';
COMMENT ON COLUMN onboarding_responses.home_city_key IS 'CityKey for news preferences (normalized, lowercase, e.g., rotterdam)';
COMMENT ON COLUMN onboarding_responses.memleket IS 'Array of Turkish city keys (normalized, lowercase)';
COMMENT ON COLUMN onboarding_responses.gender IS 'User gender preference for addressing';
COMMENT ON COLUMN onboarding_responses.onboarding_version IS 'Version of onboarding flow completed (for A/B testing)';
COMMENT ON COLUMN onboarding_responses.completed_at IS 'Timestamp when onboarding was completed';



