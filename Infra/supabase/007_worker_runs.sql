-- Migration: create worker_runs table for worker execution tracking (TDA-143)
-- Table captures run metadata, progress, counters, and errors per worker invocation.

CREATE TABLE IF NOT EXISTS public.worker_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot TEXT NOT NULL,
    city TEXT,
    category TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    counters JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enforce allowed status values via check constraint
ALTER TABLE public.worker_runs
    ADD CONSTRAINT worker_runs_status_check
    CHECK (status IN ('pending', 'running', 'finished', 'failed'));

-- Indexes to support admin queries and dashboards
CREATE INDEX IF NOT EXISTS idx_worker_runs_bot ON public.worker_runs(bot);
CREATE INDEX IF NOT EXISTS idx_worker_runs_city ON public.worker_runs(city);
CREATE INDEX IF NOT EXISTS idx_worker_runs_status ON public.worker_runs(status);
CREATE INDEX IF NOT EXISTS idx_worker_runs_created_at ON public.worker_runs(created_at);






