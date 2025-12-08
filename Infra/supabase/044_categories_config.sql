-- 044_categories_config.sql
-- Categories Configuration Table
-- 
-- Migrates category configuration from YAML to database to avoid
-- synchronization issues and enable dynamic category management.
--
-- Categories are stored in database table, making them available
-- immediately without requiring git commits/pushes.

-- Categories configuration table
CREATE TABLE IF NOT EXISTS public.categories_config (
    id                  BIGSERIAL PRIMARY KEY,
    category_key        TEXT NOT NULL UNIQUE,
    label               TEXT NOT NULL,
    description         TEXT,
    aliases             JSONB DEFAULT '[]'::jsonb,
    google_types        JSONB DEFAULT '[]'::jsonb,
    osm_tags            JSONB,
    discovery_enabled   BOOLEAN DEFAULT true,
    discovery_priority  INTEGER DEFAULT 0,
    discovery_strategy  TEXT,  -- 'catch_all' voor 'other' category
    discovery_max_per_cell INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT categories_config_key_format CHECK (
        category_key ~ '^[a-z0-9_]+$' AND LENGTH(category_key) > 0
    ),
    CONSTRAINT categories_config_discovery_priority_range CHECK (
        discovery_priority >= 0 AND discovery_priority <= 100
    )
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_categories_config_key ON public.categories_config(category_key);
CREATE INDEX IF NOT EXISTS idx_categories_config_discovery ON public.categories_config(discovery_enabled, discovery_priority);

-- Comments for documentation
COMMENT ON TABLE public.categories_config IS 
    'Category configuration - single source of truth for discovery and classification. Synchronized from admin UI or migrated from YAML.';
COMMENT ON COLUMN public.categories_config.category_key IS 
    'Canonical category key (lowercase, underscores) used as identifier (e.g., restaurant, bakery, clinic)';
COMMENT ON COLUMN public.categories_config.label IS 
    'Display label for the category (e.g., "restaurant", "bakkerij", "medische praktijk")';
COMMENT ON COLUMN public.categories_config.description IS 
    'Human-readable description of the category';
COMMENT ON COLUMN public.categories_config.aliases IS 
    'JSONB array of aliases (Turkish/Dutch keywords) for AI classification (e.g., ["ocakbasi", "lokanta"])';
COMMENT ON COLUMN public.categories_config.google_types IS 
    'JSONB array of Google Places API types (legacy, kept for historical parity)';
COMMENT ON COLUMN public.categories_config.osm_tags IS 
    'JSONB structure for OSM Overpass queries: {"any": [{"shop": "bakery"}]} or {"all": [...]}';
COMMENT ON COLUMN public.categories_config.discovery_enabled IS 
    'Whether this category participates in discovery runs (true = discoverable)';
COMMENT ON COLUMN public.categories_config.discovery_priority IS 
    'Priority for discovery ordering (higher = more important, 0-100)';
COMMENT ON COLUMN public.categories_config.discovery_strategy IS 
    'Discovery strategy: NULL (normal OSM tag-based), "catch_all" (for other category)';
COMMENT ON COLUMN public.categories_config.discovery_max_per_cell IS 
    'Maximum results per grid cell for catch-all strategy (only used when strategy="catch_all")';

