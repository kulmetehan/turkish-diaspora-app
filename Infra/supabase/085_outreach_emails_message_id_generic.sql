-- 085_outreach_emails_message_id_generic.sql
-- Add generic message_id column for provider-agnostic email tracking
-- Part of SES to Brevo migration plan

-- 1. Add new message_id column
ALTER TABLE public.outreach_emails 
ADD COLUMN IF NOT EXISTS message_id TEXT;

-- 2. Copy existing ses_message_id values to message_id
UPDATE public.outreach_emails 
SET message_id = ses_message_id 
WHERE ses_message_id IS NOT NULL AND message_id IS NULL;

-- 3. Create index on message_id
CREATE INDEX IF NOT EXISTS idx_outreach_emails_message_id 
ON public.outreach_emails(message_id) 
WHERE message_id IS NOT NULL;

-- 4. Update column comments
COMMENT ON COLUMN public.outreach_emails.message_id IS 'Provider message ID for tracking (SES, Brevo, etc.). Replaces ses_message_id for provider-agnostic tracking.';
COMMENT ON COLUMN public.outreach_emails.ses_message_id IS 'DEPRECATED: Use message_id instead. Kept for backward compatibility with existing SES-sent emails.';

