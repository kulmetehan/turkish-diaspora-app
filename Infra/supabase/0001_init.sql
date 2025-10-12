-- Create custom ENUM types if they don't already exist
-- This ensures our 'state' columns have controlled values.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'location_state') THEN
        CREATE TYPE location_state AS ENUM (
            'CANDIDATE',
            'PENDING_VERIFICATION',
            'VERIFIED',
            'SUSPENDED',
            'RETIRED'
        );
    END IF;
END$$;


-- 1. Main table for all business data: locations
CREATE TABLE IF NOT EXISTS public.locations (
    -- Identity
    id                  bigserial PRIMARY KEY,
    place_id            text UNIQUE, -- Google Place ID, a key identifier
    source              text NOT NULL DEFAULT 'google_places',

    -- Core
    name                text NOT NULL,
    address             text,
    lat                 numeric(10, 7),
    lng                 numeric(10, 7),
    category            text,
    business_status     text, -- e.g., 'OPERATIONAL', 'CLOSED_PERMANENTLY'

    -- Reputation
    rating              numeric(2, 1),
    user_ratings_total  integer DEFAULT 0,

    -- Lifecycle
    state               location_state NOT NULL DEFAULT 'CANDIDATE',
    confidence_score    numeric(3, 2),
    is_probable_not_open_yet boolean DEFAULT false,

    -- Freshness
    first_seen_at       timestamptz NOT NULL DEFAULT now(),
    last_seen_at        timestamptz NOT NULL DEFAULT now(),
    last_verified_at    timestamptz,
    next_check_at       timestamptz,
    freshness_score     numeric(3, 2),

    -- Audit
    evidence_urls       text[], -- Array of URLs used for verification
    notes               text,
    is_retired          boolean DEFAULT false
);

-- Add comments to columns for clarity
COMMENT ON COLUMN public.locations.place_id IS 'Unique ID from the data source, e.g., Google Places API.';
COMMENT ON COLUMN public.locations.state IS 'The current state of the location in our verification pipeline.';
COMMENT ON COLUMN public.locations.next_check_at IS 'Timestamp for when the MonitorBot should re-check this record.';


-- 2. Audit trail for all AI actions: ai_logs
CREATE TABLE IF NOT EXISTS public.ai_logs (
    id                  bigserial PRIMARY KEY,
    location_id         bigint REFERENCES public.locations(id) ON DELETE SET NULL,
    action_type         text NOT NULL, -- e.g., 'classification', 'enrichment'
    prompt              text,
    raw_response        jsonb,
    validated_output    jsonb,
    model_used          text,
    is_success          boolean NOT NULL,
    error_message       text,
    created_at          timestamptz NOT NULL DEFAULT now()
);


-- 3. Queue for orchestration: tasks
CREATE TABLE IF NOT EXISTS public.tasks (
    id                  bigserial PRIMARY KEY,
    location_id         bigint REFERENCES public.locations(id) ON DELETE CASCADE,
    task_type           text NOT NULL, -- e.g., 'discover', 'verify', 'monitor'
    status              text NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    payload             jsonb,
    attempts            integer DEFAULT 0,
    last_attempted_at   timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now()
);


-- 4. Gold records for active learning: training_data
CREATE TABLE IF NOT EXISTS public.training_data (
    id                  bigserial PRIMARY KEY,
    location_id         bigint REFERENCES public.locations(id),
    input_data          jsonb NOT NULL,
    expected_output     jsonb NOT NULL,
    is_gold_standard    boolean DEFAULT true,
    notes               text,
    created_at          timestamptz NOT NULL DEFAULT now()
);


-- 5. Mapping of business types to frontend categories and icons: category_icon_map
CREATE TABLE IF NOT EXISTS public.category_icon_map (
    id                  serial PRIMARY KEY,
    source_category     text UNIQUE NOT NULL, -- e.g., 'bakery', 'restaurant' from Google
    display_category    text NOT NULL, -- e.g., 'Bakkerij', 'Restaurant'
    icon_name           text NOT NULL -- e.g., 'bakery-icon', 'restaurant-icon'
);


-- Create indexes for performance on frequently queried columns
-- The IF NOT EXISTS clause makes these idempotent
CREATE INDEX IF NOT EXISTS idx_locations_state ON public.locations(state);
CREATE INDEX IF NOT EXISTS idx_locations_category ON public.locations(category);
CREATE INDEX IF NOT EXISTS idx_locations_next_check_at ON public.locations(next_check_at);
CREATE INDEX IF NOT EXISTS idx_tasks_status_type ON public.tasks(status, task_type);