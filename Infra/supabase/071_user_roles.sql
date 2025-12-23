-- 071_user_roles.sql
-- User Roles System for Gamification
-- Defines role types and user role assignments

-- Create ENUM type for user roles
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM (
            'yeni_gelen',      -- New user
            'mahalleli',       -- Active neighborhood member
            'anlatıcı',        -- Storyteller (many Söz)
            'ses_veren',       -- Voice giver (many poll contributions)
            'sözü_dinlenir',  -- Respected Söz
            'yerinde_tespit', -- Accurate observations
            'sessiz_güç'      -- Silent power (many reads, few posts)
        );
    END IF;
END$$;

-- User roles table
CREATE TABLE IF NOT EXISTS public.user_roles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    primary_role user_role NOT NULL,
    secondary_role user_role,
    earned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ, -- For temporary roles
    city_key TEXT, -- For city-specific roles
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_user_roles_city_key ON public.user_roles(city_key);
CREATE INDEX IF NOT EXISTS idx_user_roles_primary_role ON public.user_roles(primary_role);
CREATE INDEX IF NOT EXISTS idx_user_roles_updated_at ON public.user_roles(updated_at);

-- Table and column comments
COMMENT ON TABLE public.user_roles IS 'User role assignments for gamification system. Each user has a primary role and optionally a secondary role.';
COMMENT ON COLUMN public.user_roles.user_id IS 'Primary key, references auth.users. One role record per user.';
COMMENT ON COLUMN public.user_roles.primary_role IS 'Main role assigned to the user based on their activity patterns.';
COMMENT ON COLUMN public.user_roles.secondary_role IS 'Optional secondary role that complements the primary role.';
COMMENT ON COLUMN public.user_roles.earned_at IS 'Timestamp when the role was first earned.';
COMMENT ON COLUMN public.user_roles.expires_at IS 'Optional expiration timestamp for temporary roles. NULL means permanent.';
COMMENT ON COLUMN public.user_roles.city_key IS 'City key for city-specific roles (e.g., rotterdam, amsterdam). NULL means global role.';
COMMENT ON COLUMN public.user_roles.updated_at IS 'Timestamp when this role record was last updated.';


