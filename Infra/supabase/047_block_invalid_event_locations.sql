-- 047_block_invalid_event_locations.sql
-- Block invalid event locations in events_public view and fix wrong country assignments

-- Extend is_location_blocked function to also block standalone foreign cities
CREATE OR REPLACE FUNCTION is_location_blocked(location_text TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    location_lower TEXT;
BEGIN
    IF location_text IS NULL OR location_text = '' THEN
        RETURN FALSE;
    END IF;
    
    location_lower := LOWER(TRIM(location_text));
    
    -- Block US cities with "Netherlands" suffix
    IF (location_lower LIKE '%washington%' OR location_lower LIKE '%houston%' OR location_lower LIKE '%lodi%' 
        OR location_lower LIKE '%new york%' OR location_lower LIKE '%los angeles%' OR location_lower LIKE '%chicago%')
       AND location_lower LIKE '%netherlands%' THEN
        RETURN TRUE;
    END IF;
    
    -- Block German cities with "Netherlands" suffix
    IF (location_lower LIKE '%berlin%' OR location_lower LIKE '%münchen%' OR location_lower LIKE '%munchen%' 
        OR location_lower LIKE '%köln%' OR location_lower LIKE '%koln%' OR location_lower LIKE '%hamburg%' 
        OR location_lower LIKE '%frankfurt%')
       AND location_lower LIKE '%netherlands%' THEN
        RETURN TRUE;
    END IF;
    
    -- Block standalone US cities without context (likely errors)
    IF location_lower = 'washington' OR location_lower = 'houston' OR location_lower = 'lodi' THEN
        RETURN TRUE;
    END IF;
    
    -- Block if it's "City, Netherlands" pattern for blocked cities
    IF (location_lower LIKE 'washington, netherlands%' 
        OR location_lower LIKE 'houston, netherlands%' 
        OR location_lower LIKE 'lodi, netherlands%') THEN
        RETURN TRUE;
    END IF;
    
    -- Block standalone German cities (without Netherlands suffix, but still foreign)
    IF location_lower IN ('berlin', 'münchen', 'munchen', 'köln', 'koln', 'hamburg', 
        'frankfurt', 'stuttgart', 'düsseldorf', 'dusseldorf', 'offenbach', 'mannheim', 
        'hannover', 'bochum', 'nürnberg', 'nurnberg') THEN
        RETURN TRUE;
    END IF;
    
    -- Block UK cities
    IF location_lower = 'london' THEN
        RETURN TRUE;
    END IF;
    
    -- Block Austrian cities
    IF location_lower = 'vienna' OR location_lower = 'wien' THEN
        RETURN TRUE;
    END IF;
    
    -- Block Swiss cities
    IF location_lower = 'zürich' OR location_lower = 'zurich' THEN
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION is_location_blocked IS 'Checks if location should be blocked due to invalid patterns. Blocks standalone foreign cities (German, UK, Austrian, Swiss) and cities with "Netherlands" suffix. Matches Python logic in event_geocoding_bot.py.';

-- Helper function to detect if location_text is a foreign city (not Netherlands/Belgium)
CREATE OR REPLACE FUNCTION is_foreign_city(location_text TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    location_lower TEXT;
BEGIN
    IF location_text IS NULL OR location_text = '' THEN
        RETURN FALSE;
    END IF;
    
    location_lower := LOWER(TRIM(location_text));
    
    -- German cities
    IF location_lower IN ('berlin', 'münchen', 'munchen', 'köln', 'koln', 'hamburg', 
        'frankfurt', 'stuttgart', 'düsseldorf', 'dusseldorf', 'offenbach', 'mannheim', 
        'hannover', 'bochum', 'nürnberg', 'nurnberg') THEN
        RETURN TRUE;
    END IF;
    
    -- UK cities
    IF location_lower = 'london' THEN
        RETURN TRUE;
    END IF;
    
    -- Austrian cities
    IF location_lower = 'vienna' OR location_lower = 'wien' THEN
        RETURN TRUE;
    END IF;
    
    -- Swiss cities
    IF location_lower = 'zürich' OR location_lower = 'zurich' THEN
        RETURN TRUE;
    END IF;
    
    -- US cities
    IF location_lower IN ('washington', 'houston', 'lodi', 'new york', 'los angeles', 'chicago') THEN
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION is_foreign_city IS 'Detects if location_text is a foreign city (not Netherlands/Belgium). Used to filter events with wrong country assignments.';

-- Update events_public view to use blocking functions
CREATE OR REPLACE VIEW public.events_public AS
SELECT
    ec.id,
    ec.event_source_id,
    ec.event_raw_id,
    ec.title,
    ec.description,
    ec.start_time_utc,
    ec.end_time_utc,
    ec.location_text,
    ec.url,
    ec.source_key,
    ec.ingest_hash,
    ec.state,
    ec.created_at,
    ec.updated_at,
    er.category_key,
    er.summary_ai,
    er.confidence_score,
    er.language_code,
    -- Extract city_key from location_text first, fallback to source city_key
    COALESCE(
        extract_city_key_from_location(ec.location_text),
        es.city_key
    ) AS city_key,
    ec.lat,
    ec.lng,
    ec.country
FROM public.events_candidate ec
JOIN public.event_raw er ON er.id = ec.event_raw_id
LEFT JOIN public.event_sources es ON es.id = ec.event_source_id
WHERE er.processing_state = 'enriched'
  AND ec.duplicate_of_id IS NULL
  -- Block invalid locations even if not yet geocoded
  AND NOT is_location_blocked(ec.location_text)
  -- Block events with wrong country assignment (country=nederland but location is foreign city)
  AND NOT (ec.country = 'netherlands' AND is_foreign_city(ec.location_text))
  AND (
    -- Only show Netherlands events (or events not yet geocoded)
    ec.country = 'netherlands'
    OR
    -- Temporary: allow events without country until they are geocoded
    -- This ensures existing events are still visible until geocoding bot runs
    -- After geocoding, events with country = 'belgium' etc. will be automatically filtered out
    (ec.country IS NULL AND ec.lat IS NULL AND ec.lng IS NULL)
  );
