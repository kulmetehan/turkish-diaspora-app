-- 106_add_chat_topics_url.sql
-- Add url field to chat_topics for music and news items

ALTER TABLE chat_topics 
  ADD COLUMN IF NOT EXISTS url TEXT;

CREATE INDEX IF NOT EXISTS idx_chat_topics_url ON chat_topics(url) WHERE url IS NOT NULL;

COMMENT ON COLUMN chat_topics.url IS 'Direct URL storage for music/news items (alternative to description parsing)';
