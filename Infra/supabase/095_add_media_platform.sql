-- 095_add_media_platform.sql
-- Add 'media' as a valid platform value and 'media_upload' as preview_method for shared_links

-- Drop the existing platform check constraint
ALTER TABLE public.shared_links DROP CONSTRAINT IF EXISTS shared_links_platform_check;

-- Add the updated platform constraint with 'media' included
ALTER TABLE public.shared_links ADD CONSTRAINT shared_links_platform_check CHECK (platform IN (
    'marktplaats',
    'instagram',
    'facebook',
    'youtube',
    'twitter',
    'tiktok',
    'news',
    'event',
    'media',
    'other'
));

-- Drop the existing preview_method check constraint (if it exists as a named constraint)
-- Note: The constraint might be inline, so we need to check and recreate the column if needed
DO $$
BEGIN
    -- Check if there's a constraint on preview_method
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'shared_links_preview_method_check'
    ) THEN
        ALTER TABLE public.shared_links DROP CONSTRAINT shared_links_preview_method_check;
    END IF;
END $$;

-- Add updated preview_method constraint with 'media_upload' included
ALTER TABLE public.shared_links ADD CONSTRAINT shared_links_preview_method_check CHECK (
    preview_method IS NULL OR preview_method IN ('oembed', 'opengraph', 'fallback', 'manual', 'media_upload')
);

COMMENT ON COLUMN public.shared_links.platform IS 'Platform/source of the shared link. "media" is used for direct media uploads (images/videos).';
COMMENT ON COLUMN public.shared_links.preview_method IS 'Method used to generate preview: oembed, opengraph, fallback, manual, or media_upload';

