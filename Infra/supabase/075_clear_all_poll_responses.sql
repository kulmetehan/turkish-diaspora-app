-- 075_clear_all_poll_responses.sql
-- Clear all poll responses for testing purposes
-- This removes all poll responses from the database

-- Delete all poll responses
-- Note: This will cascade delete related activity_stream entries if they exist
DELETE FROM public.poll_responses;

-- Reset the sequence (optional, but good practice)
-- This ensures new poll responses start with ID 1 if you want a clean slate
-- ALTER SEQUENCE public.poll_responses_id_seq RESTART WITH 1;

-- Note: If you also want to clear poll-related activity stream entries:
-- DELETE FROM public.activity_stream WHERE activity_type = 'poll_response';

