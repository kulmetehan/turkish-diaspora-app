-- Discovery grid performance indexes
-- Optimizes queries for the discovery grid endpoint (GET /api/v1/admin/discovery/grid)
-- 
-- These indexes support:
-- 1. Filtering locations by state and first_seen_at (for 30-day window queries)
-- 2. Bounding box queries on lat/lng coordinates (for city/district bbox filtering)
--
-- Created: 2025-01-XX
-- Purpose: Improve performance of batched discovery grid queries

-- Composite index for state + first_seen_at filtering
-- This optimizes the WHERE clause: state = 'CANDIDATE' AND first_seen_at >= $1
-- Partial index reduces size by only indexing CANDIDATE locations
CREATE INDEX IF NOT EXISTS idx_locations_state_first_seen
    ON public.locations(state, first_seen_at)
    WHERE state = 'CANDIDATE';

-- Btree index on coordinates for bounding box queries
-- This optimizes the WHERE clause: lat BETWEEN $2 AND $3 AND lng BETWEEN $4 AND $5
-- Partial index excludes NULL coordinates to reduce index size
CREATE INDEX IF NOT EXISTS idx_locations_lat_lng
    ON public.locations(lat, lng)
    WHERE lat IS NOT NULL AND lng IS NOT NULL;

-- Comments for documentation
COMMENT ON INDEX idx_locations_state_first_seen IS 'Composite index for discovery grid queries filtering by state and first_seen_at (30-day window)';
COMMENT ON INDEX idx_locations_lat_lng IS 'Btree index on coordinates for bounding box queries in discovery grid endpoint';

