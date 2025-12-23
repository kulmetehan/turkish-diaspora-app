-- Turkish Diaspora App - Event Pipeline Diagnostics
-- Author: LaMarka Digital
-- Description: SQL queries for diagnosing event pipeline bottlenecks and issues

-- A. Pipeline Overview: Events per stage
-- Shows total events in each pipeline stage
SELECT 
    'event_pages_raw' AS stage,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE processing_state = 'pending') AS pending,
    COUNT(*) FILTER (WHERE processing_state = 'extracted') AS processed,
    COUNT(*) FILTER (WHERE processing_state = 'error_extract') AS errors,
    0 AS normalized,
    0 AS enriched
FROM event_pages_raw
UNION ALL
SELECT 
    'event_raw' AS stage,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE processing_state = 'pending') AS pending,
    COUNT(*) FILTER (WHERE processing_state = 'normalized') AS processed,
    COUNT(*) FILTER (WHERE processing_state LIKE 'error%') AS errors,
    COUNT(*) FILTER (WHERE processing_state = 'normalized') AS normalized,
    COUNT(*) FILTER (WHERE processing_state = 'enriched') AS enriched
FROM event_raw
UNION ALL
SELECT 
    'events_candidate' AS stage,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE state = 'candidate') AS pending,
    COUNT(*) FILTER (WHERE duplicate_of_id IS NULL) AS processed,
    COUNT(*) FILTER (WHERE duplicate_of_id IS NOT NULL) AS errors,
    0 AS normalized,
    0 AS enriched
FROM events_candidate
UNION ALL
SELECT 
    'events_public' AS stage,
    COUNT(*) AS total,
    0 AS pending,
    COUNT(*) AS processed,
    0 AS errors,
    0 AS normalized,
    0 AS enriched
FROM events_public;

-- B. Events stuck in event_raw (not normalized)
-- Shows events that are stuck in pending state
SELECT 
    er.id,
    er.title,
    er.start_at,
    er.location_text,
    er.processing_state,
    er.processing_errors,
    er.created_at,
    es.key AS source_key,
    es.name AS source_name
FROM event_raw er
JOIN event_sources es ON es.id = er.event_source_id
WHERE er.processing_state = 'pending'
ORDER BY er.created_at DESC
LIMIT 50;

-- C. Events in events_candidate but not in events_public (with reason)
-- Shows why events are filtered out from public view
SELECT 
    ec.id,
    ec.title,
    ec.location_text,
    ec.country,
    ec.lat,
    ec.lng,
    er.processing_state,
    ec.duplicate_of_id,
    CASE 
        WHEN er.processing_state != 'enriched' THEN 'Not enriched'
        WHEN ec.duplicate_of_id IS NOT NULL THEN 'Duplicate'
        WHEN is_location_blocked(ec.location_text) THEN 'Location blocked'
        WHEN ec.country = 'netherlands' AND is_foreign_city(ec.location_text) THEN 'Wrong country assignment'
        WHEN ec.country IS NOT NULL AND ec.country != 'netherlands' THEN 'Not Netherlands'
        WHEN ec.country IS NULL AND ec.lat IS NOT NULL THEN 'Geocoded but no country'
        ELSE 'Other'
    END AS filter_reason
FROM events_candidate ec
JOIN event_raw er ON er.id = ec.event_raw_id
LEFT JOIN event_sources es ON es.id = ec.event_source_id
WHERE er.processing_state = 'enriched'
  AND ec.id NOT IN (SELECT id FROM events_public)
ORDER BY ec.created_at DESC
LIMIT 50;

-- D. Events with problematic location_text
-- Shows events with locations that might be blocked or incorrect
SELECT 
    ec.id,
    ec.title,
    ec.location_text,
    ec.country,
    is_location_blocked(ec.location_text) AS is_blocked,
    is_foreign_city(ec.location_text) AS is_foreign,
    extract_city_key_from_location(ec.location_text) AS extracted_city,
    es.city_key AS source_city
FROM events_candidate ec
LEFT JOIN event_sources es ON es.id = ec.event_source_id
WHERE ec.location_text IS NOT NULL
  AND (
    is_location_blocked(ec.location_text)
    OR is_foreign_city(ec.location_text)
    OR (ec.country = 'netherlands' AND is_foreign_city(ec.location_text))
  )
ORDER BY ec.created_at DESC
LIMIT 50;

-- E. Events per source (conversion rate)
-- Shows how many events are extracted per source and conversion rates
SELECT 
    es.key AS source_key,
    es.name AS source_name,
    COUNT(DISTINCT epr.id) AS pages_scraped,
    COUNT(DISTINCT er.id) AS events_extracted,
    COUNT(DISTINCT ec.id) AS events_normalized,
    COUNT(DISTINCT CASE WHEN er.processing_state = 'enriched' THEN ec.id END) AS events_enriched,
    COUNT(DISTINCT ep.id) AS events_public,
    ROUND(COUNT(DISTINCT er.id)::numeric / NULLIF(COUNT(DISTINCT epr.id), 0), 2) AS extraction_rate,
    ROUND(COUNT(DISTINCT ep.id)::numeric / NULLIF(COUNT(DISTINCT er.id), 0) * 100, 2) AS public_rate_pct
FROM event_sources es
LEFT JOIN event_pages_raw epr ON epr.event_source_id = es.id
LEFT JOIN event_raw er ON er.event_source_id = es.id
LEFT JOIN events_candidate ec ON ec.event_raw_id = er.id
LEFT JOIN events_public ep ON ep.id = ec.id
GROUP BY es.id, es.key, es.name
ORDER BY events_extracted DESC;

-- F. Recent events flow (last 7 days)
-- Shows events created in the last 7 days and their current state
SELECT 
    DATE(er.created_at) AS date,
    COUNT(*) AS events_created,
    COUNT(*) FILTER (WHERE er.processing_state = 'pending') AS pending,
    COUNT(*) FILTER (WHERE er.processing_state = 'normalized') AS normalized,
    COUNT(*) FILTER (WHERE er.processing_state = 'enriched') AS enriched,
    COUNT(*) FILTER (WHERE er.processing_state LIKE 'error%') AS errors,
    COUNT(DISTINCT ec.id) AS in_candidates,
    COUNT(DISTINCT ep.id) AS in_public
FROM event_raw er
LEFT JOIN events_candidate ec ON ec.event_raw_id = er.id
LEFT JOIN events_public ep ON ep.id = ec.id
WHERE er.created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(er.created_at)
ORDER BY date DESC;

-- G. Events by processing_state breakdown
-- Detailed breakdown of events by processing state
SELECT 
    er.processing_state,
    COUNT(*) AS count,
    COUNT(*) FILTER (WHERE er.start_at >= NOW()) AS future_events,
    COUNT(*) FILTER (WHERE er.start_at < NOW()) AS past_events,
    MIN(er.created_at) AS oldest,
    MAX(er.created_at) AS newest
FROM event_raw er
GROUP BY er.processing_state
ORDER BY count DESC;

-- H. Location issues summary
-- Summary of location-related issues
SELECT 
    COUNT(*) AS total_events,
    COUNT(*) FILTER (WHERE location_text IS NULL) AS no_location,
    COUNT(*) FILTER (WHERE is_location_blocked(location_text)) AS blocked_locations,
    COUNT(*) FILTER (WHERE is_foreign_city(location_text)) AS foreign_cities,
    COUNT(*) FILTER (WHERE country = 'netherlands' AND is_foreign_city(location_text)) AS wrong_country_assignment,
    COUNT(*) FILTER (WHERE country IS NULL AND lat IS NOT NULL) AS geocoded_no_country
FROM events_candidate;

-- I. Sample events stuck in normalization
-- Shows sample events that failed normalization
SELECT 
    er.id,
    er.title,
    er.start_at,
    er.location_text,
    er.processing_state,
    er.processing_errors,
    er.created_at
FROM event_raw er
WHERE er.processing_state = 'error_norm'
ORDER BY er.created_at DESC
LIMIT 20;

-- J. Sample events stuck in enrichment
-- Shows sample events that failed enrichment
SELECT 
    er.id,
    er.title,
    er.start_at,
    er.location_text,
    er.processing_state,
    er.processing_errors,
    er.created_at
FROM event_raw er
WHERE er.processing_state LIKE 'error%'
  AND er.processing_state != 'error_norm'
ORDER BY er.created_at DESC
LIMIT 20;

-- K. Country distribution in events_public (VERIFICATION)
-- Check if country normalization worked correctly
SELECT 
    country,
    COUNT(*) AS count
FROM events_public
GROUP BY country
ORDER BY count DESC;

-- L. London events verification (VERIFICATION)
-- Check if London events are correctly geocoded as "united kingdom"
SELECT 
    id,
    title,
    location_text,
    country,
    lat,
    lng
FROM events_public
WHERE LOWER(location_text) = 'london'
ORDER BY id;

-- M. Zürich events verification (VERIFICATION)
-- Check if Zürich events are correctly geocoded as "switzerland"
SELECT 
    id,
    title,
    location_text,
    country,
    lat,
    lng
FROM events_public
WHERE LOWER(location_text) IN ('zürich', 'zurich')
ORDER BY id;

-- N. Belgium events verification (VERIFICATION)
-- Check if Belgium events are correctly geocoded as "belgium"
SELECT 
    id,
    title,
    location_text,
    country,
    lat,
    lng
FROM events_public
WHERE LOWER(location_text) IN ('antwerpen', 'antwerp', 'brussel', 'brussels')
ORDER BY id;

-- O. Problematic country values check (VERIFICATION)
-- Check if there are any remaining problematic country values
SELECT 
    country,
    COUNT(*) AS count,
    STRING_AGG(DISTINCT location_text, ', ' ORDER BY location_text LIMIT 5) AS sample_locations
FROM events_candidate
WHERE country IS NOT NULL
  AND (
    country LIKE '%schweiz%' OR country LIKE '%suisse%' OR country LIKE '%svizzera%' OR country LIKE '%svizra%'
    OR country LIKE '%belgië%' OR country LIKE '%belgique%' OR country LIKE '%belgien%'
    OR (country = 'germany' AND LOWER(location_text) = 'london')
  )
GROUP BY country
ORDER BY count DESC;

-- P. Events_public summary (VERIFICATION)
-- Overall summary of events_public
SELECT 
    COUNT(*) AS total_events,
    COUNT(*) FILTER (WHERE country = 'netherlands') AS netherlands_events,
    COUNT(*) FILTER (WHERE country = 'belgium') AS belgium_events,
    COUNT(*) FILTER (WHERE country = 'germany') AS germany_events,
    COUNT(*) FILTER (WHERE country = 'switzerland') AS switzerland_events,
    COUNT(*) FILTER (WHERE country = 'united kingdom') AS uk_events,
    COUNT(*) FILTER (WHERE country = 'austria') AS austria_events,
    COUNT(*) FILTER (WHERE country IS NULL) AS no_country
FROM events_public;
















