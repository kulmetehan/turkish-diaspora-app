-- 036_premium_features.sql
-- Premium features infrastructure (EPIC-3)

-- Premium features table for feature flags per account
CREATE TABLE IF NOT EXISTS public.premium_features (
    id BIGSERIAL PRIMARY KEY,
    business_account_id BIGINT NOT NULL REFERENCES public.business_accounts(id) ON DELETE CASCADE,
    feature_key TEXT NOT NULL, -- 'enhanced_location_info', 'advanced_analytics', 'priority_support', etc.
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    enabled_at TIMESTAMPTZ,
    disabled_at TIMESTAMPTZ,
    metadata JSONB, -- Additional feature-specific data
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(business_account_id, feature_key)
);

CREATE INDEX IF NOT EXISTS idx_premium_features_account ON public.premium_features(business_account_id);
CREATE INDEX IF NOT EXISTS idx_premium_features_key ON public.premium_features(feature_key);
CREATE INDEX IF NOT EXISTS idx_premium_features_enabled ON public.premium_features(business_account_id, is_enabled) WHERE is_enabled = true;

-- Payment transactions audit trail
CREATE TABLE IF NOT EXISTS public.payment_transactions (
    id BIGSERIAL PRIMARY KEY,
    business_account_id BIGINT NOT NULL REFERENCES public.business_accounts(id) ON DELETE CASCADE,
    stripe_payment_intent_id TEXT UNIQUE,
    stripe_subscription_id TEXT,
    transaction_type TEXT NOT NULL, -- 'subscription', 'one_time', 'refund'
    amount NUMERIC NOT NULL, -- Amount in cents
    currency TEXT NOT NULL DEFAULT 'eur',
    status TEXT NOT NULL, -- 'pending', 'succeeded', 'failed', 'refunded'
    description TEXT,
    metadata JSONB, -- Additional transaction data
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_account ON public.payment_transactions(business_account_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_stripe_pi ON public.payment_transactions(stripe_payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_stripe_sub ON public.payment_transactions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_status ON public.payment_transactions(status);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_created_at ON public.payment_transactions(created_at DESC);

-- Function to sync premium features based on subscription tier
CREATE OR REPLACE FUNCTION sync_premium_features()
RETURNS TRIGGER AS $$
BEGIN
    -- Enable/disable features based on subscription tier
    IF NEW.subscription_tier = 'premium' THEN
        INSERT INTO public.premium_features (business_account_id, feature_key, is_enabled, enabled_at)
        VALUES 
            (NEW.id, 'enhanced_location_info', true, now()),
            (NEW.id, 'advanced_analytics', true, now()),
            (NEW.id, 'priority_support', true, now())
        ON CONFLICT (business_account_id, feature_key) 
        DO UPDATE SET is_enabled = true, enabled_at = now(), updated_at = now();
    ELSIF NEW.subscription_tier = 'pro' THEN
        INSERT INTO public.premium_features (business_account_id, feature_key, is_enabled, enabled_at)
        VALUES 
            (NEW.id, 'enhanced_location_info', true, now()),
            (NEW.id, 'advanced_analytics', true, now()),
            (NEW.id, 'priority_support', true, now()),
            (NEW.id, 'api_access', true, now()),
            (NEW.id, 'custom_branding', true, now())
        ON CONFLICT (business_account_id, feature_key) 
        DO UPDATE SET is_enabled = true, enabled_at = now(), updated_at = now();
    ELSE
        -- Basic tier: disable all premium features
        UPDATE public.premium_features
        SET is_enabled = false, disabled_at = now(), updated_at = now()
        WHERE business_account_id = NEW.id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to sync features when subscription tier changes
CREATE TRIGGER sync_premium_features_trigger
    AFTER INSERT OR UPDATE OF subscription_tier ON public.business_accounts
    FOR EACH ROW
    EXECUTE FUNCTION sync_premium_features();

COMMENT ON TABLE public.premium_features IS 'Feature flags for premium features per business account';
COMMENT ON TABLE public.payment_transactions IS 'Audit trail for all payment transactions';
COMMENT ON FUNCTION sync_premium_features() IS 'Automatically syncs premium features based on subscription tier';


















