-- 091_prikbord_media_uploads.sql
-- Add media uploads support to Prikbord

-- Add media_urls column for uploaded images/videos
ALTER TABLE public.shared_links
ADD COLUMN IF NOT EXISTS media_urls TEXT[] DEFAULT '{}';

-- Add post_type column to distinguish between link and media posts
ALTER TABLE public.shared_links
ADD COLUMN IF NOT EXISTS post_type TEXT DEFAULT 'link' CHECK (post_type IN ('link', 'media'));

-- Create index for post_type filtering
CREATE INDEX IF NOT EXISTS idx_shared_links_post_type ON public.shared_links(post_type, status) WHERE status = 'active';

COMMENT ON COLUMN public.shared_links.media_urls IS 'Array of media URLs (images/videos) for media posts';
COMMENT ON COLUMN public.shared_links.post_type IS 'Type of post: link (shared link) or media (uploaded media)';

