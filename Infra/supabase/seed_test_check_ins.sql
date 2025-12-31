-- Seed Test Check-ins for Active Users Map Display
-- This creates check-ins from the last 4 hours for authenticated users
-- Run this in Supabase SQL Editor to test the check-ins avatar feature

-- Step 1: Get some users (if you have any authenticated users)
-- If you don't have users, you'll need to create them via Supabase Auth first
-- Then their profiles will be in user_profiles table

-- Step 2: Get some verified locations with coordinates
-- We'll use Rotterdam area locations as an example

-- Step 3: Create check-ins for the last 4 hours
-- Multiple users at the same location to test stacking

WITH 
-- Get users (limit to first 10 if you have many)
users AS (
    SELECT id, display_name, avatar_url
    FROM user_profiles
    WHERE id IS NOT NULL
    LIMIT 10
),
-- Get locations in Rotterdam area (or any area you want to test)
locations AS (
    SELECT id, name, lat, lng
    FROM locations
    WHERE state = 'VERIFIED'
      AND lat IS NOT NULL 
      AND lng IS NOT NULL
      -- Rotterdam area example (adjust bbox as needed)
      AND lng BETWEEN 4.2 AND 4.8
      AND lat BETWEEN 51.8 AND 52.0
    LIMIT 20
),
-- Generate check-ins
check_ins_to_create AS (
    SELECT 
        u.id as user_id,
        l.id as location_id,
        -- Random time within last 4 hours
        NOW() - (random() * INTERVAL '4 hours') as created_at
    FROM users u
    CROSS JOIN locations l
    -- Create multiple check-ins per location (for stacking test)
    -- Each user checks in at 2-3 random locations
    WHERE random() < 0.3  -- 30% chance per user-location combination
    ORDER BY random()
    LIMIT 50  -- Create up to 50 check-ins
)
-- Insert check-ins
INSERT INTO check_ins (user_id, location_id, created_at)
SELECT 
    user_id,
    location_id,
    created_at
FROM check_ins_to_create
ON CONFLICT (location_id, COALESCE(user_id::text, client_id::text), DATE(created_at)) 
DO NOTHING;

-- Verify the check-ins were created
SELECT 
    ci.location_id,
    l.name as location_name,
    COUNT(DISTINCT ci.user_id) as user_count,
    COUNT(*) as check_in_count,
    MAX(ci.created_at) as latest_check_in,
    NOW() - MAX(ci.created_at) as age
FROM check_ins ci
INNER JOIN locations l ON ci.location_id = l.id
WHERE ci.user_id IS NOT NULL
  AND ci.created_at >= NOW() - INTERVAL '4 hours'
GROUP BY ci.location_id, l.name
ORDER BY user_count DESC, latest_check_in DESC
LIMIT 20;

