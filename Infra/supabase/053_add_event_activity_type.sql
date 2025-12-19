-- 053_add_event_activity_type.sql
-- Add 'event' to activity_type constraint

-- Drop existing constraint
ALTER TABLE activity_stream 
  DROP CONSTRAINT IF EXISTS activity_stream_type_check;

-- Add updated constraint with 'event' type
ALTER TABLE activity_stream
  ADD CONSTRAINT activity_stream_type_check CHECK (
    activity_type IN ('check_in', 'reaction', 'note', 'poll_response', 'favorite', 'bulletin_post', 'event')
  );

COMMENT ON CONSTRAINT activity_stream_type_check ON activity_stream IS 'Activity types including event support for feed redesign';





