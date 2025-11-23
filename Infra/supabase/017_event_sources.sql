-- Migration: create event_sources table for event scraping configuration
-- Defines enum, table, indexes, and seed rows for initial admin management.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'event_source_status'
    ) THEN
        CREATE TYPE public.event_source_status AS ENUM ('active', 'disabled');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.event_sources (
    id BIGSERIAL PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    list_url TEXT,
    selectors JSONB NOT NULL DEFAULT '{}'::jsonb,
    interval_minutes INTEGER NOT NULL DEFAULT 60 CHECK (interval_minutes > 0),
    status event_source_status NOT NULL DEFAULT 'active',
    last_run_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_error_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_sources_status ON public.event_sources(status);
CREATE INDEX IF NOT EXISTS idx_event_sources_last_success ON public.event_sources(last_success_at DESC NULLS LAST);

COMMENT ON TABLE public.event_sources IS 'Admin-defined event scraping sources (websites + selectors).';
COMMENT ON COLUMN public.event_sources.key IS 'Stable identifier referenced by workers.';
COMMENT ON COLUMN public.event_sources.selectors IS 'JSON selectors config (CSS/xpath/metadata).';
COMMENT ON COLUMN public.event_sources.interval_minutes IS 'Minutes between scraper runs.';
COMMENT ON COLUMN public.event_sources.status IS 'active or disabled; disabled sources must be ignored by workers.';

-- Seed at least four example sources to satisfy Acceptance Criteria.
INSERT INTO public.event_sources (key, name, base_url, list_url, selectors, interval_minutes, status)
VALUES
    (
        'rotterdam_culture',
        'Rotterdam Cultuur Agenda',
        'https://www.rotterdam.nl/cultuur',
        'https://www.rotterdam.nl/cultuur/evenementen/',
        jsonb_build_object(
            'list', '.event-card',
            'title', '.event-card__title',
            'date', '.event-card__date'
        ),
        120,
        'active'
    ),
    (
        'denhaag_events',
        'Den Haag Events',
        'https://denhaag.com/nl',
        'https://denhaag.com/nl/agenda',
        jsonb_build_object(
            'list', '.agenda-item',
            'title', '.agenda-item__title',
            'date', '.agenda-item__date'
        ),
        120,
        'active'
    ),
    (
        'amsterdam_turkish_centre',
        'Amsterdam Turks Cultureel Centrum',
        'https://www.atcc.nl',
        NULL,
        jsonb_build_object(
            'list', '.event',
            'title', '.event-title',
            'date', '.event-date'
        ),
        180,
        'disabled'
    ),
    (
        'utrecht_diaspora_hub',
        'Utrecht Diaspora Hub',
        'https://www.diasporahub-utrecht.nl',
        'https://www.diasporahub-utrecht.nl/events',
        jsonb_build_object(
            'list', '.listing-item',
            'title', '.listing-item__title',
            'date', '.listing-item__date'
        ),
        90,
        'active'
    )
ON CONFLICT (key) DO NOTHING;


INSERT INTO public.event_sources (key, name, base_url, list_url, city_key, selectors, interval_minutes, status)
VALUES
    (
        'sahmeran_events',
        'Şahmeran Entertainment',
        'https://sahmeran.nl',
        'https://sahmeran.nl/events/',
        'rotterdam',
        jsonb_build_object(
            'format', 'html',
            'item_selector', '.jet-listing-grid__item',
            'title_selector', '.jet-listing-dynamic-field__content a',
            'url_selector', '.jet-listing-dynamic-field__content a@href',
            'date_selector', 'time@datetime',
            'location_selector', '.elementor-icon-list-text',
            'description_selector', '.jet-listing-dynamic-field__content p',
            'image_selector', '.jet-listing-dynamic-image__link@href'
        ),
        120,
        'active'
    ),
    (
        'ahoy_events',
        'Ahoy Agenda',
        'https://www.ahoy.nl',
        'https://www.ahoy.nl/agenda',
        'rotterdam',
        jsonb_build_object(
            'format', 'json_ld',
            'script_selector', 'script[type="application/ld+json"]',
            'json_items_path', '$.@graph',
            'json_type_filter', 'Event',
            'json_title_field', 'name',
            'json_url_field', 'url',
            'json_start_field', 'startDate',
            'json_end_field', 'endDate',
            'json_location_field', 'location.name',
            'json_image_field', 'image',
            'json_description_field', 'description',
            'timezone', 'Europe/Amsterdam'
        ),
        60,
        'active'
    )
ON CONFLICT (key) DO NOTHING;



INSERT INTO public.event_sources (key, name, base_url, list_url, city_key, selectors, interval_minutes, status)
VALUES
    (
        'ajda_events',
        'Ajda Events',
        'https://ajda.nl',
        'https://ajda.nl/events-list/',
        'amsterdam',
        jsonb_build_object(
            'format', 'ai_page'
        ),
        180,
        'active'
    ),
    (
        'ediz_events',
        'Ediz Events',
        'https://edizevents.nl',
        'https://edizevents.nl/agenda/',
        'rotterdam',
        jsonb_build_object(
            'format', 'ai_page'
        ),
        180,
        'active'
    )
ON CONFLICT (key) DO NOTHING;



