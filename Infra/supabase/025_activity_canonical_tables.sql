-- 025_activity_canonical_tables.sql
-- Canonical activity tables (source of truth)

-- Check-ins
CREATE TABLE IF NOT EXISTS public.check_ins (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    client_id UUID, -- For anonymous users
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_in_activity_stream BOOLEAN DEFAULT false,
    CONSTRAINT check_ins_identity_check CHECK (
        (user_id IS NOT NULL) OR (client_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_check_ins_location_id ON public.check_ins(location_id);
CREATE INDEX IF NOT EXISTS idx_check_ins_user_id ON public.check_ins(user_id);
CREATE INDEX IF NOT EXISTS idx_check_ins_client_id ON public.check_ins(client_id);
CREATE INDEX IF NOT EXISTS idx_check_ins_created_at ON public.check_ins(created_at);
CREATE INDEX IF NOT EXISTS idx_check_ins_processed ON public.check_ins(processed_in_activity_stream) WHERE processed_in_activity_stream = false;
CREATE UNIQUE INDEX IF NOT EXISTS idx_check_ins_unique_per_day ON public.check_ins(location_id, COALESCE(user_id::text, client_id::text), DATE(created_at));

-- Location reactions (emoji reactions)
CREATE TABLE IF NOT EXISTS public.location_reactions (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    client_id UUID,
    reaction_type TEXT NOT NULL, -- 'fire', 'heart', 'thumbs_up', 'smile', etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_in_activity_stream BOOLEAN DEFAULT false,
    CONSTRAINT location_reactions_identity_check CHECK (
        (user_id IS NOT NULL) OR (client_id IS NOT NULL)
    ),
    CONSTRAINT location_reactions_type_check CHECK (
        reaction_type IN ('fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag')
    )
);

CREATE INDEX IF NOT EXISTS idx_location_reactions_location_id ON public.location_reactions(location_id);
CREATE INDEX IF NOT EXISTS idx_location_reactions_user_id ON public.location_reactions(user_id);
CREATE INDEX IF NOT EXISTS idx_location_reactions_client_id ON public.location_reactions(client_id);
CREATE INDEX IF NOT EXISTS idx_location_reactions_created_at ON public.location_reactions(created_at);
CREATE INDEX IF NOT EXISTS idx_location_reactions_processed ON public.location_reactions(processed_in_activity_stream) WHERE processed_in_activity_stream = false;
CREATE UNIQUE INDEX IF NOT EXISTS idx_location_reactions_unique ON public.location_reactions(location_id, COALESCE(user_id::text, client_id::text), reaction_type);

-- Location notes (user-generated content)
CREATE TABLE IF NOT EXISTS public.location_notes (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    client_id UUID,
    content TEXT NOT NULL,
    is_edited BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_in_activity_stream BOOLEAN DEFAULT false,
    CONSTRAINT location_notes_identity_check CHECK (
        (user_id IS NOT NULL) OR (client_id IS NOT NULL)
    ),
    CONSTRAINT location_notes_content_length CHECK (
        LENGTH(content) >= 3 AND LENGTH(content) <= 1000
    )
);

CREATE INDEX IF NOT EXISTS idx_location_notes_location_id ON public.location_notes(location_id);
CREATE INDEX IF NOT EXISTS idx_location_notes_user_id ON public.location_notes(user_id);
CREATE INDEX IF NOT EXISTS idx_location_notes_client_id ON public.location_notes(client_id);
CREATE INDEX IF NOT EXISTS idx_location_notes_created_at ON public.location_notes(created_at);
CREATE INDEX IF NOT EXISTS idx_location_notes_processed ON public.location_notes(processed_in_activity_stream) WHERE processed_in_activity_stream = false;

-- Favorites
CREATE TABLE IF NOT EXISTS public.favorites (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.locations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    client_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_in_activity_stream BOOLEAN DEFAULT false,
    CONSTRAINT favorites_identity_check CHECK (
        (user_id IS NOT NULL) OR (client_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_favorites_location_id ON public.favorites(location_id);
CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON public.favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_client_id ON public.favorites(client_id);
CREATE INDEX IF NOT EXISTS idx_favorites_processed ON public.favorites(processed_in_activity_stream) WHERE processed_in_activity_stream = false;
CREATE UNIQUE INDEX IF NOT EXISTS idx_favorites_unique ON public.favorites(location_id, COALESCE(user_id::text, client_id::text));

COMMENT ON TABLE public.check_ins IS 'Canonical check-in records (source of truth)';
COMMENT ON TABLE public.location_reactions IS 'Canonical emoji reaction records';
COMMENT ON TABLE public.location_notes IS 'Canonical user-generated notes';
COMMENT ON TABLE public.favorites IS 'Canonical favorite/bookmark records';
COMMENT ON COLUMN public.check_ins.processed_in_activity_stream IS 'Flag for activity_stream worker processing';





