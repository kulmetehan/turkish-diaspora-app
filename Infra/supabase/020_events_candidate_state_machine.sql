-- 020_events_candidate_state_machine.sql
-- Constrain events_candidate.state to the supported admin workflow states.
-- This file must remain additive—existing rows already use 'candidate'.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'events_candidate_state_check'
    ) THEN
        ALTER TABLE public.events_candidate
            ADD CONSTRAINT events_candidate_state_check
            CHECK (
                state IN ('candidate', 'verified', 'published', 'rejected')
            );
    END IF;
END
$$;


