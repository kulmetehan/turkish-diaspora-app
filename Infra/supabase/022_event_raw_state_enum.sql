-- 022_event_raw_state_enum.sql
-- Align event_raw.processing_state constraint with actual worker states.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'event_raw_processing_state_check'
    ) THEN
        ALTER TABLE public.event_raw
            DROP CONSTRAINT event_raw_processing_state_check;
    END IF;
END
$$;

ALTER TABLE public.event_raw
    ADD CONSTRAINT event_raw_processing_state_check
    CHECK (
        processing_state IN (
            'pending',
            'normalized',
            'error_norm',
            'enriched',
            'error'
        )
    );

COMMENT ON CONSTRAINT event_raw_processing_state_check ON public.event_raw
    IS 'Ensures processing_state matches supported worker states.';


