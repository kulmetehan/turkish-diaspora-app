-- 083_outreach_audit_log.sql
-- Outreach Audit Logging System
-- Database schema for audit logging of all outreach and claim actions (AVG compliance)
-- Part of claim-consent-outreach-implementation-plan (Fase 9.3)

-- 1. Create outreach_audit_log table
CREATE TABLE IF NOT EXISTS public.outreach_audit_log (
    id BIGSERIAL PRIMARY KEY,
    action_type TEXT NOT NULL, -- email_sent, claim, remove, opt_out, etc.
    location_id BIGINT REFERENCES public.locations(id) ON DELETE SET NULL,
    email TEXT, -- Recipient email address (nullable)
    details JSONB, -- Extra information: timestamp, status, reason, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_outreach_audit_log_action_type ON public.outreach_audit_log(action_type);
CREATE INDEX IF NOT EXISTS idx_outreach_audit_log_location ON public.outreach_audit_log(location_id) WHERE location_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_outreach_audit_log_email ON public.outreach_audit_log(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_outreach_audit_log_created_at ON public.outreach_audit_log(created_at);

-- 3. Add table and column comments for documentation
COMMENT ON TABLE public.outreach_audit_log IS 'Audit log for all outreach and claim actions (AVG compliance). Append-only table - no UPDATE or DELETE operations allowed. Retention policy: 2 years.';
COMMENT ON COLUMN public.outreach_audit_log.action_type IS 'Type of action: email_sent, claim, remove, opt_out, etc.';
COMMENT ON COLUMN public.outreach_audit_log.location_id IS 'Location ID related to the action (nullable).';
COMMENT ON COLUMN public.outreach_audit_log.email IS 'Recipient email address for email-related actions (nullable).';
COMMENT ON COLUMN public.outreach_audit_log.details IS 'Additional information about the action (JSONB): timestamp, status, reason, etc.';
COMMENT ON COLUMN public.outreach_audit_log.created_at IS 'Timestamp when the action occurred (audit log entry creation time).';

-- 4. Add constraint to prevent UPDATE/DELETE (append-only)
-- Note: PostgreSQL doesn't support preventing UPDATE/DELETE at table level,
-- but we can use RLS (Row Level Security) policies or application-level enforcement.
-- For now, we rely on application-level enforcement (no UPDATE/DELETE queries).
-- In production, consider adding RLS policies if needed.

-- 5. Optional: Create a function to enforce append-only (if RLS is enabled in future)
-- This is a placeholder for potential future RLS implementation
-- CREATE POLICY outreach_audit_log_insert_only ON public.outreach_audit_log
--     FOR INSERT
--     TO authenticated
--     WITH CHECK (true);
--
-- CREATE POLICY outreach_audit_log_no_update ON public.outreach_audit_log
--     FOR UPDATE
--     TO authenticated
--     USING (false);
--
-- CREATE POLICY outreach_audit_log_no_delete ON public.outreach_audit_log
--     FOR DELETE
--     TO authenticated
--     USING (false);

