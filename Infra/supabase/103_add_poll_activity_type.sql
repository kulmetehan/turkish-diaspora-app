-- 103_add_poll_activity_type.sql
-- Add 'poll' to activity_type constraint for user-created polls

-- Drop existing constraint
ALTER TABLE activity_stream 
  DROP CONSTRAINT IF EXISTS activity_stream_type_check;

-- Add updated constraint with 'poll' type
ALTER TABLE activity_stream
  ADD CONSTRAINT activity_stream_type_check CHECK (
    activity_type IN ('check_in', 'reaction', 'note', 'poll_response', 'favorite', 'bulletin_post', 'event', 'poll')
  );

COMMENT ON CONSTRAINT activity_stream_type_check ON activity_stream IS 'Activity types including poll for user-created polls';









