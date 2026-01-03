-- 092_contact_submissions.sql
-- Contact form submissions table

CREATE TABLE IF NOT EXISTS public.contact_submissions (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'read', 'replied', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraint: at least email or phone must be provided
    CONSTRAINT check_contact_info CHECK (
        email IS NOT NULL OR phone IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS idx_contact_submissions_status ON public.contact_submissions(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_contact_submissions_created_at ON public.contact_submissions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_contact_submissions_email ON public.contact_submissions(email) WHERE email IS NOT NULL;

COMMENT ON TABLE public.contact_submissions IS 'Contact form submissions from users';
COMMENT ON COLUMN public.contact_submissions.status IS 'Status: new, read, replied, archived';





