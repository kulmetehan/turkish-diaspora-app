-- 043_cities_config.sql
-- Cities and Districts Configuration Tables
-- 
-- Migrates city/district configuration from YAML to database to avoid
-- synchronization issues between admin UI changes and GitHub Actions.
--
-- Cities and districts are stored in database tables, making them available
-- immediately without requiring git commits/pushes.

-- Cities configuration table
CREATE TABLE IF NOT EXISTS public.cities_config (
    id              BIGSERIAL PRIMARY KEY,
    city_key        TEXT NOT NULL UNIQUE,
    city_name       TEXT NOT NULL,
    country         TEXT NOT NULL DEFAULT 'NL',
    center_lat      NUMERIC(10, 7),
    center_lng      NUMERIC(10, 7),
    config_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT cities_config_city_key_format CHECK (
        city_key ~ '^[a-z0-9_]+$' AND LENGTH(city_key) > 0
    ),
    CONSTRAINT cities_config_country_format CHECK (
        country ~ '^[A-Z]{2}$'
    ),
    CONSTRAINT cities_config_center_lat_range CHECK (
        center_lat IS NULL OR (center_lat >= -90.0 AND center_lat <= 90.0)
    ),
    CONSTRAINT cities_config_center_lng_range CHECK (
        center_lng IS NULL OR (center_lng >= -180.0 AND center_lng <= 180.0)
    )
);

-- Districts configuration table
CREATE TABLE IF NOT EXISTS public.districts_config (
    id              BIGSERIAL PRIMARY KEY,
    city_key        TEXT NOT NULL REFERENCES public.cities_config(city_key) ON DELETE CASCADE,
    district_key    TEXT NOT NULL,
    lat_min         NUMERIC(10, 7) NOT NULL,
    lat_max         NUMERIC(10, 7) NOT NULL,
    lng_min         NUMERIC(10, 7) NOT NULL,
    lng_max         NUMERIC(10, 7) NOT NULL,
    config_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: one district key per city
    UNIQUE(city_key, district_key),
    
    -- Constraints
    CONSTRAINT districts_config_district_key_format CHECK (
        district_key ~ '^[a-z0-9_]+$' AND LENGTH(district_key) > 0
    ),
    CONSTRAINT districts_config_bbox_lat_valid CHECK (
        lat_min < lat_max AND lat_min >= -90.0 AND lat_max <= 90.0
    ),
    CONSTRAINT districts_config_bbox_lng_valid CHECK (
        lng_min < lng_max AND lng_min >= -180.0 AND lng_max <= 180.0
    )
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cities_config_city_key ON public.cities_config(city_key);
CREATE INDEX IF NOT EXISTS idx_districts_config_city_key ON public.districts_config(city_key);
CREATE INDEX IF NOT EXISTS idx_districts_config_city_district ON public.districts_config(city_key, district_key);

-- Comments for documentation
COMMENT ON TABLE public.cities_config IS 
    'City configuration synchronized from admin UI. Primary source of truth for Discovery Train and other services.';
COMMENT ON TABLE public.districts_config IS 
    'District configuration synchronized from admin UI. Districts belong to cities via foreign key.';
    
COMMENT ON COLUMN public.cities_config.city_key IS 
    'Normalized city key (lowercase, underscores) used as identifier (e.g., rotterdam, den_haag)';
COMMENT ON COLUMN public.cities_config.city_name IS 
    'Display name for the city (e.g., Rotterdam, Den Haag)';
COMMENT ON COLUMN public.cities_config.country IS 
    '2-letter ISO country code (default: NL)';
COMMENT ON COLUMN public.cities_config.center_lat IS 
    'City center latitude (WGS84 degrees)';
COMMENT ON COLUMN public.cities_config.center_lng IS 
    'City center longitude (WGS84 degrees)';
COMMENT ON COLUMN public.cities_config.config_json IS 
    'Additional configuration stored as JSON (e.g., apply references, metadata)';
    
COMMENT ON COLUMN public.districts_config.city_key IS 
    'Foreign key to cities_config.city_key';
COMMENT ON COLUMN public.districts_config.district_key IS 
    'Normalized district key (lowercase, underscores) used as identifier (e.g., centrum, noord)';
COMMENT ON COLUMN public.districts_config.lat_min IS 
    'Minimum latitude of district bounding box (WGS84 degrees)';
COMMENT ON COLUMN public.districts_config.lat_max IS 
    'Maximum latitude of district bounding box (WGS84 degrees)';
COMMENT ON COLUMN public.districts_config.lng_min IS 
    'Minimum longitude of district bounding box (WGS84 degrees)';
COMMENT ON COLUMN public.districts_config.lng_max IS 
    'Maximum longitude of district bounding box (WGS84 degrees)';
COMMENT ON COLUMN public.districts_config.config_json IS 
    'Additional configuration stored as JSON (e.g., apply references, metadata)';

