# Reset en Run Sahmeran Events Flow

Dit document beschrijft de exacte stappen om de Sahmeran events pipeline volledig te resetten en opnieuw uit te voeren.

## Stap 1: Reset Database

Voer de reset queries uit in Supabase SQL Editor of via psql:

```sql
-- Reset script voor Sahmeran events
-- Voer deze queries uit in de juiste volgorde

-- 1. Reset event_pages_raw naar pending voor Sahmeran
UPDATE event_pages_raw
SET processing_state = 'pending',
    errors = NULL,
    updated_at = now()
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');

-- 2. Verwijder alle event_raw records voor Sahmeran
DELETE FROM event_raw
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');

-- 3. Verwijder alle events_candidate records voor Sahmeran
DELETE FROM events_candidate
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');

-- 4. Reset detail_page_extracted flags in raw_payload (voor event_raw die mogelijk blijven)
UPDATE event_raw
SET raw_payload = raw_payload - 'detail_page_extracted' - 'detail_page_url' - 'detail_page_extracted_event',
    updated_at = now()
WHERE raw_payload ? 'detail_page_extracted'
  AND event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');
```

**Verificatie na reset:**
```sql
SELECT 
    'event_pages_raw' as table_name,
    COUNT(*) FILTER (WHERE processing_state = 'pending') as pending_count,
    COUNT(*) as total_count
FROM event_pages_raw
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
UNION ALL
SELECT 
    'event_raw' as table_name,
    0 as pending_count,
    COUNT(*) as total_count
FROM event_raw
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
UNION ALL
SELECT 
    'events_candidate' as table_name,
    0 as pending_count,
    COUNT(*) as total_count
FROM events_candidate
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');
```

Verwacht resultaat: `event_pages_raw` heeft pending_count > 0, `event_raw` en `events_candidate` hebben total_count = 0.

## Stap 2: Run Event Scraper Bot

Deze bot haalt de HTML pages op van Sahmeran:

```bash
cd Backend
source .venv/bin/activate  # Of je virtual environment activeren
python -m app.workers.event_scraper_bot
```

**Verificatie na scraper:**
```sql
SELECT 
    processing_state,
    COUNT(*) as count
FROM event_pages_raw
WHERE event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
GROUP BY processing_state
ORDER BY processing_state;
```

Verwacht: Meerdere records met `processing_state = 'pending'` of `'extracted'`.

## Stap 3: Run Event AI Extractor Bot

Deze bot extraheert events uit HTML en haalt detail pages op voor events zonder locatie:

```bash
python -m app.workers.event_ai_extractor_bot --limit 50
```

**Verificatie na AI extractor:**
```sql
-- Controleer event_raw records met detail page informatie
SELECT 
    er.id,
    er.title,
    er.location_text,
    er.venue,
    er.event_url,
    er.processing_state,
    CASE 
        WHEN er.raw_payload ? 'detail_page_extracted' THEN 'yes'
        ELSE 'no'
    END as detail_page_extracted,
    er.raw_payload->>'detail_page_url' as detail_page_url,
    er.raw_payload->'detail_page_extracted_event'->>'venue' as extracted_venue_from_detail,
    er.raw_payload->'detail_page_extracted_event'->>'location_text' as extracted_location_from_detail
FROM event_raw er
WHERE er.event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
ORDER BY er.created_at DESC
LIMIT 20;
```

Verwacht: 
- Events met `location_text` en `venue` waar mogelijk
- Events met `detail_page_extracted = 'yes'` als detail pages zijn opgehaald
- `extracted_location_from_detail` en `extracted_venue_from_detail` bevatten volledige adressen waar beschikbaar

## Stap 4: Run Event Normalization Bot

Deze bot normaliseert event_raw naar events_candidate:

```bash
python -m app.workers.event_normalization_bot --limit 200
```

**Verificatie na normalization:**
```sql
-- Controleer events_candidate met locatie informatie
SELECT 
    ec.id,
    ec.location_text,
    er.venue,
    er.title,
    CASE 
        WHEN ec.location_text IS NOT NULL THEN 'has_location'
        ELSE 'no_location'
    END as status
FROM events_candidate ec
JOIN event_raw er ON er.id = ec.event_raw_id
WHERE ec.event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
ORDER BY ec.created_at DESC
LIMIT 20;
```

Verwacht: Events met `location_text` die volledige adressen bevatten waar mogelijk (niet alleen stad namen).

## Stap 5: Run Event Geocoding Bot

Deze bot geocodeert locaties naar lat/lng:

```bash
python -m app.workers.event_geocoding_bot --limit 200
```

**Verificatie na geocoding:**
```sql
-- Controleer geocodeerde events
SELECT 
    ec.id,
    ec.location_text,
    ec.lat,
    ec.lng,
    ec.country,
    er.venue,
    CASE 
        WHEN ec.location_text IS NOT NULL AND ec.lat IS NOT NULL AND ec.lng IS NOT NULL THEN 'geocoded'
        WHEN ec.location_text IS NOT NULL AND ec.lat IS NULL THEN 'needs_geocoding'
        WHEN ec.location_text IS NULL THEN 'no_location'
        ELSE 'unknown'
    END as status
FROM events_candidate ec
JOIN event_raw er ON er.id = ec.event_raw_id
WHERE ec.event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
ORDER BY ec.created_at DESC
LIMIT 20;
```

Verwacht: Events met `lat` en `lng` waar `location_text` volledige adressen bevat.

## Stap 6: Run Event Enrichment Bot

Deze bot verrijkt events met extra informatie:

```bash
python -m app.workers.event_enrichment_bot --limit 200
```

## Stap 7: Finale Verificatie

Voer deze queries uit om de complete status te controleren:

```sql
-- 1. Samenvatting: Totaal aantal events en status
SELECT 
    COUNT(*) as total_events,
    COUNT(*) FILTER (WHERE ec.location_text IS NOT NULL) as with_location,
    COUNT(*) FILTER (WHERE ec.lat IS NOT NULL AND ec.lng IS NOT NULL) as with_coordinates,
    COUNT(*) FILTER (WHERE ec.lat IS NOT NULL AND ec.lng IS NOT NULL AND ec.country = 'netherlands') as in_netherlands,
    COUNT(*) FILTER (WHERE er.venue IS NOT NULL AND ec.lat IS NOT NULL AND ec.lng IS NOT NULL) as with_venue_and_coords
FROM events_candidate ec
JOIN event_raw er ON er.id = ec.event_raw_id
WHERE ec.event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');

-- 2. Controleer detail pages die zijn opgehaald
SELECT 
    COUNT(*) FILTER (WHERE er.raw_payload ? 'detail_page_extracted') as detail_pages_fetched,
    COUNT(*) FILTER (WHERE er.raw_payload ? 'detail_page_extracted' 
                     AND er.raw_payload->'detail_page_extracted_event'->>'location_text' IS NOT NULL) as detail_pages_with_location,
    COUNT(*) FILTER (WHERE er.raw_payload ? 'detail_page_extracted' 
                     AND er.raw_payload->'detail_page_extracted_event'->>'venue' IS NOT NULL) as detail_pages_with_venue
FROM event_raw er
WHERE er.event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events');

-- 3. Events met volledige adressen vs alleen stad namen
SELECT 
    ec.id,
    ec.location_text,
    er.venue,
    ec.lat,
    ec.lng,
    CASE 
        WHEN er.venue IS NULL AND ec.location_text ~ '^[A-Za-z\s,]+$' AND ec.location_text !~ '\d' THEN 'only_city_name'
        WHEN er.venue IS NOT NULL OR ec.location_text ~ '\d' OR ec.location_text ~ ',\s*\d{4}' THEN 'has_details'
        ELSE 'unknown'
    END as location_type
FROM events_candidate ec
JOIN event_raw er ON er.id = ec.event_raw_id
WHERE ec.event_source_id = (SELECT id FROM event_sources WHERE key = 'sahmeran_events')
  AND ec.location_text IS NOT NULL
ORDER BY ec.created_at DESC
LIMIT 30;
```

## Success Criteria

De pipeline is succesvol als:
1. ✅ Events worden correct geëxtraheerd uit HTML pages
2. ✅ Detail pages worden opgehaald voor events zonder locatie
3. ✅ Volledige adressen worden geëxtraheerd uit detail pages (niet alleen stad namen)
4. ✅ Events met volledige adressen worden correct gegeocodeerd
5. ✅ Events verschijnen op de frontend map op de juiste locatie (niet op stad centrum)

## Troubleshooting

Als events nog steeds alleen stad namen hebben:
1. Controleer of detail pages worden opgehaald (query 2 in finale verificatie)
2. Controleer `extracted_location_from_detail` in `event_raw.raw_payload`
3. Controleer de AI logs voor extractie fouten
4. Controleer of de verbeterde prompt correct is geïmplementeerd

Als events niet op de map verschijnen:
1. Controleer of `lat` en `lng` zijn ingesteld
2. Controleer of `country = 'netherlands'` voor Nederlandse events
3. Controleer de `events_public` view filters










