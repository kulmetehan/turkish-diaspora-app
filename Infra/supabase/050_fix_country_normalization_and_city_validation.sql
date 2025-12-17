-- 050_fix_country_normalization_and_city_validation.sql
-- Fix country normalization for multi-language formats and city validation
-- This corrects:
-- 1. Multi-language country names (e.g., "schweiz/suisse/svizzera/svizra" → "switzerland")
-- 2. London events incorrectly geocoded as "germany" → "united kingdom"

UPDATE events_candidate
SET country = CASE
    -- Multi-language Switzerland formats
    WHEN country LIKE '%schweiz%' OR country LIKE '%suisse%' OR country LIKE '%svizzera%' OR country LIKE '%svizra%' THEN 'switzerland'
    -- Multi-language Belgium formats
    WHEN country LIKE '%belgië%' OR country LIKE '%belgique%' OR country LIKE '%belgien%' THEN 'belgium'
    -- London incorrectly geocoded as Germany
    WHEN country = 'germany' AND LOWER(location_text) = 'london' THEN 'united kingdom'
    ELSE country
END
WHERE country IS NOT NULL
  AND (
    -- Multi-language formats
    country LIKE '%schweiz%' OR country LIKE '%suisse%' OR country LIKE '%svizzera%' OR country LIKE '%svizra%'
    OR country LIKE '%belgië%' OR country LIKE '%belgique%' OR country LIKE '%belgien%'
    -- London in Germany (should be UK)
    OR (country = 'germany' AND LOWER(location_text) = 'london')
  );

COMMENT ON TABLE events_candidate IS 'Event candidates with normalized country values. Multi-language country names are normalized to English (e.g., "switzerland", "belgium", "united kingdom"). Known cities are validated against expected countries.';









