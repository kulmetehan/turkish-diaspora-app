-- 097_activity_feed_performance_indexes.sql
-- Performance indexes for activity feed queries to fix slow query warnings
-- These indexes optimize the complex JOINs and aggregations in the activity feed endpoint

-- Index for activity_reactions GROUP BY subquery
-- This optimizes: SELECT activity_id, reaction_type, COUNT(*) FROM activity_reactions GROUP BY activity_id, reaction_type
CREATE INDEX IF NOT EXISTS idx_activity_reactions_activity_type 
ON activity_reactions(activity_id, reaction_type);

-- Index for promoted_locations is_promoted check
-- This optimizes the JOIN condition checking: pl.status = 'active' AND pl.promotion_type IN ('feed', 'both') AND pl.starts_at <= now() AND pl.ends_at > now()
CREATE INDEX IF NOT EXISTS idx_promoted_locations_feed_active 
ON promoted_locations(location_id, status, promotion_type, starts_at, ends_at) 
WHERE status = 'active' AND promotion_type IN ('feed', 'both');

-- Additional index for activity_reactions user lookup
-- This optimizes the LEFT JOIN for user_reaction_join
CREATE INDEX IF NOT EXISTS idx_activity_reactions_activity_user 
ON activity_reactions(activity_id, user_id) WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_activity_reactions_activity_client 
ON activity_reactions(activity_id, client_id) WHERE client_id IS NOT NULL;

COMMENT ON INDEX idx_activity_reactions_activity_type IS 'Optimizes GROUP BY queries for reaction counts per activity';
COMMENT ON INDEX idx_promoted_locations_feed_active IS 'Optimizes promoted location checks in activity feed queries';
COMMENT ON INDEX idx_activity_reactions_activity_user IS 'Optimizes user reaction lookups for authenticated users';
COMMENT ON INDEX idx_activity_reactions_activity_client IS 'Optimizes user reaction lookups for anonymous clients';

