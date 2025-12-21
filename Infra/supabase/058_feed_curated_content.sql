-- Migration 058: Feed Curated Content
-- Create feed_curated_content table for storing AI-curated rankings for feed page dashboard cards

CREATE TABLE IF NOT EXISTS public.feed_curated_content (
    id BIGSERIAL PRIMARY KEY,
    content_type TEXT NOT NULL CHECK (content_type IN ('news', 'events', 'location_stats')),
    ranked_items JSONB NOT NULL, -- Array of ranked items with relevance_score
    metadata JSONB, -- AI metadata, timestamp, total_ranked, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL -- When ranking becomes stale
);

CREATE INDEX IF NOT EXISTS idx_feed_curated_content_type ON feed_curated_content(content_type);
CREATE INDEX IF NOT EXISTS idx_feed_curated_content_expires ON feed_curated_content(expires_at);
CREATE INDEX IF NOT EXISTS idx_feed_curated_content_created ON feed_curated_content(created_at DESC);

COMMENT ON TABLE feed_curated_content IS 'Stores AI-curated content rankings for feed page dashboard cards';
COMMENT ON COLUMN feed_curated_content.content_type IS 'Type of curated content: news, events, location_stats';
COMMENT ON COLUMN feed_curated_content.ranked_items IS 'JSONB array of ranked items with relevance_score and original item data';
COMMENT ON COLUMN feed_curated_content.metadata IS 'Additional metadata: total_ranked, cached_at, AI model used, etc.';
COMMENT ON COLUMN feed_curated_content.expires_at IS 'Timestamp when this ranking becomes stale (news: 6h, events/locations: 24h)';






