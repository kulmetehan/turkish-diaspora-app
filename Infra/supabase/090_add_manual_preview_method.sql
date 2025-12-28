-- 090_add_manual_preview_method.sql
-- Add 'manual' as a valid preview_method value for shared_links

-- Drop the existing constraint
ALTER TABLE public.shared_links 
DROP CONSTRAINT IF EXISTS shared_links_preview_method_check;

-- Add the new constraint with 'manual' included
ALTER TABLE public.shared_links 
ADD CONSTRAINT shared_links_preview_method_check 
CHECK (preview_method IN ('oembed', 'opengraph', 'fallback', 'manual'));

