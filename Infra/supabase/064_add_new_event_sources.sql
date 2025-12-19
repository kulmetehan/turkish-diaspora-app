-- Migration: Add 4 new event sources for Meervaart, Melkweg, Paradiso, and De Doelen
-- These sources use AI-powered extraction (format: 'ai_page') similar to Sahmeran/Ajda/Ediz
-- The EventAIExtractorBot will automatically click through to detail pages when event data is incomplete

INSERT INTO public.event_sources (key, name, base_url, list_url, city_key, selectors, interval_minutes, status)
VALUES
    (
        'meervaart_events',
        'Meervaart Theater',
        'https://meervaart.nl',
        'https://meervaart.nl/agenda',
        'amsterdam',
        jsonb_build_object('format', 'ai_page'),
        180,
        'active'
    ),
    (
        'melkweg_events',
        'Melkweg Amsterdam',
        'https://www.melkweg.nl',
        'https://www.melkweg.nl/nl/agenda/',
        'amsterdam',
        jsonb_build_object('format', 'ai_page'),
        180,
        'active'
    ),
    (
        'paradiso_events',
        'Paradiso Amsterdam',
        'https://www.paradiso.nl',
        'https://www.paradiso.nl/landing/concertagenda-paradiso/2069817',
        'amsterdam',
        jsonb_build_object('format', 'ai_page'),
        180,
        'active'
    ),
    (
        'dedoelen_events',
        'De Doelen Rotterdam',
        'https://www.dedoelen.nl',
        'https://www.dedoelen.nl/nl/agenda',
        'rotterdam',
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
        WHERE key IN ('meervaart_events', 'melkweg_events', 'paradiso_events', 'dedoelen_events')
    ) THEN
        RAISE EXCEPTION 'Failed to insert new event sources';
    END IF;
END $$;

COMMENT ON TABLE public.event_sources IS 'Added 4 new event sources: meervaart_events, melkweg_events, paradiso_events, dedoelen_events (2025-01-XX)';
