-- 026_activity_stream.sql
-- Denormalized activity stream for fast feed queries

CREATE TABLE IF NOT EXISTS public.activity_stream (
    id BIGSERIAL PRIMARY KEY,
    actor_type TEXT NOT NULL, -- 'user', 'client', 'business'
    actor_id UUID, -- user_id or NULL for client_id
    client_id UUID, -- Always present for traceability
    activity_type TEXT NOT NULL, -- 'check_in', 'reaction', 'note', 'poll_response', 'favorite'
    location_id BIGINT REFERENCES public.locations(id) ON DELETE SET NULL,
    city_key TEXT, -- Denormalized from location for fast filtering
    category_key TEXT, -- Denormalized from location
    payload JSONB, -- Lightweight details (reaction_type, note_preview, etc.)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT activity_stream_actor_check CHECK (
        (actor_type = 'user' AND actor_id IS NOT NULL) OR
        (actor_type = 'client' AND client_id IS NOT NULL) OR
        (actor_type = 'business' AND actor_id IS NOT NULL)
    ),
    CONSTRAINT activity_stream_type_check CHECK (
        activity_type IN ('check_in', 'reaction', 'note', 'poll_response', 'favorite')
    )
);

CREATE INDEX IF NOT EXISTS idx_activity_stream_actor ON public.activity_stream(actor_id, created_at DESC) WHERE actor_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_activity_stream_client ON public.activity_stream(client_id, created_at DESC) WHERE client_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_activity_stream_location ON public.activity_stream(location_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_stream_city ON public.activity_stream(city_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_stream_category ON public.activity_stream(category_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_stream_type ON public.activity_stream(activity_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_stream_created_at ON public.activity_stream(created_at DESC);

-- Composite index for nearby activity queries
CREATE INDEX IF NOT EXISTS idx_activity_stream_city_category ON public.activity_stream(city_key, category_key, created_at DESC);

COMMENT ON TABLE public.activity_stream IS 'Denormalized activity feed for fast queries (eventually consistent)';
COMMENT ON COLUMN public.activity_stream.payload IS 'JSONB with activity-specific details (reaction_type, note_preview, poll_id, etc.)';











