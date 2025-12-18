-- 039_promoted_locations.sql
-- Promoted locations for trending and feed promotion (EPIC-3)

CREATE TABLE IF NOT EXISTS public.promoted_locations (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    business_account_id BIGINT NOT NULL REFERENCES public.business_accounts(id) ON DELETE CASCADE,
    promotion_type TEXT NOT NULL CHECK (promotion_type IN ('trending', 'feed', 'both')),
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    stripe_payment_intent_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'expired', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_promoted_locations_location_status ON public.promoted_locations(location_id, status);
CREATE INDEX IF NOT EXISTS idx_promoted_locations_business_account ON public.promoted_locations(business_account_id);
CREATE INDEX IF NOT EXISTS idx_promoted_locations_dates ON public.promoted_locations(starts_at, ends_at);
CREATE INDEX IF NOT EXISTS idx_promoted_locations_active ON public.promoted_locations(status, starts_at, ends_at) WHERE status = 'active';

COMMENT ON TABLE public.promoted_locations IS 'Promoted locations for trending and feed promotion';
COMMENT ON COLUMN public.promoted_locations.promotion_type IS 'Type of promotion: trending, feed, or both';
COMMENT ON COLUMN public.promoted_locations.status IS 'Promotion status: pending (payment pending), active (live), expired (ended), cancelled';

-- Promotion payments audit trail (shared by locations and news)
CREATE TABLE IF NOT EXISTS public.promotion_payments (
    id BIGSERIAL PRIMARY KEY,
    promotion_type TEXT NOT NULL CHECK (promotion_type IN ('location', 'news')),
    promotion_id BIGINT NOT NULL,
    business_account_id BIGINT NOT NULL REFERENCES public.business_accounts(id) ON DELETE CASCADE,
    stripe_payment_intent_id TEXT UNIQUE NOT NULL,
    amount INTEGER NOT NULL, -- Amount in cents
    currency TEXT NOT NULL DEFAULT 'eur',
    status TEXT NOT NULL CHECK (status IN ('pending', 'succeeded', 'failed', 'refunded')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_promotion_payments_business_account ON public.promotion_payments(business_account_id);
CREATE INDEX IF NOT EXISTS idx_promotion_payments_stripe ON public.promotion_payments(stripe_payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_promotion_payments_promotion ON public.promotion_payments(promotion_type, promotion_id);
CREATE INDEX IF NOT EXISTS idx_promotion_payments_status ON public.promotion_payments(status);

COMMENT ON TABLE public.promotion_payments IS 'Audit trail for promotion payments (locations and news)';
COMMENT ON COLUMN public.promotion_payments.promotion_type IS 'Type of promotion: location or news';
COMMENT ON COLUMN public.promotion_payments.promotion_id IS 'References promoted_locations.id or promoted_news.id depending on promotion_type';



















