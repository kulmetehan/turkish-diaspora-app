-- 107_backfill_poll_activity_stream.sql
-- Backfill activity_stream entries for existing polls without entries
-- Use 'business' actor_type for admin-created polls with system UUID for actor_id

-- System UUID for business/system actors (all zeros)
-- This satisfies the constraint requirement that business actor_type must have actor_id NOT NULL
INSERT INTO activity_stream (
    actor_type,
    actor_id,
    client_id,
    activity_type,
    location_id,
    city_key,
    category_key,
    payload,
    created_at
)
SELECT 
    'business' as actor_type,
    '00000000-0000-0000-0000-000000000000'::uuid as actor_id,
    '00000000-0000-0000-0000-000000000000'::uuid as client_id,
    'poll' as activity_type,
    NULL as location_id,
    p.targeting_city_key as city_key,
    NULL as category_key,
    jsonb_build_object(
        'poll_id', p.id,
        'title', p.title,
        'question', p.question
    ) as payload,
    p.created_at
FROM polls p
WHERE NOT EXISTS (
    SELECT 1 FROM activity_stream ast
    WHERE ast.activity_type = 'poll'
    AND (ast.payload->>'poll_id')::int = p.id
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_activity_stream_poll_id 
ON activity_stream((payload->>'poll_id'))
WHERE activity_type = 'poll';

COMMENT ON INDEX idx_activity_stream_poll_id IS 'Index for faster poll_id lookups in activity_stream payload';
