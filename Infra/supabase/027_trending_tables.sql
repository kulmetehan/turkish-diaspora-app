-- 027_trending_tables.sql
-- Trending locations calculation and history

-- Main trending locations table (materialized view-like, updated by worker)
CREATE TABLE IF NOT EXISTS public.trending_locations (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    city_key TEXT NOT NULL,
    category_key TEXT,
    window TEXT NOT NULL, -- '5m', '1h', '24h', '7d'
    score NUMERIC(10, 4) NOT NULL,
    rank INTEGER,
    check_ins_count INTEGER DEFAULT 0,
    reactions_count INTEGER DEFAULT 0,
    notes_count INTEGER DEFAULT 0,
    raw_counts JSONB, -- For debugging: {check_ins: 10, reactions: 5, notes: 2}
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(location_id, city_key, category_key, window)
);

CREATE INDEX IF NOT EXISTS idx_trending_locations_city ON public.trending_locations(city_key, window, score DESC);
CREATE INDEX IF NOT EXISTS idx_trending_locations_category ON public.trending_locations(city_key, category_key, window, score DESC);
CREATE INDEX IF NOT EXISTS idx_trending_locations_updated ON public.trending_locations(updated_at);

-- Historical snapshots (daily)
CREATE TABLE IF NOT EXISTS public.trending_locations_history (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    city_key TEXT NOT NULL,
    category_key TEXT,
    window TEXT NOT NULL,
    score NUMERIC(10, 4) NOT NULL,
    rank INTEGER,
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trending_history_date ON public.trending_locations_history(snapshot_date, city_key, category_key, score DESC);

COMMENT ON TABLE public.trending_locations IS 'Current trending scores (updated by trending_worker)';
COMMENT ON TABLE public.trending_locations_history IS 'Daily snapshots of trending scores for historical analysis';



















