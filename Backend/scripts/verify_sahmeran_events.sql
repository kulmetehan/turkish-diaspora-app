-- Verificatie queries voor Sahmeran events pipeline
-- Voer deze uit na elke stap om te controleren of alles goed werkt

-- 1. Controleer event_pages_raw status
SELECT 
    processing_state,
    COUNT(*) as count
FROM event_pages_raw
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
GROUP BY processing_state
ORDER BY processing_state;

-- 2. Controleer event_raw records met detail page informatie
SELECT 
    er.id,
    er.title,
    er.location_text,
    er.venue,
    er.event_url,
    er.processing_state,
    CASE 
        WHEN er.raw_payload ? 'detail_page_extracted' THEN 'yes'
        ELSE 'no'
    END as detail_page_extracted,
    er.raw_payload->>'detail_page_url' as detail_page_url,
    er.raw_payload->'detail_page_extracted_event'->>'venue' as extracted_venue_from_detail,
    er.raw_payload->'detail_page_extracted_event'->>'location_text' as extracted_location_from_detail
FROM event_raw er
WHERE er.event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
ORDER BY er.created_at DESC
LIMIT 20;

-- 3. Controleer events_candidate met locatie informatie
SELECT 
    ec.id,
    ec.location_text,
    ec.lat,
    ec.lng,
    ec.country,
    er.venue,
    er.title,
    CASE 
        WHEN ec.location_text IS NOT NULL AND ec.lat IS NOT NULL AND ec.lng IS NOT NULL THEN 'geocoded'
        WHEN ec.location_text IS NOT NULL AND ec.lat IS NULL THEN 'needs_geocoding'
        WHEN ec.location_text IS NULL THEN 'no_location'
        ELSE 'unknown'
    END as status
FROM events_candidate ec
JOIN event_raw er ON er.id = ec.event_raw_id
WHERE ec.event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
ORDER BY ec.created_at DESC
LIMIT 20;

-- 4. Samenvatting: Totaal aantal events en status
SELECT 
    COUNT(*) as total_events,
    COUNT(*) FILTER (WHERE ec.location_text IS NOT NULL) as with_location,
    COUNT(*) FILTER (WHERE ec.lat IS NOT NULL AND ec.lng IS NOT NULL) as with_coordinates,
    COUNT(*) FILTER (WHERE ec.lat IS NOT NULL AND ec.lng IS NOT NULL AND ec.country = 'netherlands') as in_netherlands,
    COUNT(*) FILTER (WHERE er.venue IS NOT NULL AND ec.lat IS NOT NULL AND ec.lng IS NOT NULL) as with_venue_and_coords
FROM events_candidate ec
JOIN event_raw er ON er.id = ec.event_raw_id
WHERE ec.event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');

-- 5. Controleer detail pages die zijn opgehaald
SELECT 
    COUNT(*) FILTER (WHERE er.raw_payload ? 'detail_page_extracted') as detail_pages_fetched,
    COUNT(*) FILTER (WHERE er.raw_payload ? 'detail_page_extracted' 
                     AND er.raw_payload->'detail_page_extracted_event'->>'location_text' IS NOT NULL) as detail_pages_with_location,
    COUNT(*) FILTER (WHERE er.raw_payload ? 'detail_page_extracted' 
                     AND er.raw_payload->'detail_page_extracted_event'->>'venue' IS NOT NULL) as detail_pages_with_venue
FROM event_raw er
WHERE er.event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');

-- 6. Events met alleen stad naam (zonder venue of adres)
SELECT 
    ec.id,
    ec.location_text,
    er.venue,
    ec.lat,
    ec.lng,
    CASE 
        WHEN er.venue IS NULL AND ec.location_text ~ '^[A-Za-z\s]+$' THEN 'only_city_name'
        WHEN er.venue IS NOT NULL OR ec.location_text ~ '\d' THEN 'has_details'
        ELSE 'unknown'
    END as location_type
FROM events_candidate ec
JOIN event_raw er ON er.id = ec.event_raw_id
WHERE ec.event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
  AND ec.location_text IS NOT NULL
ORDER BY ec.created_at DESC
LIMIT 30;





