-- Fix events with midnight times by removing old events_candidate records
-- and resetting new event_raw records for re-normalization

-- Step 1: Find and delete old events_candidate records that have midnight times
-- These are the ones currently showing in events_public with wrong times
DELETE FROM events_candidate
WHERE id IN (
    SELECT ec.id
    FROM events_candidate ec
    JOIN event_raw er ON er.id = ec.event_raw_id
    WHERE (ec.title ILIKE '%ILKER AYRIK%GERÇEKLER ACIDIR%' 
       OR (ec.title ILIKE '%IBRAHIM SELIM%' AND ec.title ILIKE '%AMSTERDAM%'))
      AND ec.start_time_utc > NOW()
      AND (
          EXTRACT(HOUR FROM ec.start_time_utc AT TIME ZONE 'Europe/Amsterdam') = 0
          AND EXTRACT(MINUTE FROM ec.start_time_utc AT TIME ZONE 'Europe/Amsterdam') = 0
      )
      AND ec.duplicate_of_id IS NULL
)
RETURNING id, title, start_time_utc, event_raw_id;

-- Step 2: Reset event_raw records with good times back to pending
-- These are the records that were extracted from detail pages with correct times
UPDATE event_raw
SET processing_state = 'pending'
WHERE id IN (
    SELECT id FROM event_raw
    WHERE (title ILIKE '%ILKER AYRIK%GERÇEKLER ACIDIR%' 
       OR (title ILIKE '%IBRAHIM SELIM%' AND title ILIKE '%AMSTERDAM%'))
      AND start_at > NOW()
      AND processing_state = 'enriched'
      -- Only reset records that have non-midnight times in Amsterdam timezone
      AND NOT (
          EXTRACT(HOUR FROM start_at AT TIME ZONE 'Europe/Amsterdam') = 0
          AND EXTRACT(MINUTE FROM start_at AT TIME ZONE 'Europe/Amsterdam') = 0
      )
)
RETURNING id, title, start_at, 
    TO_CHAR(start_at AT TIME ZONE 'Europe/Amsterdam', 'HH24:MI') as start_time_amsterdam,
    processing_state;
