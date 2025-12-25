-- 081_token_claims_reminder_sent.sql
-- Add reminder_sent_at column to token_location_claims
-- Part of claim-consent-outreach-implementation-plan (Fase 8.1)

-- 1. Add reminder_sent_at column
ALTER TABLE public.token_location_claims
ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMPTZ;

-- 2. Create index for performance (partial index for NULL values)
CREATE INDEX IF NOT EXISTS idx_token_claims_reminder_sent_at_null 
ON public.token_location_claims(reminder_sent_at) 
WHERE reminder_sent_at IS NULL;

-- 3. Add column comment for documentation
COMMENT ON COLUMN public.token_location_claims.reminder_sent_at IS 'Timestamp when expiry reminder email was sent. NULL means reminder not yet sent.';

