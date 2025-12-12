-- 046_fix_event_city_extraction.sql
-- Fix events_public view to extract city_key from location_text instead of source

-- Helper function to extract city_key from location_text
CREATE OR REPLACE FUNCTION extract_city_key_from_location(location_text TEXT)
RETURNS TEXT AS $$
DECLARE
    location_lower TEXT;
BEGIN
    IF location_text IS NULL OR location_text = '' THEN
        RETURN NULL;
    END IF;
    
    location_lower := LOWER(location_text);
    
    -- Map city patterns to city_keys (matching Python logic in event_geocoding_bot.py)
    -- Netherlands cities
    IF location_lower LIKE '%rotterdam%' THEN
        RETURN 'rotterdam';
    ELSIF location_lower LIKE '%amsterdam%' THEN
        RETURN 'amsterdam';
    ELSIF location_lower LIKE '%den haag%' OR location_lower LIKE '%the hague%' OR location_lower LIKE '%''s-gravenhage%' OR location_lower LIKE '%s-gravenhage%' THEN
        RETURN 'den_haag';
    ELSIF location_lower LIKE '%utrecht%' THEN
        RETURN 'utrecht';
    ELSIF location_lower LIKE '%eindhoven%' THEN
        RETURN 'eindhoven';
    ELSIF location_lower LIKE '%groningen%' THEN
        RETURN 'groningen';
    ELSIF location_lower LIKE '%tilburg%' THEN
        RETURN 'tilburg';
    ELSIF location_lower LIKE '%almere%' THEN
        RETURN 'almere';
    ELSIF location_lower LIKE '%breda%' THEN
        RETURN 'breda';
    ELSIF location_lower LIKE '%nijmegen%' THEN
        RETURN 'nijmegen';
    ELSIF location_lower LIKE '%enschede%' THEN
        RETURN 'enschede';
    ELSIF location_lower LIKE '%haarlem%' THEN
        RETURN 'haarlem';
    ELSIF location_lower LIKE '%arnhem%' THEN
        RETURN 'arnhem';
    ELSIF location_lower LIKE '%zaanstad%' THEN
        RETURN 'zaanstad';
    ELSIF location_lower LIKE '%amersfoort%' THEN
        RETURN 'amersfoort';
    ELSIF location_lower LIKE '%apeldoorn%' THEN
        RETURN 'apeldoorn';
    -- Belgium cities
    ELSIF location_lower LIKE '%antwerpen%' OR location_lower LIKE '%antwerp%' THEN
        RETURN 'antwerpen';
    ELSIF location_lower LIKE '%brussel%' OR location_lower LIKE '%brussels%' OR location_lower LIKE '%bruxelles%' THEN
        RETURN 'brussel';
    ELSIF location_lower LIKE '%gent%' OR location_lower LIKE '%ghent%' THEN
        RETURN 'gent';
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION extract_city_key_from_location IS 'Extracts city_key from location_text using pattern matching. Returns city_key (e.g., rotterdam, amsterdam, antwerpen) or NULL if no match found. Matches Python logic in event_geocoding_bot.py.';

-- Update events_public view to use extracted city_key from location_text, fallback to source city_key
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
  AND (
    -- Only show Netherlands events (or events not yet geocoded)
    ec.country = 'netherlands'
    OR
    -- Temporary: allow events without country until they are geocoded
    -- This ensures existing events are still visible until geocoding bot runs
    -- After geocoding, events with country = 'belgium' etc. will be automatically filtered out
    (ec.country IS NULL AND ec.lat IS NULL AND ec.lng IS NULL)
  );
