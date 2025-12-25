-- 080_outreach_emails_opt_out_token.sql
-- Add opt_out_token column to outreach_emails table for secure opt-out links
-- Part of claim-consent-outreach implementation plan (Stap 6.4)

-- 1. Add opt_out_token column
ALTER TABLE public.outreach_emails
ADD COLUMN IF NOT EXISTS opt_out_token TEXT;

-- 2. Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_outreach_emails_opt_out_token 
ON public.outreach_emails(opt_out_token) 
WHERE opt_out_token IS NOT NULL;

-- 3. Add column comment
COMMENT ON COLUMN public.outreach_emails.opt_out_token IS 'Secure token for opt-out links. Generated per email for secure opt-out functionality.';

