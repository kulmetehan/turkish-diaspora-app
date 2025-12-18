-- Migration 060: Event Reactions
-- Create event_reactions table for emoji reactions on events
-- Note: References events_candidate (the underlying table) since events_public is a VIEW

CREATE TABLE IF NOT EXISTS event_reactions (
    id bigserial PRIMARY KEY,
    event_id bigint NOT NULL REFERENCES events_candidate(id) ON DELETE CASCADE,
    reaction_type text NOT NULL CHECK (reaction_type IN ('fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag')),
    client_id text,
    user_id uuid,
    identity_key text GENERATED ALWAYS AS (COALESCE(user_id::text, client_id)) STORED,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(event_id, identity_key, reaction_type)
);

CREATE INDEX IF NOT EXISTS idx_event_reactions_event_id ON event_reactions(event_id);
CREATE INDEX IF NOT EXISTS idx_event_reactions_identity ON event_reactions(identity_key);
CREATE INDEX IF NOT EXISTS idx_event_reactions_type ON event_reactions(reaction_type);

COMMENT ON TABLE event_reactions IS 'Emoji reactions on events';
COMMENT ON COLUMN event_reactions.reaction_type IS 'Type of emoji reaction: fire, heart, thumbs_up, smile, star, flag';
COMMENT ON COLUMN event_reactions.identity_key IS 'Generated column: user_id if available, otherwise client_id';
