-- 049_normalize_existing_country_values.sql
-- Normalize existing country values in events_candidate to English spelling
-- This fixes events that were geocoded before the normalization was added

UPDATE events_candidate
SET country = CASE
    WHEN country = 'nederland' THEN 'netherlands'
    WHEN country = 'holland' THEN 'netherlands'
    WHEN country = 'deutschland' THEN 'germany'
    WHEN country = 'duitsland' THEN 'germany'
    WHEN country = 'belgië' THEN 'belgium'
    WHEN country = 'belgie' THEN 'belgium'
    WHEN country = 'belgique' THEN 'belgium'
    WHEN country = 'österreich' THEN 'austria'
    WHEN country = 'oostenrijk' THEN 'austria'
    WHEN country = 'schweiz' THEN 'switzerland'
    WHEN country = 'suisse' THEN 'switzerland'
    WHEN country = 'zwitserland' THEN 'switzerland'
    ELSE country
END
WHERE country IS NOT NULL
  AND country IN ('nederland', 'holland', 'deutschland', 'duitsland', 
                  'belgië', 'belgie', 'belgique', 'österreich', 'oostenrijk',
                  'schweiz', 'suisse', 'zwitserland');

COMMENT ON TABLE events_candidate IS 'Normalized event candidates. Country values are normalized to English (e.g., "netherlands", "germany", "belgium").';









