-- Migration 057: Activity Reactions
-- Create activity_reactions table for emoji reactions on activity items

CREATE TABLE IF NOT EXISTS activity_reactions (
    id bigserial PRIMARY KEY,
    activity_id bigint NOT NULL REFERENCES activity_stream(id) ON DELETE CASCADE,
    reaction_type text NOT NULL CHECK (reaction_type IN ('fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag')),
    client_id text,
    user_id uuid,
    identity_key text GENERATED ALWAYS AS (COALESCE(user_id::text, client_id)) STORED,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(activity_id, identity_key, reaction_type)
);

CREATE INDEX IF NOT EXISTS idx_activity_reactions_activity_id ON activity_reactions(activity_id);
CREATE INDEX IF NOT EXISTS idx_activity_reactions_identity ON activity_reactions(identity_key);
CREATE INDEX IF NOT EXISTS idx_activity_reactions_type ON activity_reactions(reaction_type);

COMMENT ON TABLE activity_reactions IS 'Emoji reactions on activity stream items';
COMMENT ON COLUMN activity_reactions.reaction_type IS 'Type of emoji reaction: fire, heart, thumbs_up, smile, star, flag';
COMMENT ON COLUMN activity_reactions.identity_key IS 'Generated column: user_id if available, otherwise client_id';








