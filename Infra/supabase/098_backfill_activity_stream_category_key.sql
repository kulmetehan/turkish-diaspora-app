-- 098_backfill_activity_stream_category_key.sql
-- Backfill category_key for existing activity_stream records
-- This ensures that all existing check-ins and other activities show category images

-- Update all activity_stream records that have a location but no category_key
UPDATE activity_stream ast
SET category_key = l.category
FROM locations l
WHERE ast.location_id = l.id
  AND (ast.category_key IS NULL OR ast.category_key = '')
  AND ast.location_id IS NOT NULL
  AND l.category IS NOT NULL
  AND l.category != '';

-- Add comment for documentation
COMMENT ON COLUMN activity_stream.category_key IS 'Category of the location (denormalized from locations.category). Used for displaying category-specific images in the activity feed.';

