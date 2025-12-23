-- Migration 074: Remove CHECK constraint on location_reactions.reaction_type to allow custom emoji strings
-- The previous CHECK constraint only allowed: 'fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag'
-- We now want to allow any emoji string for custom reactions (consistent with other reaction tables)

-- Remove CHECK constraint from location_reactions
ALTER TABLE location_reactions 
DROP CONSTRAINT IF EXISTS location_reactions_type_check;

-- Update comment to reflect that reaction_type now accepts any emoji string
COMMENT ON COLUMN location_reactions.reaction_type IS 'Emoji reaction string (e.g., "👍", "❤️", "🔥")';

