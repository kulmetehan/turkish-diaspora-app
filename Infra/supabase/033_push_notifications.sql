-- 033_push_notifications.sql
-- Push notifications infrastructure (EPIC-1.5)

CREATE TABLE IF NOT EXISTS public.device_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token TEXT NOT NULL, -- Web Push subscription token (JSON)
    platform TEXT NOT NULL DEFAULT 'web', -- 'web', 'ios', 'android'
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT true,
    UNIQUE(user_id, token) -- One subscription per user per device
);

CREATE INDEX IF NOT EXISTS idx_device_tokens_user_id ON public.device_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_device_tokens_active ON public.device_tokens(is_active) WHERE is_active = true;

CREATE TABLE IF NOT EXISTS public.push_notification_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT true,
    poll_notifications BOOLEAN NOT NULL DEFAULT true,
    trending_notifications BOOLEAN NOT NULL DEFAULT false,
    activity_notifications BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.push_notification_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    device_token_id BIGINT REFERENCES public.device_tokens(id) ON DELETE SET NULL,
    notification_type TEXT NOT NULL, -- 'poll', 'trending', 'activity', 'system'
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    data JSONB,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered BOOLEAN,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_push_notification_log_user_id ON public.push_notification_log(user_id);
CREATE INDEX IF NOT EXISTS idx_push_notification_log_sent_at ON public.push_notification_log(sent_at);

COMMENT ON TABLE public.device_tokens IS 'Stores Web Push subscription tokens for push notifications';
COMMENT ON TABLE public.push_notification_preferences IS 'User preferences for push notification types';
COMMENT ON TABLE public.push_notification_log IS 'Audit log for all push notifications sent';



















