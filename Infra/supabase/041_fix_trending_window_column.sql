-- 041_fix_trending_window_column.sql
-- Fix trending_locations table: ensure 'window' column exists and is used consistently
-- This migration handles both cases: table with 'time_window' or missing 'window' column

-- Step 1: If 'time_window' column exists, rename it to 'window'
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'trending_locations' 
        AND column_name = 'time_window'
    ) THEN
        ALTER TABLE public.trending_locations 
        RENAME COLUMN time_window TO "window";
        
        RAISE NOTICE 'Renamed time_window column to window';
    END IF;
END$$;

-- Step 2: If 'window' column doesn't exist, add it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'trending_locations' 
        AND column_name = 'window'
    ) THEN
        ALTER TABLE public.trending_locations 
        ADD COLUMN "window" TEXT NOT NULL DEFAULT '24h';
        
        RAISE NOTICE 'Added window column with default value 24h';
    END IF;
END$$;

-- Step 3: Drop old unique constraint if it exists (with time_window)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM pg_constraint 
        WHERE conname = 'trending_locations_location_id_city_key_category_key_time_window_key'
    ) THEN
        ALTER TABLE public.trending_locations 
        DROP CONSTRAINT trending_locations_location_id_city_key_category_key_time_window_key;
        
        RAISE NOTICE 'Dropped old unique constraint with time_window';
    END IF;
END$$;

-- Step 4: Ensure the correct unique constraint exists (with window)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_constraint 
        WHERE conname = 'trending_locations_location_id_city_key_category_key_window_key'
    ) THEN
        ALTER TABLE public.trending_locations 
        ADD CONSTRAINT trending_locations_location_id_city_key_category_key_window_key 
        UNIQUE (location_id, city_key, category_key, "window");
        
        RAISE NOTICE 'Added unique constraint with window';
    END IF;
END$$;

-- Step 5: Recreate indexes - MUST use EXECUTE in DO block because 'window' is reserved keyword
DROP INDEX IF EXISTS public.idx_trending_locations_city;
DROP INDEX IF EXISTS public.idx_trending_locations_category;

DO $$
BEGIN
    -- Create city index - use EXECUTE to properly quote 'window' column name
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_trending_locations_city ON public.trending_locations(city_key, "window", score DESC)';
    RAISE NOTICE 'Created idx_trending_locations_city index';
    
    -- Create category index - use EXECUTE to properly quote 'window' column name
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_trending_locations_category ON public.trending_locations(city_key, category_key, "window", score DESC)';
    RAISE NOTICE 'Created idx_trending_locations_category index';
END$$;

-- Step 6: Remove default value from window column if it was added (to match original schema)
DO $$
BEGIN
    ALTER TABLE public.trending_locations 
    ALTER COLUMN "window" DROP DEFAULT;
    
    RAISE NOTICE 'Removed default value from window column';
EXCEPTION
    WHEN OTHERS THEN
        -- Ignore if default doesn't exist or column doesn't have default
        NULL;
END$$;

COMMENT ON COLUMN public.trending_locations."window" IS 'Time window: 5m, 1h, 24h, 7d';

