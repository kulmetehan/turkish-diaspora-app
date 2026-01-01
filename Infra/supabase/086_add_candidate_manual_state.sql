-- 086_add_candidate_manual_state.sql
-- Add CANDIDATE_MANUAL to location_state ENUM for user-submitted locations

-- Add CANDIDATE_MANUAL to location_state ENUM
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'CANDIDATE_MANUAL' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'location_state')
    ) THEN
        ALTER TYPE location_state ADD VALUE 'CANDIDATE_MANUAL';
    END IF;
END $$;

COMMENT ON TYPE location_state IS 'Location state enum. CANDIDATE_MANUAL is for user-submitted locations that need admin review.';





