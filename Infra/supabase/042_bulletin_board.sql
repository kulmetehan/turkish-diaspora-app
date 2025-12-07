-- 042_bulletin_board.sql
-- Bulletin board (advertentiebord) feature with AI moderation

-- Main bulletin posts table
CREATE TABLE IF NOT EXISTS public.bulletin_posts (
    id BIGSERIAL PRIMARY KEY,
    
    -- Creator identity (either user OR business, not both)
    created_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_by_business_id BIGINT REFERENCES public.business_accounts(id) ON DELETE SET NULL,
    creator_type TEXT NOT NULL CHECK (creator_type IN ('user', 'business')),
    
    -- Core content
    title TEXT NOT NULL CHECK (LENGTH(title) >= 3 AND LENGTH(title) <= 100),
    description TEXT CHECK (description IS NULL OR LENGTH(description) <= 2000),
    category TEXT NOT NULL CHECK (category IN (
        'personnel_wanted',
        'offer',
        'free_for_sale',
        'event',
        'services',
        'other'
    )),
    
    -- Location context (optional - link to location or just city)
    linked_location_id BIGINT REFERENCES public.locations(id) ON DELETE SET NULL,
    city TEXT, -- Denormalized for filtering
    neighborhood TEXT,
    
    -- Contact info (optional - users can choose to show or use messaging)
    contact_phone TEXT,
    contact_email TEXT,
    contact_whatsapp TEXT,
    show_contact_info BOOLEAN NOT NULL DEFAULT true,
    
    -- Media
    image_urls TEXT[] DEFAULT '{}', -- Array of image URLs (stored in Supabase Storage)
    
    -- Lifecycle
    expires_at TIMESTAMPTZ, -- When this post should expire
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',      -- Awaiting moderation
        'active',       -- Live and visible
        'expired',      -- Past expiry date
        'removed',      -- Manually removed
        'reported'      -- Flagged for review
    )),
    
    -- Moderation
    moderation_status TEXT NOT NULL DEFAULT 'pending' CHECK (moderation_status IN (
        'pending',          -- Awaiting AI moderation
        'approved',         -- AI approved
        'rejected',         -- AI rejected
        'requires_review',  -- Needs manual review
        'reported'          -- Community reported
    )),
    moderation_result JSONB, -- Stores ContentModerationResult from AI
    moderated_at TIMESTAMPTZ,
    moderation_ai_log_id BIGINT REFERENCES public.ai_logs(id) ON DELETE SET NULL,
    
    -- Analytics
    view_count INTEGER NOT NULL DEFAULT 0,
    contact_count INTEGER NOT NULL DEFAULT 0, -- Tracked when users click contact
    
    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ, -- When status changed to 'active'
    removed_at TIMESTAMPTZ,
    removed_reason TEXT,
    
    -- Constraints
    CONSTRAINT check_creator CHECK (
        (creator_type = 'user' AND created_by_user_id IS NOT NULL AND created_by_business_id IS NULL) OR
        (creator_type = 'business' AND created_by_business_id IS NOT NULL AND created_by_user_id IS NULL)
    ),
    CONSTRAINT check_moderation_before_active CHECK (
        (status = 'active' AND moderation_status = 'approved') OR
        (status != 'active')
    )
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bulletin_posts_status ON public.bulletin_posts(status, expires_at) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_bulletin_posts_moderation_status ON public.bulletin_posts(moderation_status, created_at DESC) WHERE moderation_status IN ('pending', 'requires_review');
CREATE INDEX IF NOT EXISTS idx_bulletin_posts_category ON public.bulletin_posts(category, status);
CREATE INDEX IF NOT EXISTS idx_bulletin_posts_city ON public.bulletin_posts(city, status) WHERE city IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_bulletin_posts_created_by_user ON public.bulletin_posts(created_by_user_id, created_at DESC) WHERE created_by_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_bulletin_posts_created_by_business ON public.bulletin_posts(created_by_business_id, created_at DESC) WHERE created_by_business_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_bulletin_posts_linked_location ON public.bulletin_posts(linked_location_id) WHERE linked_location_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_bulletin_posts_created_at ON public.bulletin_posts(created_at DESC);

-- Track user interactions (views, saves, reports)
CREATE TABLE IF NOT EXISTS public.bulletin_post_interactions (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES public.bulletin_posts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    client_id TEXT, -- For anonymous users
    interaction_type TEXT NOT NULL CHECK (interaction_type IN ('view', 'save', 'report', 'contact_click')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT check_identity CHECK (
        (user_id IS NOT NULL) OR (client_id IS NOT NULL AND client_id != '')
    )
);

CREATE INDEX IF NOT EXISTS idx_bulletin_interactions_post ON public.bulletin_post_interactions(post_id, interaction_type);
CREATE INDEX IF NOT EXISTS idx_bulletin_interactions_user ON public.bulletin_post_interactions(user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_bulletin_interactions_client ON public.bulletin_post_interactions(client_id, created_at DESC) WHERE client_id IS NOT NULL;

-- Reporting for moderation (separate from main reports table for bulletin-specific reports)
CREATE TABLE IF NOT EXISTS public.bulletin_post_reports (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES public.bulletin_posts(id) ON DELETE CASCADE,
    reported_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    reported_by_client_id TEXT,
    reason TEXT NOT NULL,
    details TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'dismissed', 'action_taken')),
    reviewed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT check_reporter CHECK (
        (reported_by_user_id IS NOT NULL) OR (reported_by_client_id IS NOT NULL AND reported_by_client_id != '')
    )
);

CREATE INDEX IF NOT EXISTS idx_bulletin_reports_post ON public.bulletin_post_reports(post_id, status);
CREATE INDEX IF NOT EXISTS idx_bulletin_reports_status ON public.bulletin_post_reports(status, created_at DESC) WHERE status = 'pending';

-- Automatic expiration trigger function
CREATE OR REPLACE FUNCTION expire_bulletin_posts()
RETURNS void AS $$
BEGIN
    UPDATE public.bulletin_posts
    SET status = 'expired', updated_at = now()
    WHERE status = 'active'
      AND expires_at IS NOT NULL
      AND expires_at < now();
END;
$$ LANGUAGE plpgsql;

-- Function to get creator profile info (for display)
CREATE OR REPLACE FUNCTION get_bulletin_post_creator(post public.bulletin_posts)
RETURNS JSONB AS $$
DECLARE
    creator_info JSONB;
BEGIN
    IF post.creator_type = 'business' THEN
        SELECT jsonb_build_object(
            'type', 'business',
            'id', ba.id,
            'name', ba.company_name,
            'verified', EXISTS(
                SELECT 1 FROM public.business_location_claims blc
                WHERE blc.business_account_id = ba.id
                AND blc.status = 'approved'
                LIMIT 1
            )
        ) INTO creator_info
        FROM public.business_accounts ba
        WHERE ba.id = post.created_by_business_id;
    ELSE
        SELECT jsonb_build_object(
            'type', 'user',
            'id', up.id,
            'name', COALESCE(up.display_name, split_part(au.email, '@', 1))
        ) INTO creator_info
        FROM public.user_profiles up
        INNER JOIN auth.users au ON au.id = up.id
        WHERE up.id = post.created_by_user_id;
    END IF;
    
    RETURN COALESCE(creator_info, jsonb_build_object('type', 'unknown'));
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to update view_count when interaction is logged
CREATE OR REPLACE FUNCTION update_bulletin_post_view_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.interaction_type = 'view' THEN
        UPDATE public.bulletin_posts
        SET view_count = view_count + 1
        WHERE id = NEW.post_id;
    ELSIF NEW.interaction_type = 'contact_click' THEN
        UPDATE public.bulletin_posts
        SET contact_count = contact_count + 1
        WHERE id = NEW.post_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_bulletin_view_count_trigger
    AFTER INSERT ON public.bulletin_post_interactions
    FOR EACH ROW
    WHEN (NEW.interaction_type IN ('view', 'contact_click'))
    EXECUTE FUNCTION update_bulletin_post_view_count();

-- Function to auto-set moderation_status to 'reported' when multiple reports
CREATE OR REPLACE FUNCTION auto_flag_bulletin_post_on_reports()
RETURNS TRIGGER AS $$
DECLARE
    report_count INTEGER;
BEGIN
    -- Count pending reports for this post
    SELECT COUNT(*) INTO report_count
    FROM public.bulletin_post_reports
    WHERE post_id = NEW.post_id
      AND status = 'pending';
    
    -- If 3+ reports, auto-flag for review
    IF report_count >= 3 THEN
        UPDATE public.bulletin_posts
        SET moderation_status = 'reported',
            status = 'pending',
            updated_at = now()
        WHERE id = NEW.post_id
          AND moderation_status != 'reported';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_flag_bulletin_on_reports_trigger
    AFTER INSERT ON public.bulletin_post_reports
    FOR EACH ROW
    WHEN (NEW.status = 'pending')
    EXECUTE FUNCTION auto_flag_bulletin_post_on_reports();

COMMENT ON TABLE public.bulletin_posts IS 'Community bulletin board posts (advertentiebord)';
COMMENT ON TABLE public.bulletin_post_interactions IS 'User interactions with bulletin posts (views, saves, reports, contact clicks)';
COMMENT ON TABLE public.bulletin_post_reports IS 'Community reports on bulletin posts for moderation';
COMMENT ON COLUMN public.bulletin_posts.moderation_result IS 'AI moderation result stored as JSONB';
COMMENT ON COLUMN public.bulletin_posts.moderation_status IS 'Moderation state: pending, approved, rejected, requires_review, reported';

