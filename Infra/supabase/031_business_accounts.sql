-- 031_business_accounts.sql
-- Business accounts and location claiming (Fase 3)

CREATE TYPE claim_status AS ENUM ('pending', 'approved', 'rejected', 'revoked');
CREATE TYPE subscription_tier AS ENUM ('basic', 'premium', 'pro');

CREATE TABLE IF NOT EXISTS public.business_accounts (
    id BIGSERIAL PRIMARY KEY,
    owner_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    vat_kvk TEXT,
    country TEXT DEFAULT 'NL',
    website TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    subscription_tier subscription_tier DEFAULT 'basic',
    subscription_status TEXT DEFAULT 'active', -- 'active', 'cancelled', 'expired'
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_business_accounts_owner ON public.business_accounts(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_business_accounts_stripe ON public.business_accounts(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.business_members (
    id BIGSERIAL PRIMARY KEY,
    business_account_id BIGINT NOT NULL REFERENCES public.business_accounts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'editor', -- 'owner', 'admin', 'editor'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(business_account_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_business_members_user_id ON public.business_members(user_id);

CREATE TABLE IF NOT EXISTS public.business_location_claims (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    business_account_id BIGINT NOT NULL REFERENCES public.business_accounts(id) ON DELETE CASCADE,
    status claim_status NOT NULL DEFAULT 'pending',
    verification_notes TEXT,
    verified_by UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- Admin who approved
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(location_id) -- One claim per location
);

CREATE INDEX IF NOT EXISTS idx_business_claims_location ON public.business_location_claims(location_id);
CREATE INDEX IF NOT EXISTS idx_business_claims_account ON public.business_location_claims(business_account_id);
CREATE INDEX IF NOT EXISTS idx_business_claims_status ON public.business_location_claims(status);

CREATE TABLE IF NOT EXISTS public.business_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    business_account_id BIGINT NOT NULL REFERENCES public.business_accounts(id) ON DELETE CASCADE,
    stripe_subscription_id TEXT NOT NULL UNIQUE,
    tier subscription_tier NOT NULL,
    status TEXT NOT NULL, -- 'active', 'cancelled', 'past_due', 'expired'
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_business_subscriptions_account ON public.business_subscriptions(business_account_id);
CREATE INDEX IF NOT EXISTS idx_business_subscriptions_stripe ON public.business_subscriptions(stripe_subscription_id);

COMMENT ON TABLE public.business_accounts IS 'Business accounts for location owners';
COMMENT ON TABLE public.business_members IS 'Team members with access to business account';
COMMENT ON TABLE public.business_location_claims IS 'Location claiming requests and approvals';
COMMENT ON TABLE public.business_subscriptions IS 'Subscription history and current status';




















