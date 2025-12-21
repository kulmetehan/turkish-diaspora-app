-- Migration: Add 4 new event sources (Podium Mozaïek, TivoliVredenburg, Bitterzoet, Muziekgebouw)
-- These sources use AI-powered extraction (format: 'ai_page') similar to Doelen and Melkweg

INSERT INTO public.event_sources (key, name, base_url, list_url, city_key, selectors, interval_minutes, status)
VALUES
    (
        'podiummozaiek_events',
        'Podium Mozaïek Amsterdam',
        'https://www.podiummozaiek.nl',
        'https://www.podiummozaiek.nl/programma/agenda',
        'amsterdam',
        jsonb_build_object('format', 'ai_page'),
        180,
        'active'
    ),
    (
        'tivolivredenburg_events',
        'TivoliVredenburg Utrecht',
        'https://www.tivolivredenburg.nl',
        'https://www.tivolivredenburg.nl/agenda/?genre=turks',
        'utrecht',
        jsonb_build_object('format', 'ai_page'),
        180,
        'active'
    ),
    (
        'bitterzoet_events',
        'Bitterzoet Amsterdam',
        'https://www.bitterzoet.com',
        'https://www.bitterzoet.com/agenda/',
        'amsterdam',
        jsonb_build_object('format', 'ai_page'),
        180,
        'active'
    ),
    (
        'muziekgebouw_events',
        'Muziekgebouw Amsterdam',
        'https://www.muziekgebouw.nl',
        'https://www.muziekgebouw.nl/nl/agenda?page=1&max=60',
        'amsterdam',
        jsonb_build_object('format', 'ai_page'),
        180,
        'active'
    )
ON CONFLICT (key) DO NOTHING;

-- Verify the inserts
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.event_sources
        WHERE key IN ('podiummozaiek_events', 'tivolivredenburg_events', 'bitterzoet_events', 'muziekgebouw_events')
    ) THEN
        RAISE EXCEPTION 'Failed to insert new event sources';
    END IF;
END $$;

COMMENT ON TABLE public.event_sources IS 'Added 4 new event sources: podiummozaiek_events, tivolivredenburg_events, bitterzoet_events, muziekgebouw_events (2025-01-XX)';

