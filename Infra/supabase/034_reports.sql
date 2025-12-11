-- 034_reports.sql
-- Reporting system for user reports on content and users (EPIC-2.5, Story 40)

CREATE TYPE report_status AS ENUM ('pending', 'resolved', 'dismissed');

CREATE TABLE IF NOT EXISTS public.reports (
    id BIGSERIAL PRIMARY KEY,
    reported_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- Optional, for authenticated users
    reported_by_client_id TEXT, -- Required for anonymous users
    report_type TEXT NOT NULL CHECK (report_type IN ('location', 'note', 'reaction', 'user')), -- Type of content/user being reported
    target_id BIGINT NOT NULL, -- ID of the reported item (location_id, note_id, reaction_id, or user_id)
    reason TEXT NOT NULL, -- Report reason/category (e.g., 'spam', 'inappropriate', 'harassment', 'false_information')
    details TEXT, -- Optional additional details from reporter
    status report_status NOT NULL DEFAULT 'pending',
    resolved_by UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- Admin who resolved the report
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT, -- Admin notes on resolution
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Ensure at least one identifier is present
    CONSTRAINT reports_identifier_check CHECK (
        (reported_by_user_id IS NOT NULL) OR (reported_by_client_id IS NOT NULL AND reported_by_client_id != '')
    )
);

CREATE INDEX IF NOT EXISTS idx_reports_status ON public.reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_type_target ON public.reports(report_type, target_id);
CREATE INDEX IF NOT EXISTS idx_reports_created ON public.reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_user_id ON public.reports(reported_by_user_id) WHERE reported_by_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reports_client_id ON public.reports(reported_by_client_id) WHERE reported_by_client_id IS NOT NULL;

COMMENT ON TABLE public.reports IS 'User reports on content (locations, notes, reactions) and users';
COMMENT ON COLUMN public.reports.reported_by_user_id IS 'Authenticated user who reported (optional)';
COMMENT ON COLUMN public.reports.reported_by_client_id IS 'Anonymous client_id who reported (required if user_id is NULL)';
COMMENT ON COLUMN public.reports.report_type IS 'Type of content being reported: location, note, reaction, or user';
COMMENT ON COLUMN public.reports.target_id IS 'ID of the reported item (varies by report_type)';
COMMENT ON COLUMN public.reports.reason IS 'Report reason/category';
COMMENT ON COLUMN public.reports.status IS 'Report status: pending (waiting for review), resolved (action taken), dismissed (no action needed)';









