-- 029_rate_limiting.sql
-- Rate limiting storage

CREATE TABLE IF NOT EXISTS public.rate_limits (
    id BIGSERIAL PRIMARY KEY,
    key_type TEXT NOT NULL, -- 'client_id', 'user_id', 'ip'
    key_value TEXT NOT NULL,
    action TEXT NOT NULL, -- 'check_in', 'reaction', 'note', 'poll_response', 'account_creation'
    window_start TIMESTAMPTZ NOT NULL,
    count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(key_type, key_value, action, window_start)
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_key ON public.rate_limits(key_type, key_value, action, window_start DESC);
-- Removed partial index with now() - use regular index instead
-- Cleanup job will handle old records removal
CREATE INDEX IF NOT EXISTS idx_rate_limits_window ON public.rate_limits(window_start);

COMMENT ON TABLE public.rate_limits IS 'Rate limiting counters with sliding window (cleanup after 24h)';





