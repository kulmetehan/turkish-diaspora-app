-- Migration 063: Remove CHECK constraints on reaction_type to allow custom emoji strings
-- The previous CHECK constraints only allowed: 'fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag'
-- We now want to allow any emoji string for custom reactions

-- Remove CHECK constraint from activity_reactions
ALTER TABLE activity_reactions 
DROP CONSTRAINT IF EXISTS activity_reactions_reaction_type_check;

-- Remove CHECK constraint from news_reactions
ALTER TABLE news_reactions 
DROP CONSTRAINT IF EXISTS news_reactions_reaction_type_check;

-- Remove CHECK constraint from event_reactions
ALTER TABLE event_reactions 
DROP CONSTRAINT IF EXISTS event_reactions_reaction_type_check;

-- Update comments to reflect that reaction_type now accepts any emoji string
COMMENT ON COLUMN activity_reactions.reaction_type IS 'Emoji reaction string (e.g., "👍", "❤️", "🔥")';
COMMENT ON COLUMN news_reactions.reaction_type IS 'Emoji reaction string (e.g., "👍", "❤️", "🔥")';
COMMENT ON COLUMN event_reactions.reaction_type IS 'Emoji reaction string (e.g., "👍", "❤️", "🔥")';
