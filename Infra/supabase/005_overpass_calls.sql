-- Overpass API call telemetry table
-- Tracks all Overpass API requests for monitoring and debugging
CREATE TABLE IF NOT EXISTS public.overpass_calls (
    id                  bigserial PRIMARY KEY,
    ts                  timestamptz NOT NULL DEFAULT now(),
    endpoint           text NOT NULL,
    bbox_or_center     text, -- "lat,lng" or "lat_min,lng_min,lat_max,lng_max"
    radius_m           integer,
    query_bytes        integer,
    status_code        integer,
    found              integer DEFAULT 0,
    normalized         integer DEFAULT 0,
    category_set       text[], -- Array of categories requested
    cell_id            text, -- Unique identifier for the grid cell
    attempt            integer DEFAULT 1,
    duration_ms        integer,
    error_message      text,
    retry_after_s      integer,
    user_agent         text,
    timeout_s          integer,
    max_results        integer,
    raw_preview        text
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_overpass_calls_ts ON public.overpass_calls(ts);
CREATE INDEX IF NOT EXISTS idx_overpass_calls_endpoint ON public.overpass_calls(endpoint);
CREATE INDEX IF NOT EXISTS idx_overpass_calls_status ON public.overpass_calls(status_code);
CREATE INDEX IF NOT EXISTS idx_overpass_calls_cell_id ON public.overpass_calls(cell_id);
CREATE INDEX IF NOT EXISTS idx_overpass_calls_category_set ON public.overpass_calls USING GIN(category_set);
-- Composite index for grid coverage queries (cell_id + status_code for efficient filtering)
CREATE INDEX IF NOT EXISTS idx_overpass_calls_cell_status ON public.overpass_calls(cell_id, status_code);

-- Comments for clarity
COMMENT ON TABLE public.overpass_calls IS 'Telemetry for all Overpass API calls made by the discovery bot';
COMMENT ON COLUMN public.overpass_calls.bbox_or_center IS 'Either center point "lat,lng" or bounding box "lat_min,lng_min,lat_max,lng_max"';
COMMENT ON COLUMN public.overpass_calls.category_set IS 'Array of category keys requested in this call';
COMMENT ON COLUMN public.overpass_calls.cell_id IS 'Unique identifier for the grid cell being queried';
COMMENT ON COLUMN public.overpass_calls.attempt IS 'Attempt number for this cell (1-based)';
COMMENT ON COLUMN public.overpass_calls.found IS 'Number of raw elements returned by Overpass';
COMMENT ON COLUMN public.overpass_calls.normalized IS 'Number of elements successfully normalized and inserted';
