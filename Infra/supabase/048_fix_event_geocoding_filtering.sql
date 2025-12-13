-- 048_fix_event_geocoding_filtering.sql
-- Fix event geocoding and filtering: geocode first, filter by country after
-- This allows foreign events to be geocoded before filtering, ensuring only
-- Netherlands events appear in events_public

-- Update is_location_blocked function: only block clearly invalid patterns
-- Remove blocking of standalone foreign cities (they should be geocoded first)
CREATE OR REPLACE FUNCTION is_location_blocked(location_text TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    location_lower TEXT;
BEGIN
    IF location_text IS NULL OR location_text = '' THEN
        RETURN FALSE;
    END IF;
    
    location_lower := LOWER(TRIM(location_text));
    
    -- Block US cities with "Netherlands" suffix (clearly wrong)
    IF (location_lower LIKE '%washington%' OR location_lower LIKE '%houston%' OR location_lower LIKE '%lodi%' 
        OR location_lower LIKE '%new york%' OR location_lower LIKE '%los angeles%' OR location_lower LIKE '%chicago%')
       AND location_lower LIKE '%netherlands%' THEN
        RETURN TRUE;
    END IF;
    
    -- Block German cities with "Netherlands" suffix (clearly wrong)
    IF (location_lower LIKE '%berlin%' OR location_lower LIKE '%münchen%' OR location_lower LIKE '%munchen%' 
        OR location_lower LIKE '%köln%' OR location_lower LIKE '%koln%' OR location_lower LIKE '%hamburg%' 
        OR location_lower LIKE '%frankfurt%')
       AND location_lower LIKE '%netherlands%' THEN
        RETURN TRUE;
    END IF;
    
    -- Block if it's "City, Netherlands" pattern for clearly wrong cities
    IF (location_lower LIKE 'washington, netherlands%' 
        OR location_lower LIKE 'houston, netherlands%' 
        OR location_lower LIKE 'lodi, netherlands%'
        OR location_lower LIKE 'berlin, netherlands%'
        OR location_lower LIKE 'london, netherlands%') THEN
        RETURN TRUE;
    END IF;
    
    -- Do NOT block standalone foreign cities - they should be geocoded first
    -- The geocoding bot will geocode them and set country, then events_public
    -- will filter by country = 'netherlands'
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION is_location_blocked IS 'Checks if location should be blocked due to clearly invalid patterns (e.g., "Washington, Netherlands"). Does NOT block standalone foreign cities - they should be geocoded first, then filtered by country.';

-- Update events_public view: filter by country for geocoded events,
-- use is_location_blocked() only for non-geocoded events with clearly wrong patterns
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
    -- For geocoded events: filter by country = 'netherlands' (accept both English and Dutch spelling)
    (ec.country IS NOT NULL AND (ec.country = 'netherlands' OR ec.country = 'nederland'))
    OR
    -- For non-geocoded events: only block clearly invalid patterns
    -- Allow standalone foreign cities to pass through until geocoding
    (ec.country IS NULL AND ec.lat IS NULL AND ec.lng IS NULL 
     AND NOT is_location_blocked(ec.location_text))
  );

COMMENT ON VIEW public.events_public IS 'Public events view. Shows only Netherlands events (country = netherlands or nederland) for geocoded events. For non-geocoded events, only blocks clearly invalid patterns (e.g., "Washington, Netherlands"). Foreign cities are allowed until geocoding bot processes them.';
