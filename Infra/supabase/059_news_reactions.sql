-- Migration 059: News Reactions
-- Create news_reactions table for emoji reactions on news items

CREATE TABLE IF NOT EXISTS news_reactions (
    id bigserial PRIMARY KEY,
    news_id bigint NOT NULL REFERENCES raw_ingested_news(id) ON DELETE CASCADE,
    reaction_type text NOT NULL CHECK (reaction_type IN ('fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag')),
    client_id text,
    user_id uuid,
    identity_key text GENERATED ALWAYS AS (COALESCE(user_id::text, client_id)) STORED,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(news_id, identity_key, reaction_type)
);

CREATE INDEX IF NOT EXISTS idx_news_reactions_news_id ON news_reactions(news_id);
CREATE INDEX IF NOT EXISTS idx_news_reactions_identity ON news_reactions(identity_key);
CREATE INDEX IF NOT EXISTS idx_news_reactions_type ON news_reactions(reaction_type);

COMMENT ON TABLE news_reactions IS 'Emoji reactions on news items';
COMMENT ON COLUMN news_reactions.reaction_type IS 'Type of emoji reaction: fire, heart, thumbs_up, smile, star, flag';
COMMENT ON COLUMN news_reactions.identity_key IS 'Generated column: user_id if available, otherwise client_id';






