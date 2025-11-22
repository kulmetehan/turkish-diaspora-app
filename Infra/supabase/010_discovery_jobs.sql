-- Migration: create discovery_jobs table for Discovery Train orchestration
-- Table tracks (city, district?, category) jobs for sequential discovery execution.

CREATE TABLE IF NOT EXISTS public.discovery_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city_key TEXT NOT NULL,
    district_key TEXT,  -- NULL for city-level jobs (cities without districts)
    category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

-- Enforce allowed status values via check constraint
ALTER TABLE public.discovery_jobs
    ADD CONSTRAINT discovery_jobs_status_check
    CHECK (status IN ('pending', 'running', 'finished', 'failed'));

-- Indexes for efficient job selection and queries
CREATE INDEX IF NOT EXISTS idx_discovery_jobs_status ON public.discovery_jobs(status);
CREATE INDEX IF NOT EXISTS idx_discovery_jobs_city ON public.discovery_jobs(city_key);
CREATE INDEX IF NOT EXISTS idx_discovery_jobs_category ON public.discovery_jobs(category);
CREATE INDEX IF NOT EXISTS idx_discovery_jobs_created_at ON public.discovery_jobs(created_at);

-- Composite index for FIFO job selection (pending jobs, oldest first)
CREATE INDEX IF NOT EXISTS idx_discovery_jobs_pending_fifo 
    ON public.discovery_jobs(status, created_at) 
    WHERE status = 'pending';

-- Add comments
COMMENT ON TABLE public.discovery_jobs IS 'Job queue for Discovery Train: sequential discovery orchestration by (city, district?, category)';
COMMENT ON COLUMN public.discovery_jobs.city_key IS 'City key from cities.yml (e.g., rotterdam, vlaardingen)';
COMMENT ON COLUMN public.discovery_jobs.district_key IS 'District key from cities.yml (NULL for city-level jobs)';
COMMENT ON COLUMN public.discovery_jobs.category IS 'Category key from categories.yml (e.g., restaurant, bakery)';
COMMENT ON COLUMN public.discovery_jobs.status IS 'Job status: pending, running, finished, failed';
COMMENT ON COLUMN public.discovery_jobs.attempts IS 'Number of execution attempts (for retry logic)';
COMMENT ON COLUMN public.discovery_jobs.last_error IS 'Last error message if job failed';




