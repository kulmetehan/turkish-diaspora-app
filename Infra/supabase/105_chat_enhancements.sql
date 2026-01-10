-- 105_chat_enhancements.sql
-- Chat enhancements: pinned chats and general topics (Turkchat) support

-- Pinned chats support
ALTER TABLE chat_topics ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT FALSE;
ALTER TABLE chat_topics ADD COLUMN IF NOT EXISTS pinned_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_chat_topics_pinned ON chat_topics(is_pinned, pinned_at DESC) WHERE is_pinned = TRUE;

-- General topics (Turkchat) support
-- Gebruik content_type = 'general' voor Turkchat topics
-- Voeg optioneel topic_category toe voor categorisering (Voetbalchat, Vrouwenchat, etc)
ALTER TABLE chat_topics ADD COLUMN IF NOT EXISTS topic_category VARCHAR(50);

-- Image URL for general topics (stored directly, not fetched from content)
-- Note: For content-based topics, image_url is computed dynamically, but general topics can have custom images
ALTER TABLE chat_topics ADD COLUMN IF NOT EXISTS image_url TEXT;

-- Update bestaande indexes voor efficiente queries
CREATE INDEX IF NOT EXISTS idx_chat_topics_content_type ON chat_topics(content_type, updated_at DESC);

-- Comments voor documentatie
COMMENT ON COLUMN chat_topics.is_pinned IS 'Whether this topic is pinned to the top of the chat list';
COMMENT ON COLUMN chat_topics.pinned_at IS 'Timestamp when this topic was pinned';
COMMENT ON COLUMN chat_topics.topic_category IS 'Category for general topics (e.g., Voetbalchat, Vrouwenchat, Algemeen)';

