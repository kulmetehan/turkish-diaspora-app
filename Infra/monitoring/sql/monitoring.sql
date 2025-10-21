-- Turkish Diaspora App - OSM Discovery Monitoring Queries
-- Author: LaMarka Digital
-- Description: SQL queries for monitoring Overpass API usage and discovery performance

-- A. Insert rate (last 90 minutes)
-- Shows how many locations are being inserted per minute by category
SELECT 
    date_trunc('minute', first_seen_at) AS minute,
    category, 
    COUNT(*) AS inserts
FROM locations
WHERE source = 'OSM_OVERPASS'
  AND first_seen_at >= now() - interval '90 minutes'
GROUP BY 1, 2 
ORDER BY 1, 2;

-- B. Capped cells (where found >= max_results)
-- Identifies cells that hit the result limit and may need subdivision
SELECT 
    category_set,
    COUNT(*) FILTER (WHERE found >= 50 AND normalized = 50) AS fully_capped,
    COUNT(*) AS total_cells,
    ROUND(
        COUNT(*) FILTER (WHERE found >= 50 AND normalized = 50) * 100.0 / COUNT(*), 
        2
    ) AS capped_percentage
FROM overpass_calls
WHERE ts >= now() - interval '6 hours'
GROUP BY 1 
ORDER BY fully_capped DESC;

-- C. Recent OSM records
-- Shows the most recently discovered locations from OSM
SELECT 
    id, 
    name, 
    category, 
    lat, 
    lng, 
    first_seen_at,
    source
FROM locations
WHERE source = 'OSM_OVERPASS'
ORDER BY first_seen_at DESC
LIMIT 50;

-- D. Duplicate names within ~80 meters
-- Identifies potential duplicate locations that are very close together
WITH base AS (
    SELECT 
        id, 
        name, 
        lat::float AS lat, 
        lng::float AS lng
    FROM locations
    WHERE is_retired IS NOT TRUE
        AND name IS NOT NULL
        AND lat IS NOT NULL 
        AND lng IS NOT NULL
), pairs AS (
    SELECT 
        a.id AS a_id, 
        b.id AS b_id, 
        a.name,
        111320 * sqrt(
            power(a.lat - b.lat, 2) + power(a.lng - b.lng, 2)
        ) AS meters
    FROM base a
    JOIN base b ON a.name = b.name AND a.id < b.id
)
SELECT * 
FROM pairs 
WHERE meters <= 80 
ORDER BY meters;

-- E. Overpass API performance metrics
-- Shows success rates, response times, and error patterns
SELECT 
    endpoint,
    COUNT(*) AS total_calls,
    COUNT(*) FILTER (WHERE status_code = 200) AS successful_calls,
    COUNT(*) FILTER (WHERE status_code >= 500) AS server_errors,
    COUNT(*) FILTER (WHERE status_code = 429) AS rate_limited,
    COUNT(*) FILTER (WHERE status_code = 504) AS timeouts,
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms,
    ROUND(AVG(found), 2) AS avg_found,
    ROUND(AVG(normalized), 2) AS avg_normalized,
    ROUND(
        COUNT(*) FILTER (WHERE status_code = 200) * 100.0 / COUNT(*), 
        2
    ) AS success_rate_pct
FROM overpass_calls
WHERE ts >= now() - interval '24 hours'
GROUP BY endpoint
ORDER BY total_calls DESC;

-- F. Category discovery efficiency
-- Shows which categories are being discovered most effectively
SELECT 
    unnest(category_set) AS category,
    COUNT(*) AS total_calls,
    SUM(found) AS total_found,
    SUM(normalized) AS total_normalized,
    ROUND(AVG(found), 2) AS avg_found_per_call,
    ROUND(AVG(normalized), 2) AS avg_normalized_per_call,
    ROUND(
        SUM(normalized) * 100.0 / NULLIF(SUM(found), 0), 
        2
    ) AS normalization_rate_pct
FROM overpass_calls
WHERE ts >= now() - interval '24 hours'
    AND status_code = 200
GROUP BY 1
ORDER BY total_normalized DESC;

-- G. Cell subdivision analysis
-- Shows which cells are being subdivided and their performance
SELECT 
    cell_id,
    COUNT(*) AS attempts,
    MAX(attempt) AS max_attempt,
    SUM(found) AS total_found,
    SUM(normalized) AS total_normalized,
    MIN(ts) AS first_attempt,
    MAX(ts) AS last_attempt,
    MAX(duration_ms) AS max_duration_ms
FROM overpass_calls
WHERE ts >= now() - interval '24 hours'
GROUP BY cell_id
HAVING COUNT(*) > 1  -- Only cells that were subdivided
ORDER BY attempts DESC, total_found DESC;

-- H. Error analysis
-- Detailed breakdown of errors and their patterns
SELECT 
    status_code,
    error_message,
    endpoint,
    COUNT(*) AS error_count,
    MIN(ts) AS first_error,
    MAX(ts) AS last_error
FROM overpass_calls
WHERE status_code != 200
    AND ts >= now() - interval '24 hours'
GROUP BY 1, 2, 3
ORDER BY error_count DESC;

-- I. Rate limiting analysis
-- Shows rate limiting patterns and retry behavior
SELECT 
    date_trunc('hour', ts) AS hour,
    endpoint,
    COUNT(*) AS total_calls,
    COUNT(*) FILTER (WHERE status_code = 429) AS rate_limited,
    COUNT(*) FILTER (WHERE attempt > 1) AS retries,
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms
FROM overpass_calls
WHERE ts >= now() - interval '7 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- J. Discovery coverage by geographic area
-- Shows discovery performance across different geographic regions
SELECT 
    CASE 
        WHEN lat BETWEEN 51.0 AND 52.0 AND lng BETWEEN 4.0 AND 5.0 THEN 'Rotterdam'
        WHEN lat BETWEEN 52.0 AND 53.0 AND lng BETWEEN 4.0 AND 5.0 THEN 'Amsterdam'
        WHEN lat BETWEEN 50.0 AND 51.0 AND lng BETWEEN 4.0 AND 5.0 THEN 'South Holland'
        ELSE 'Other'
    END AS region,
    COUNT(*) AS locations,
    COUNT(DISTINCT category) AS categories_found
FROM locations
WHERE source = 'OSM_OVERPASS'
    AND first_seen_at >= now() - interval '7 days'
    AND lat IS NOT NULL 
    AND lng IS NOT NULL
GROUP BY 1
ORDER BY locations DESC;
