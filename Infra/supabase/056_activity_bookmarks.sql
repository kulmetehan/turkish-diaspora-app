-- 056_activity_bookmarks.sql
-- Activity bookmarks table for feed redesign

-- Activity bookmarks table (similar structure to likes)
CREATE TABLE IF NOT EXISTS activity_bookmarks (
  id BIGSERIAL PRIMARY KEY,
  activity_id BIGINT NOT NULL REFERENCES activity_stream(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  client_id UUID, -- For anonymous users
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT activity_bookmarks_actor_check CHECK (
    (user_id IS NOT NULL AND client_id IS NULL) OR
    (user_id IS NULL AND client_id IS NOT NULL)
  )
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_activity_bookmarks_activity ON activity_bookmarks(activity_id);
CREATE INDEX IF NOT EXISTS idx_activity_bookmarks_user ON activity_bookmarks(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_activity_bookmarks_client ON activity_bookmarks(client_id) WHERE client_id IS NOT NULL;

-- Unique indexes to prevent duplicate bookmarks (partial indexes with WHERE clause)
CREATE UNIQUE INDEX IF NOT EXISTS idx_activity_bookmarks_user_unique ON activity_bookmarks(activity_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_activity_bookmarks_client_unique ON activity_bookmarks(activity_id, client_id) WHERE client_id IS NOT NULL;

COMMENT ON TABLE activity_bookmarks IS 'Bookmarks on activity stream items';
COMMENT ON COLUMN activity_bookmarks.user_id IS 'Authenticated user ID (mutually exclusive with client_id)';
COMMENT ON COLUMN activity_bookmarks.client_id IS 'Anonymous client ID (mutually exclusive with user_id)';


