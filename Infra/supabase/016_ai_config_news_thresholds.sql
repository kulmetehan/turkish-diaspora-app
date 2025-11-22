-- Add news-specific classification thresholds to ai_config
-- This migration is idempotent (guarded with IF NOT EXISTS)

DO $$
BEGIN
    -- news_diaspora_min_score
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'ai_config'
          AND column_name = 'news_diaspora_min_score'
    ) THEN
        ALTER TABLE public.ai_config
            ADD COLUMN news_diaspora_min_score FLOAT NOT NULL DEFAULT 0.75;
    END IF;

    -- news_nl_min_score
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'ai_config'
          AND column_name = 'news_nl_min_score'
    ) THEN
        ALTER TABLE public.ai_config
            ADD COLUMN news_nl_min_score FLOAT NOT NULL DEFAULT 0.75;
    END IF;

    -- news_tr_min_score
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'ai_config'
          AND column_name = 'news_tr_min_score'
    ) THEN
        ALTER TABLE public.ai_config
            ADD COLUMN news_tr_min_score FLOAT NOT NULL DEFAULT 0.75;
    END IF;

    -- news_local_min_score
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'ai_config'
          AND column_name = 'news_local_min_score'
    ) THEN
        ALTER TABLE public.ai_config
            ADD COLUMN news_local_min_score FLOAT NOT NULL DEFAULT 0.70;
    END IF;

    -- news_origin_min_score
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'ai_config'
          AND column_name = 'news_origin_min_score'
    ) THEN
        ALTER TABLE public.ai_config
            ADD COLUMN news_origin_min_score FLOAT NOT NULL DEFAULT 0.70;
    END IF;

    -- news_geo_min_score
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'ai_config'
          AND column_name = 'news_geo_min_score'
    ) THEN
        ALTER TABLE public.ai_config
            ADD COLUMN news_geo_min_score FLOAT NOT NULL DEFAULT 0.80;
    END IF;

END
$$;

COMMENT ON COLUMN public.ai_config.news_diaspora_min_score IS 'Min score for diaspora feed relevance';
COMMENT ON COLUMN public.ai_config.news_nl_min_score IS 'Min score for NL feed relevance';
COMMENT ON COLUMN public.ai_config.news_tr_min_score IS 'Min score for Turkish feed relevance';
COMMENT ON COLUMN public.ai_config.news_local_min_score IS 'Min score for local feed relevance';
COMMENT ON COLUMN public.ai_config.news_origin_min_score IS 'Min score for origin feed relevance';
COMMENT ON COLUMN public.ai_config.news_geo_min_score IS 'Min score for geopolitics feed relevance';