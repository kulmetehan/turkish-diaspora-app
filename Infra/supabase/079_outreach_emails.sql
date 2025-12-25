-- 079_outreach_emails.sql
-- Outreach Emails System
-- Database schema for tracking outreach email status and delivery
-- Part of pre-claim outreach implementation plan (Fase 5.1)

-- 1. Create ENUM type for outreach email status
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'outreach_email_status') THEN
        CREATE TYPE outreach_email_status AS ENUM (
            'queued',      -- In wachtrij
            'sent',        -- Verzonden
            'delivered',   -- Afgeleverd
            'bounced',     -- Teruggekaatst
            'clicked',     -- Link geklikt
            'opted_out'    -- Afgemeld
        );
    END IF;
END$$;

-- 2. Create outreach_emails table
CREATE TABLE IF NOT EXISTS public.outreach_emails (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    contact_id BIGINT NOT NULL REFERENCES public.outreach_contacts(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    status outreach_email_status NOT NULL DEFAULT 'queued',
    ses_message_id TEXT, -- AWS SES message ID for tracking
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    bounced_at TIMESTAMPTZ,
    bounce_reason TEXT, -- Reason for bounce (if bounced)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_outreach_emails_location ON public.outreach_emails(location_id);
CREATE INDEX IF NOT EXISTS idx_outreach_emails_contact ON public.outreach_emails(contact_id);
CREATE INDEX IF NOT EXISTS idx_outreach_emails_status ON public.outreach_emails(status);
CREATE INDEX IF NOT EXISTS idx_outreach_emails_email ON public.outreach_emails(email);
CREATE INDEX IF NOT EXISTS idx_outreach_emails_ses_message_id ON public.outreach_emails(ses_message_id) WHERE ses_message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_outreach_emails_queued ON public.outreach_emails(status, created_at) WHERE status = 'queued';

-- 4. Add constraint to ensure one email per location (max 1 mail per location, ever)
-- Note: This is enforced at application level, but we add a partial unique index for queued/sent status
CREATE UNIQUE INDEX IF NOT EXISTS idx_outreach_emails_location_unique 
    ON public.outreach_emails(location_id) 
    WHERE status IN ('queued', 'sent', 'delivered', 'clicked');

-- 5. Add table and column comments for documentation
COMMENT ON TABLE public.outreach_emails IS 'Tracking table for outreach emails sent to location contacts. Tracks email status, delivery, bounces, and clicks. Max 1 email per location (enforced by unique index).';
COMMENT ON COLUMN public.outreach_emails.location_id IS 'Location for which email was sent.';
COMMENT ON COLUMN public.outreach_emails.contact_id IS 'Contact information used for this email (references outreach_contacts).';
COMMENT ON COLUMN public.outreach_emails.email IS 'Recipient email address (denormalized for quick queries).';
COMMENT ON COLUMN public.outreach_emails.status IS 'Email status: queued (in queue), sent (sent to provider), delivered (confirmed delivery), bounced (bounced back), clicked (link clicked), opted_out (user opted out).';
COMMENT ON COLUMN public.outreach_emails.ses_message_id IS 'AWS SES message ID for tracking delivery and bounces via SES webhooks.';
COMMENT ON COLUMN public.outreach_emails.sent_at IS 'Timestamp when email was sent to email provider (SES).';
COMMENT ON COLUMN public.outreach_emails.delivered_at IS 'Timestamp when email was confirmed delivered (via SES delivery event).';
COMMENT ON COLUMN public.outreach_emails.clicked_at IS 'Timestamp when user clicked a link in the email.';
COMMENT ON COLUMN public.outreach_emails.bounced_at IS 'Timestamp when email bounced (via SES bounce event).';
COMMENT ON COLUMN public.outreach_emails.bounce_reason IS 'Reason for bounce (provided by SES bounce event).';

