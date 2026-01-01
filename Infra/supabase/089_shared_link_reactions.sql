-- Migration 089: Shared Link Reactions
-- Create shared_link_reactions table for emoji reactions on shared links

CREATE TABLE IF NOT EXISTS public.shared_link_reactions (
    id bigserial PRIMARY KEY,
    link_id bigint NOT NULL REFERENCES public.shared_links(id) ON DELETE CASCADE,
    reaction_type text NOT NULL, -- Emoji string (e.g., "👍", "❤️", "🔥")
    client_id text,
    user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    identity_key text GENERATED ALWAYS AS (COALESCE(user_id::text, client_id)) STORED,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(link_id, identity_key, reaction_type),
    CONSTRAINT check_identity CHECK (
        (user_id IS NOT NULL) OR (client_id IS NOT NULL AND client_id != '')
    )
);

CREATE INDEX IF NOT EXISTS idx_shared_link_reactions_link_id ON public.shared_link_reactions(link_id);
CREATE INDEX IF NOT EXISTS idx_shared_link_reactions_identity ON public.shared_link_reactions(identity_key);
CREATE INDEX IF NOT EXISTS idx_shared_link_reactions_type ON public.shared_link_reactions(reaction_type);

COMMENT ON TABLE public.shared_link_reactions IS 'Emoji reactions on shared links';
COMMENT ON COLUMN public.shared_link_reactions.reaction_type IS 'Emoji reaction string (e.g., "👍", "❤️", "🔥")';
COMMENT ON COLUMN public.shared_link_reactions.identity_key IS 'Generated column: user_id if available, otherwise client_id';



