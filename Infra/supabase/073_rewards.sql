-- 073_rewards.sql
-- Rewards System for Öne Çıkanlar (Featured Users)
-- Rewards are given to users who appear in leaderboards

-- Create ENUM type for reward types
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reward_type') THEN
        CREATE TYPE reward_type AS ENUM (
            'free_item',    -- Free item from sponsor
            'coupon',       -- Discount coupon
            'discount',     -- Percentage discount
            'voucher'       -- Gift voucher
        );
    END IF;
END$$;

-- Create ENUM type for reward status
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reward_status') THEN
        CREATE TYPE reward_status AS ENUM (
            'pending',      -- Reward assigned but not yet claimed
            'claimed',      -- User has claimed the reward
            'expired',      -- Reward expired (past expires_at)
            'cancelled'     -- Reward cancelled (admin action)
        );
    END IF;
END$$;

-- Rewards table: Available rewards pool
CREATE TABLE IF NOT EXISTS public.rewards (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    reward_type reward_type NOT NULL,
    sponsor TEXT NOT NULL, -- Sponsor name (e.g., "Restaurant X")
    city_key TEXT, -- NULL = global, otherwise city-specific
    available_count INTEGER NOT NULL DEFAULT 0, -- Number of rewards available
    expires_at TIMESTAMPTZ, -- When reward availability expires (NULL = no expiration)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- User rewards table: Assigned rewards to users
CREATE TABLE IF NOT EXISTS public.user_rewards (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    reward_id BIGINT NOT NULL REFERENCES public.rewards(id) ON DELETE CASCADE,
    leaderboard_entry_id BIGINT REFERENCES public.leaderboard_entries(id) ON DELETE SET NULL,
    status reward_status NOT NULL DEFAULT 'pending',
    claimed_at TIMESTAMPTZ, -- When user claimed the reward
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Prevent duplicate rewards for same leaderboard entry
    UNIQUE(user_id, leaderboard_entry_id)
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_rewards_city_key_expires 
    ON public.rewards(city_key, expires_at) 
    WHERE expires_at IS NULL OR expires_at > NOW();
CREATE INDEX IF NOT EXISTS idx_rewards_available_count 
    ON public.rewards(available_count) 
    WHERE available_count > 0;

CREATE INDEX IF NOT EXISTS idx_user_rewards_user_id_status 
    ON public.user_rewards(user_id, status);
CREATE INDEX IF NOT EXISTS idx_user_rewards_reward_id 
    ON public.user_rewards(reward_id);
CREATE INDEX IF NOT EXISTS idx_user_rewards_leaderboard_entry_id 
    ON public.user_rewards(leaderboard_entry_id);
CREATE INDEX IF NOT EXISTS idx_user_rewards_status_created 
    ON public.user_rewards(status, created_at);

-- Table and column comments
COMMENT ON TABLE public.rewards IS 'Available rewards pool. Rewards can be city-specific or global.';
COMMENT ON COLUMN public.rewards.title IS 'Title of the reward (e.g., "Free Coffee").';
COMMENT ON COLUMN public.rewards.description IS 'Description of the reward and how to claim it.';
COMMENT ON COLUMN public.rewards.reward_type IS 'Type of reward (free_item, coupon, discount, voucher).';
COMMENT ON COLUMN public.rewards.sponsor IS 'Name of the sponsor providing the reward.';
COMMENT ON COLUMN public.rewards.city_key IS 'City key for city-specific rewards (e.g., rotterdam). NULL means global reward.';
COMMENT ON COLUMN public.rewards.available_count IS 'Number of rewards still available. Decremented when assigned.';
COMMENT ON COLUMN public.rewards.expires_at IS 'When reward availability expires. NULL means no expiration.';

COMMENT ON TABLE public.user_rewards IS 'Rewards assigned to users who appear in Öne Çıkanlar leaderboards.';
COMMENT ON COLUMN public.user_rewards.user_id IS 'User who received the reward.';
COMMENT ON COLUMN public.user_rewards.reward_id IS 'Reference to the reward from rewards table.';
COMMENT ON COLUMN public.user_rewards.leaderboard_entry_id IS 'Leaderboard entry that triggered this reward assignment.';
COMMENT ON COLUMN public.user_rewards.status IS 'Current status of the reward (pending, claimed, expired, cancelled).';
COMMENT ON COLUMN public.user_rewards.claimed_at IS 'Timestamp when user claimed the reward. NULL if not yet claimed.';


