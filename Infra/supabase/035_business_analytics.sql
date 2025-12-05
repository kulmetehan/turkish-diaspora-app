-- 035_business_analytics.sql
-- Business analytics infrastructure (EPIC-3)

-- Optional caching table for business analytics (performance optimization)
CREATE TABLE IF NOT EXISTS public.business_analytics (
    id BIGSERIAL PRIMARY KEY,
    business_account_id BIGINT NOT NULL REFERENCES public.business_accounts(id) ON DELETE CASCADE,
    location_id BIGINT REFERENCES public.locations(id) ON DELETE SET NULL,
    metric_type TEXT NOT NULL, -- 'views', 'check_ins', 'reactions', 'notes', 'favorites', 'trending_score'
    metric_value NUMERIC NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(business_account_id, location_id, metric_type, period_start, period_end)
);

CREATE INDEX IF NOT EXISTS idx_business_analytics_account ON public.business_analytics(business_account_id, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_business_analytics_location ON public.business_analytics(location_id, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_business_analytics_type ON public.business_analytics(metric_type, period_start DESC);

-- View for business overview metrics (real-time)
CREATE OR REPLACE VIEW public.business_analytics_overview AS
SELECT 
    ba.id AS business_account_id,
    COUNT(DISTINCT blc.location_id) AS total_locations,
    COUNT(DISTINCT CASE WHEN blc.status = 'approved' THEN blc.location_id END) AS approved_locations,
    SUM(CASE WHEN a.metric_type = 'views' THEN a.metric_value ELSE 0 END) AS total_views,
    SUM(CASE WHEN a.metric_type = 'check_ins' THEN a.metric_value ELSE 0 END) AS total_check_ins,
    SUM(CASE WHEN a.metric_type = 'reactions' THEN a.metric_value ELSE 0 END) AS total_reactions,
    SUM(CASE WHEN a.metric_type = 'notes' THEN a.metric_value ELSE 0 END) AS total_notes,
    SUM(CASE WHEN a.metric_type = 'favorites' THEN a.metric_value ELSE 0 END) AS total_favorites
FROM public.business_accounts ba
LEFT JOIN public.business_location_claims blc ON blc.business_account_id = ba.id
LEFT JOIN public.business_analytics a ON a.business_account_id = ba.id
GROUP BY ba.id;

COMMENT ON TABLE public.business_analytics IS 'Cached business analytics metrics for performance';
COMMENT ON VIEW public.business_analytics_overview IS 'Real-time overview metrics for business accounts';

