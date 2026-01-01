-- 096_prikbord_text_posts.sql
-- Add support for text-only posts (Facebook-style status updates)

-- Make url column nullable to support text-only posts
ALTER TABLE public.shared_links 
ALTER COLUMN url DROP NOT NULL;

-- Drop the existing post_type check constraint
ALTER TABLE public.shared_links DROP CONSTRAINT IF EXISTS shared_links_post_type_check;

-- Add updated post_type constraint with 'text' included
ALTER TABLE public.shared_links 
ADD CONSTRAINT shared_links_post_type_check CHECK (post_type IN ('link', 'media', 'text'));

-- Update the comment for post_type
COMMENT ON COLUMN public.shared_links.post_type IS 'Type of post: link (shared link), media (uploaded media), or text (text-only status update)';

-- Note: Text posts will use platform='other' (already exists in platform enum)
-- No need to add 'text' to platform enum as 'other' is appropriate for text posts

