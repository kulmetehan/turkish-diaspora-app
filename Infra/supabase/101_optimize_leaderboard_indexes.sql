-- 101_optimize_leaderboard_indexes.sql
-- Optimize leaderboard query performance by adding index for rank filtering
-- This index helps with queries that filter by rank first, then period range

-- Index optimized for the query pattern: rank IS NOT NULL AND rank <= 5 AND period range
CREATE INDEX IF NOT EXISTS idx_leaderboard_entries_rank_period 
    ON public.leaderboard_entries(rank, period_start, period_end) 
    WHERE rank IS NOT NULL AND rank <= 5;

-- Composite index for city-specific queries with rank filtering
CREATE INDEX IF NOT EXISTS idx_leaderboard_entries_city_rank_period 
    ON public.leaderboard_entries(city_key, rank, period_start, period_end) 
    WHERE rank IS NOT NULL AND rank <= 5;

-- Index for user_profiles lookup (if not exists)
CREATE INDEX IF NOT EXISTS idx_user_profiles_id 
    ON public.user_profiles(id);

-- Index for user_roles lookup (if not exists)
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id 
    ON public.user_roles(user_id);

COMMENT ON INDEX idx_leaderboard_entries_rank_period IS 'Optimized index for leaderboard queries filtering by rank first, then period range';
COMMENT ON INDEX idx_leaderboard_entries_city_rank_period IS 'Optimized index for city-specific leaderboard queries with rank filtering';



