-- 040_promoted_news.sql
-- Promoted news posts for feed promotion (EPIC-3)

CREATE TABLE IF NOT EXISTS public.promoted_news (
    id BIGSERIAL PRIMARY KEY,
    business_account_id BIGINT NOT NULL REFERENCES public.business_accounts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT, -- Optional link to external article
    image_url TEXT, -- Optional image URL
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    stripe_payment_intent_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'expired', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_promoted_news_business_account ON public.promoted_news(business_account_id);
CREATE INDEX IF NOT EXISTS idx_promoted_news_dates_status ON public.promoted_news(starts_at, ends_at, status);
CREATE INDEX IF NOT EXISTS idx_promoted_news_active ON public.promoted_news(status, starts_at, ends_at) WHERE status = 'active';

COMMENT ON TABLE public.promoted_news IS 'Promoted news posts created by businesses';
COMMENT ON COLUMN public.promoted_news.status IS 'Promotion status: pending (payment pending), active (live), expired (ended), cancelled';





