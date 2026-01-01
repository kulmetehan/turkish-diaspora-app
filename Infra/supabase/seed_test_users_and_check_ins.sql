-- Complete seed script: Create test users AND check-ins
-- Run this in Supabase SQL Editor

-- IMPORTANT: This script assumes you have Supabase Auth configured
-- Users must be created via Supabase Auth first, then their profiles exist in user_profiles
-- 
-- If you need to create test users:
-- 1. Use Supabase Dashboard → Authentication → Add User (manually)
-- 2. Or use the signup flow in your app
-- 3. Then run the check-ins part below

-- ============================================
-- PART 1: Check if you have users
-- ============================================
SELECT 
    COUNT(*) as total_users,
    COUNT(CASE WHEN display_name IS NOT NULL THEN 1 END) as users_with_names,
    COUNT(CASE WHEN avatar_url IS NOT NULL THEN 1 END) as users_with_avatars
FROM user_profiles
WHERE id IS NOT NULL;

-- ============================================
-- PART 2: Create check-ins for existing users
-- ============================================

WITH 
-- Get users (first 10 users)
users AS (
    SELECT id, display_name, avatar_url
    FROM user_profiles
    WHERE id IS NOT NULL
    LIMIT 10
),
-- Get locations in Rotterdam area (adjust bbox as needed)
locations AS (
    SELECT id, name, lat, lng
    FROM locations
    WHERE state = 'VERIFIED'
      AND lat IS NOT NULL 
      AND lng IS NOT NULL
      -- Rotterdam area: adjust these coordinates to your test area
      AND lng BETWEEN 4.2 AND 4.8
      AND lat BETWEEN 51.8 AND 52.0
    LIMIT 20
),
-- Generate check-ins (multiple users at same locations for stacking)
check_ins_to_create AS (
    SELECT 
        u.id as user_id,
        l.id as location_id,
        -- Random time within last 4 hours
        NOW() - (random() * INTERVAL '4 hours') as created_at
    FROM users u
    CROSS JOIN locations l
    -- 30% chance per user-location = ~2-3 locations per user
    WHERE random() < 0.3
    ORDER BY random()
    LIMIT 50
)
-- Insert check-ins (skip if already exists for same user-location-date)
INSERT INTO check_ins (user_id, location_id, created_at)
SELECT 
    user_id,
    location_id,
    created_at
FROM check_ins_to_create
ON CONFLICT (location_id, COALESCE(user_id::text, client_id::text), DATE(created_at)) 
DO NOTHING;

-- ============================================
-- PART 3: Verify results
-- ============================================
SELECT 
    'Check-ins created' as status,
    COUNT(*) as count
FROM check_ins
WHERE user_id IS NOT NULL
  AND created_at >= NOW() - INTERVAL '4 hours';

-- Show locations with multiple users (for stacking test)
SELECT 
    ci.location_id,
    l.name as location_name,
    l.lat,
    l.lng,
    COUNT(DISTINCT ci.user_id) as user_count,
    COUNT(*) as total_check_ins,
    MAX(ci.created_at) as latest_check_in,
    NOW() - MAX(ci.created_at) as age_minutes
FROM check_ins ci
INNER JOIN locations l ON ci.location_id = l.id
WHERE ci.user_id IS NOT NULL
  AND ci.created_at >= NOW() - INTERVAL '4 hours'
GROUP BY ci.location_id, l.name, l.lat, l.lng
HAVING COUNT(DISTINCT ci.user_id) > 0
ORDER BY user_count DESC, latest_check_in DESC
LIMIT 20;



