-- Debug queries to detect stringified JSON issues in overpass_calls
-- Run these after a discovery session to check for the TypeError root cause

-- 1. Check for stringified JSON in raw_preview
SELECT 
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE raw_preview LIKE '%"elements":"[%') as stringified_elements,
    COUNT(*) FILTER (WHERE raw_preview LIKE '%\\"elements\\":\\"[%') as escaped_stringified_elements,
    COUNT(*) FILTER (WHERE raw_preview LIKE '%"elements":%') as has_elements_key
FROM overpass_calls
WHERE ts >= now() - interval '1 hour';

-- 2. Show examples of problematic calls
SELECT 
    id,
    ts,
    endpoint,
    status_code,
    found,
    normalized,
    LEFT(raw_preview, 200) as preview_snippet
FROM overpass_calls
WHERE ts >= now() - interval '1 hour'
  AND (raw_preview LIKE '%"elements":"[%' OR raw_preview LIKE '%\\"elements\\":\\"[%')
ORDER BY ts DESC
LIMIT 10;

-- 3. Check for JSON decode errors
SELECT 
    status_code,
    COUNT(*) as count,
    AVG(duration_ms) as avg_duration_ms
FROM overpass_calls
WHERE ts >= now() - interval '1 hour'
  AND error_message LIKE '%JSON%'
GROUP BY status_code
ORDER BY count DESC;

-- 4. Recent successful vs failed calls
SELECT 
    CASE 
        WHEN status_code = 200 THEN 'success'
        WHEN status_code >= 500 THEN 'server_error'
        WHEN status_code = 429 THEN 'rate_limited'
        WHEN status_code = 504 THEN 'timeout'
        ELSE 'other_error'
    END as call_type,
    COUNT(*) as count,
    AVG(found) as avg_found,
    AVG(normalized) as avg_normalized
FROM overpass_calls
WHERE ts >= now() - interval '1 hour'
GROUP BY 1
ORDER BY count DESC;

-- 5. Check for elements type issues
SELECT 
    cell_id,
    found,
    normalized,
    CASE 
        WHEN found > 0 AND normalized = 0 THEN 'found_but_not_normalized'
        WHEN found = normalized THEN 'perfect_normalization'
        WHEN found > normalized THEN 'partial_normalization'
        ELSE 'no_results'
    END as normalization_status,
    LEFT(raw_preview, 100) as preview
FROM overpass_calls
WHERE ts >= now() - interval '1 hour'
  AND status_code = 200
ORDER BY found DESC
LIMIT 20;
