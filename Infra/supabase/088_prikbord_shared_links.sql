-- 088_prikbord_shared_links.sql
-- Prikbord: Shared links with automatic preview generation

-- Main shared links table
CREATE TABLE IF NOT EXISTS public.shared_links (
    id BIGSERIAL PRIMARY KEY,
    
    -- Core link data
    url TEXT NOT NULL UNIQUE, -- Normalized URL (lowercase, no trailing slash)
    platform TEXT NOT NULL CHECK (platform IN (
        'marktplaats',
        'instagram',
        'facebook',
        'youtube',
        'twitter',
        'tiktok',
        'news',
        'event',
        'other'
    )),
    
    -- Preview metadata (from oEmbed/Open Graph)
    title TEXT,
    description TEXT,
    image_url TEXT,
    video_url TEXT, -- For YouTube, TikTok, etc.
    
    -- Preview generation metadata
    preview_method TEXT CHECK (preview_method IN ('oembed', 'opengraph', 'fallback')),
    preview_fetched_at TIMESTAMPTZ,
    preview_cache_expires_at TIMESTAMPTZ, -- Refresh preview after X days
    
    -- Creator
    created_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_by_business_id BIGINT REFERENCES public.business_accounts(id) ON DELETE SET NULL,
    creator_type TEXT NOT NULL CHECK (creator_type IN ('user', 'business')),
    
    -- Location context (optional)
    linked_location_id BIGINT REFERENCES public.locations(id) ON DELETE SET NULL,
    city TEXT, -- Denormalized for filtering
    neighborhood TEXT,
    
    -- Context tags (emoji-based)
    context_tags TEXT[] DEFAULT '{}', -- ['🏠', '🛍️', '🎉', '📺']
    
    -- Analytics
    view_count INTEGER NOT NULL DEFAULT 0,
    like_count INTEGER NOT NULL DEFAULT 0,
    bookmark_count INTEGER NOT NULL DEFAULT 0,
    
    -- Lifecycle
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'removed', 'broken_link')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraints
    CONSTRAINT check_creator CHECK (
        (creator_type = 'user' AND created_by_user_id IS NOT NULL AND created_by_business_id IS NULL) OR
        (creator_type = 'business' AND created_by_business_id IS NOT NULL AND created_by_user_id IS NULL)
    )
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_shared_links_url ON public.shared_links(url);
CREATE INDEX IF NOT EXISTS idx_shared_links_platform ON public.shared_links(platform, status);
CREATE INDEX IF NOT EXISTS idx_shared_links_city ON public.shared_links(city, status) WHERE city IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_shared_links_created_by_user ON public.shared_links(created_by_user_id, created_at DESC) WHERE created_by_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_shared_links_created_by_business ON public.shared_links(created_by_business_id, created_at DESC) WHERE created_by_business_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_shared_links_linked_location ON public.shared_links(linked_location_id) WHERE linked_location_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_shared_links_created_at ON public.shared_links(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_shared_links_status ON public.shared_links(status, created_at DESC) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_shared_links_preview_expires ON public.shared_links(preview_cache_expires_at) WHERE preview_cache_expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_shared_links_context_tags ON public.shared_links USING GIN(context_tags) WHERE array_length(context_tags, 1) > 0;

-- Interactions table
CREATE TABLE IF NOT EXISTS public.shared_link_interactions (
    id BIGSERIAL PRIMARY KEY,
    link_id BIGINT NOT NULL REFERENCES public.shared_links(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    client_id TEXT, -- For anonymous users
    interaction_type TEXT NOT NULL CHECK (interaction_type IN ('view', 'like', 'bookmark')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT check_identity CHECK (
        (user_id IS NOT NULL) OR (client_id IS NOT NULL AND client_id != '')
    )
);

-- Unique constraints for like/bookmark (one per user/client per link)
CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_link_interactions_unique_like_user 
    ON public.shared_link_interactions(link_id, user_id, interaction_type) 
    WHERE interaction_type = 'like' AND user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_link_interactions_unique_like_client 
    ON public.shared_link_interactions(link_id, client_id, interaction_type) 
    WHERE interaction_type = 'like' AND client_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_link_interactions_unique_bookmark_user 
    ON public.shared_link_interactions(link_id, user_id, interaction_type) 
    WHERE interaction_type = 'bookmark' AND user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_link_interactions_unique_bookmark_client 
    ON public.shared_link_interactions(link_id, client_id, interaction_type) 
    WHERE interaction_type = 'bookmark' AND client_id IS NOT NULL;

-- Other indexes
CREATE INDEX IF NOT EXISTS idx_shared_link_interactions_link ON public.shared_link_interactions(link_id, interaction_type);
CREATE INDEX IF NOT EXISTS idx_shared_link_interactions_user ON public.shared_link_interactions(user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_shared_link_interactions_client ON public.shared_link_interactions(client_id, created_at DESC) WHERE client_id IS NOT NULL;

-- Function to update counts when interaction is logged
CREATE OR REPLACE FUNCTION update_shared_link_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.interaction_type = 'view' THEN
        UPDATE public.shared_links
        SET view_count = view_count + 1
        WHERE id = NEW.link_id;
    ELSIF NEW.interaction_type = 'like' THEN
        UPDATE public.shared_links
        SET like_count = like_count + 1
        WHERE id = NEW.link_id;
    ELSIF NEW.interaction_type = 'bookmark' THEN
        UPDATE public.shared_links
        SET bookmark_count = bookmark_count + 1
        WHERE id = NEW.link_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_shared_link_counts_trigger
    AFTER INSERT ON public.shared_link_interactions
    FOR EACH ROW
    EXECUTE FUNCTION update_shared_link_counts();

-- Function to decrement counts on delete (for likes/bookmarks)
CREATE OR REPLACE FUNCTION decrement_shared_link_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.interaction_type = 'like' THEN
        UPDATE public.shared_links
        SET like_count = GREATEST(like_count - 1, 0)
        WHERE id = OLD.link_id;
    ELSIF OLD.interaction_type = 'bookmark' THEN
        UPDATE public.shared_links
        SET bookmark_count = GREATEST(bookmark_count - 1, 0)
        WHERE id = OLD.link_id;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER decrement_shared_link_counts_trigger
    AFTER DELETE ON public.shared_link_interactions
    FOR EACH ROW
    WHEN (OLD.interaction_type IN ('like', 'bookmark'))
    EXECUTE FUNCTION decrement_shared_link_counts();

COMMENT ON TABLE public.shared_links IS 'Prikbord: Shared external links with automatic preview generation';
COMMENT ON TABLE public.shared_link_interactions IS 'User interactions with shared links (views, likes, bookmarks)';
COMMENT ON COLUMN public.shared_links.preview_method IS 'Method used to generate preview: oembed, opengraph, or fallback';
COMMENT ON COLUMN public.shared_links.preview_cache_expires_at IS 'When to refresh the preview (default 7 days)';
COMMENT ON COLUMN public.shared_links.context_tags IS 'Context tags for categorization (emoji-based: 🏠 Wonen, 🛍️ Ondernemer, 🎉 Event, 📺 Media)';




