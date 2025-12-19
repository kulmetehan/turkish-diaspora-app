-- 055_activity_likes.sql
-- Activity likes table for feed redesign

-- Activity likes table
CREATE TABLE IF NOT EXISTS activity_likes (
  id BIGSERIAL PRIMARY KEY,
  activity_id BIGINT NOT NULL REFERENCES activity_stream(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  client_id UUID, -- For anonymous users
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT activity_likes_actor_check CHECK (
    (user_id IS NOT NULL AND client_id IS NULL) OR
    (user_id IS NULL AND client_id IS NOT NULL)
  )
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_activity_likes_activity ON activity_likes(activity_id);
CREATE INDEX IF NOT EXISTS idx_activity_likes_user ON activity_likes(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_activity_likes_client ON activity_likes(client_id) WHERE client_id IS NOT NULL;

-- Unique indexes to prevent duplicate likes (partial indexes with WHERE clause)
CREATE UNIQUE INDEX IF NOT EXISTS idx_activity_likes_user_unique ON activity_likes(activity_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_activity_likes_client_unique ON activity_likes(activity_id, client_id) WHERE client_id IS NOT NULL;

COMMENT ON TABLE activity_likes IS 'Likes on activity stream items';
COMMENT ON COLUMN activity_likes.user_id IS 'Authenticated user ID (mutually exclusive with client_id)';
COMMENT ON COLUMN activity_likes.client_id IS 'Anonymous client ID (mutually exclusive with user_id)';





