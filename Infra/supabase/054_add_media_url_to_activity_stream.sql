-- 054_add_media_url_to_activity_stream.sql
-- Add optional media_url column to activity_stream for feed redesign

-- Add optional media_url column
ALTER TABLE activity_stream
  ADD COLUMN IF NOT EXISTS media_url TEXT;

-- Create index for non-null media URLs (for filtering/media queries)
CREATE INDEX IF NOT EXISTS idx_activity_stream_media_url 
  ON activity_stream(media_url) WHERE media_url IS NOT NULL;

COMMENT ON COLUMN activity_stream.media_url IS 'Optional URL to media attachment (image, etc.) for feed cards';




