-- N3.3 Full-text search support for news search endpoint

ALTER TABLE public.raw_ingested_news
    ADD COLUMN IF NOT EXISTS news_search_tsv tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(title, '')), 'A')
        || setweight(to_tsvector('simple', coalesce(summary, '')), 'B')
        || setweight(to_tsvector('simple', coalesce(content, '')), 'C')
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_news_search_tsv
    ON public.raw_ingested_news
    USING GIN (news_search_tsv);


