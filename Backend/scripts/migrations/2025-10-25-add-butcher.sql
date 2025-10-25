-- Migration: add 'butcher' category to locations.category enum if it does not exist yet.
-- This is safe to run multiple times: it will raise only if 'butcher' already exists.
-- For Supabase / Postgres.

DO $$
BEGIN
    -- Attempt to add the new value to the enum type.
    -- Adjust the enum type name below if your enum name is different.
    ALTER TYPE location_category_enum ADD VALUE IF NOT EXISTS 'butcher';
EXCEPTION
    WHEN duplicate_object THEN
        -- ignore if it already exists
        NULL;
END$$;

-- Optional: backfill existing rows that look like a butcher but were previously bucketed
-- as 'supermarket'. This is heuristic and can be adjusted.
UPDATE locations
SET category = 'butcher'
WHERE category = 'supermarket'
  AND (
        name ILIKE '%kasap%' OR
        name ILIKE '%slager%' OR
        name ILIKE '%slagerij%' OR
        name ILIKE '%butcher%' OR
        name ILIKE '%halal butcher%' OR
        name ILIKE '%butchery%' OR
        name ILIKE '%vleeshandel%'
      );
