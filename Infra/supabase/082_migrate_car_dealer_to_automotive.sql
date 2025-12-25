-- 082_migrate_car_dealer_to_automotive.sql
-- Migrate category from 'car_dealer' to 'automotive'
--
-- This migration updates all references to the 'car_dealer' category
-- to use the new 'automotive' category key throughout the database.
--
-- Affected tables:
-- - locations.category
-- - categories_config.category_key (if exists)

BEGIN;

-- Update locations table
UPDATE locations
SET category = 'automotive'
WHERE category = 'car_dealer';

-- Update categories_config table if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'categories_config'
    ) THEN
        UPDATE categories_config
        SET 
            category_key = 'automotive',
            label = 'automotive',
            updated_at = NOW()
        WHERE category_key = 'car_dealer';
    END IF;
END $$;

-- Log the migration
DO $$
DECLARE
    locations_updated INTEGER;
    config_updated INTEGER;
BEGIN
    SELECT COUNT(*) INTO locations_updated
    FROM locations
    WHERE category = 'automotive' AND category = 'automotive';
    
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'categories_config'
    ) THEN
        SELECT COUNT(*) INTO config_updated
        FROM categories_config
        WHERE category_key = 'automotive';
    ELSE
        config_updated := 0;
    END IF;
    
    RAISE NOTICE 'Migration completed: % locations updated, % config records updated', 
        locations_updated, config_updated;
END $$;

COMMIT;

