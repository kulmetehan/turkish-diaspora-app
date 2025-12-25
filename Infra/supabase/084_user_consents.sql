-- 084_user_consents.sql
-- User Consent Flags System
-- Database schema for consent tracking (service vs marketing emails)
-- Part of claim-consent-outreach-implementation-plan (Fase 10.2)

-- 1. Create user_consents table
CREATE TABLE IF NOT EXISTS public.user_consents (
    email TEXT PRIMARY KEY, -- Email address (PRIMARY KEY for uniqueness)
    service_consent BOOLEAN NOT NULL DEFAULT true, -- Service emails (outreach, confirmations) - implicit consent
    marketing_consent BOOLEAN NOT NULL DEFAULT false, -- Marketing emails - explicit opt-in required
    opted_out_at TIMESTAMPTZ, -- When user opted out (both consents set to false)
    opt_out_reason TEXT, -- Optional reason for opt-out
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_consents_service_consent ON public.user_consents(service_consent) WHERE service_consent = true;
CREATE INDEX IF NOT EXISTS idx_user_consents_marketing_consent ON public.user_consents(marketing_consent) WHERE marketing_consent = true;
CREATE INDEX IF NOT EXISTS idx_user_consents_opted_out_at ON public.user_consents(opted_out_at) WHERE opted_out_at IS NOT NULL;

-- 3. Add table and column comments for documentation
COMMENT ON TABLE public.user_consents IS 'Consent tracking for email communications. Tracks service consent (implicit for outreach) and marketing consent (explicit opt-in).';
COMMENT ON COLUMN public.user_consents.email IS 'Email address (PRIMARY KEY). Can be for authenticated or non-authenticated users.';
COMMENT ON COLUMN public.user_consents.service_consent IS 'Service email consent (outreach, confirmations, transactional). Default true (implicit consent for outreach).';
COMMENT ON COLUMN public.user_consents.marketing_consent IS 'Marketing email consent. Default false (requires explicit opt-in).';
COMMENT ON COLUMN public.user_consents.opted_out_at IS 'Timestamp when user opted out (both consents set to false).';
COMMENT ON COLUMN public.user_consents.opt_out_reason IS 'Optional reason for opt-out.';

-- 4. Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_consents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_consents_updated_at
    BEFORE UPDATE ON public.user_consents
    FOR EACH ROW
    EXECUTE FUNCTION update_user_consents_updated_at();

