-- 072_leaderboards.sql
-- Leaderboards System for Öne Çıkanlar (Featured Users)
-- Temporary, thematic leaderboards that rotate

-- Create ENUM type for leaderboard categories
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leaderboard_category') THEN
        CREATE TYPE leaderboard_category AS ENUM (
            'soz_hafta',       -- Best Söz this week
            'mahalle_gururu',  -- Local active (neighborhood pride)
            'sessiz_guç',      -- Silent power (many reads, few posts)
            'diaspora_nabzı'   -- Poll contribution (diaspora pulse)
        );
    END IF;
END$$;

-- Leaderboard entries table
CREATE TABLE IF NOT EXISTS public.leaderboard_entries (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    category leaderboard_category NOT NULL,
    city_key TEXT, -- NULL = global
    period_start TIMESTAMPTZ NOT NULL, -- Start of period (day/week/month)
    period_end TIMESTAMPTZ NOT NULL,   -- End of period
    score INTEGER NOT NULL, -- Internal score for ranking (not visible to users)
    rank INTEGER, -- 1-5, for selection (top 5 per category)
    context_data JSONB, -- Extra data: location_id, poll_id, note_id, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_leaderboard_entries_category_city_period 
    ON public.leaderboard_entries(category, city_key, period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_leaderboard_entries_user_id 
    ON public.leaderboard_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_leaderboard_entries_period 
    ON public.leaderboard_entries(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_leaderboard_entries_score 
    ON public.leaderboard_entries(category, city_key, period_start, period_end, score DESC);

-- Table and column comments
COMMENT ON TABLE public.leaderboard_entries IS 'Temporary leaderboard entries for Öne Çıkanlar feature. Entries are created for specific time periods and categories.';
COMMENT ON COLUMN public.leaderboard_entries.user_id IS 'User who appears in this leaderboard entry.';
COMMENT ON COLUMN public.leaderboard_entries.category IS 'Category of leaderboard (soz_hafta, mahalle_gururu, etc.).';
COMMENT ON COLUMN public.leaderboard_entries.city_key IS 'City key for city-specific leaderboards. NULL means global leaderboard.';
COMMENT ON COLUMN public.leaderboard_entries.period_start IS 'Start timestamp of the period this entry represents (e.g., start of week).';
COMMENT ON COLUMN public.leaderboard_entries.period_end IS 'End timestamp of the period this entry represents (e.g., end of week).';
COMMENT ON COLUMN public.leaderboard_entries.score IS 'Internal score used for ranking. Not exposed to users.';
COMMENT ON COLUMN public.leaderboard_entries.rank IS 'Rank position (1-5) for this entry in its category/period. NULL if not yet ranked.';
COMMENT ON COLUMN public.leaderboard_entries.context_data IS 'Additional context data in JSONB format (e.g., location_id, poll_id, note_id for reference).';


