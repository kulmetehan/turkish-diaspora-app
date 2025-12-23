-- Reset script voor Sahmeran events
-- Voer deze queries uit in de juiste volgorde

-- Stap 1: Reset event_pages_raw naar pending voor Sahmeran
UPDATE event_pages_raw
SET processing_state = 'pending',
    errors = NULL,
    updated_at = now()
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');

-- Stap 2: Verwijder alle event_raw records voor Sahmeran
DELETE FROM event_raw
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');

-- Stap 3: Verwijder alle events_candidate records voor Sahmeran
DELETE FROM events_candidate
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');

-- Stap 4: Reset detail_page_extracted flags in raw_payload (voor event_raw die mogelijk blijven)
-- Dit is alleen nodig als er event_raw records zijn die niet via event_source_id gekoppeld zijn
UPDATE event_raw
SET raw_payload = raw_payload - 'detail_page_extracted' - 'detail_page_url' - 'detail_page_extracted_event',
    updated_at = now()
WHERE raw_payload ? 'detail_page_extracted'
  AND event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');

-- Verificatie query: Controleer of alles is gereset
SELECT 
    'event_pages_raw' as table_name,
    COUNT(*) FILTER (WHERE processing_state = 'pending') as pending_count,
    COUNT(*) as total_count
FROM event_pages_raw
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
UNION ALL
SELECT 
    'event_raw' as table_name,
    0 as pending_count,
    COUNT(*) as total_count
FROM event_raw
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
UNION ALL
SELECT 
    'events_candidate' as table_name,
    0 as pending_count,
    COUNT(*) as total_count
FROM events_candidate
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');
















