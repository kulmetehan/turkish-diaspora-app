-- 011_news_ingest.sql
-- Adds raw_ingested_news and news_source_state tables for NewsIngestBot.

CREATE TABLE IF NOT EXISTS news_source_state (
    id BIGSERIAL PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    category TEXT NOT NULL,
    language TEXT NOT NULL,
    region TEXT NULL,
    refresh_minutes INT NOT NULL,
    last_fetched_at TIMESTAMPTZ NULL,
    next_refresh_at TIMESTAMPTZ NULL,
    consecutive_failures INT NOT NULL DEFAULT 0,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS news_source_state_next_refresh_idx
    ON news_source_state (next_refresh_at);

CREATE TABLE IF NOT EXISTS raw_ingested_news (
    id BIGSERIAL PRIMARY KEY,
    source_key TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    category TEXT NOT NULL,
    language TEXT NOT NULL,
    region TEXT NULL,
    title TEXT NOT NULL,
    summary TEXT NULL,
    content TEXT NULL,
    author TEXT NULL,
    link TEXT NOT NULL,
    image_url TEXT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ingest_hash CHAR(40) NOT NULL,
    raw_entry JSONB NOT NULL,
    processing_state TEXT NOT NULL DEFAULT 'pending',
    processing_errors JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS raw_ingested_news_source_hash_key
    ON raw_ingested_news (source_key, ingest_hash);

CREATE INDEX IF NOT EXISTS raw_ingested_news_published_at_idx
    ON raw_ingested_news (published_at DESC);

CREATE INDEX IF NOT EXISTS raw_ingested_news_category_idx
    ON raw_ingested_news (category);

CREATE INDEX IF NOT EXISTS raw_ingested_news_processing_state_idx
    ON raw_ingested_news (processing_state);

