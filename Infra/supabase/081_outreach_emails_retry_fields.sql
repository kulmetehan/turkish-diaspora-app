-- 081_outreach_emails_retry_fields.sql
-- Add retry fields to outreach_emails table for retry logic
-- Part of claim-consent-outreach implementation plan (Stap 6.4)

-- 1. Add retry_count column
ALTER TABLE public.outreach_emails
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

-- 2. Add last_retry_at column
ALTER TABLE public.outreach_emails
ADD COLUMN IF NOT EXISTS last_retry_at TIMESTAMPTZ;

-- 3. Create index for retry queries (emails that need retry)
CREATE INDEX IF NOT EXISTS idx_outreach_emails_retry 
ON public.outreach_emails(status, retry_count, last_retry_at) 
WHERE status = 'queued' AND retry_count < 2;

-- 4. Add column comments
COMMENT ON COLUMN public.outreach_emails.retry_count IS 'Number of retry attempts for this email. Max 2 retries allowed.';
COMMENT ON COLUMN public.outreach_emails.last_retry_at IS 'Timestamp of last retry attempt. Used for exponential backoff (1 hour, then 4 hours).';

