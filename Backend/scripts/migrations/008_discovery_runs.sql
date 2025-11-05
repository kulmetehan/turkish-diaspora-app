-- Create discovery_runs table to track discovery run metrics and KPIs
-- This table stores counters for each discovery run (inserted, deduped, updated, etc.)

CREATE TABLE IF NOT EXISTS discovery_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    counters JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes TEXT
);

-- Add index on started_at for efficient KPI queries (last N days)
CREATE INDEX IF NOT EXISTS idx_discovery_runs_started_at ON discovery_runs(started_at);

-- Add comment to explain the table purpose
COMMENT ON TABLE discovery_runs IS 'Tracks discovery run metrics: inserted, deduped, updated counts for KPI monitoring';
COMMENT ON COLUMN discovery_runs.counters IS 'JSONB object with counters: discovered, inserted, deduped_place_id, deduped_fuzzy, updated_existing, failed';

