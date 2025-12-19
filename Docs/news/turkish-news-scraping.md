# Turkish News Scraping Feature

## Overzicht

De "Turks Nieuws" categorie biedt nieuwsartikelen van Turkse-Nederlandse nieuwssites die geen RSS feeds aanbieden. Deze feature gebruikt een two-stage scraping pipeline met AI extractie om artikelen te extraheren en te normaliseren.

## Architectuur

### Data Flow

```
Turkish News Crawler (2x/dag via GitHub Actions)
  ↓
turkish_news_scraper_bot (Stage 1)
  ↓
NewsScraperService → BaseScraperService
  ↓
news_pages_raw (raw HTML storage)
  ↓
news_ai_extractor_bot (Stage 2)
  ↓
NewsExtractionService → OpenAIService
  ↓
raw_ingested_news (extracted articles)
  ↓
News Classify Bot (bestaand)
  ↓
normalized_news (bestaand)
  ↓
Frontend: /api/v1/news?feed=nl&categories=turks_nieuws
```

### Hergebruik van Event Patterns

De implementatie hergebruikt bewezen patterns van de event scraping pipeline:

- **BaseScraperService**: Shared HTTP client, retry logic, concurrency control (herbruikbaar voor events en news)
- **OpenAIService**: Direct hergebruik voor AI extractie
- **Two-stage pipeline**: Scraper → AI Extractor (zoals events)
- **Database pattern**: `news_pages_raw` (zoals `event_pages_raw`) + `raw_ingested_news` (bestaand)

## Componenten

### Backend Services

#### BaseScraperService
**Locatie:** `Backend/services/base_scraper_service.py`

Shared base class voor HTTP scraping:
- HTTP client management (async context manager)
- Retry logic met exponential backoff
- Concurrency control via semaphore
- Gebruikt door zowel `EventScraperService` als `NewsScraperService`

#### NewsScraperService
**Locatie:** `Backend/services/news_scraper_service.py`

News-specifieke scraping service:
- Erft van `BaseScraperService`
- Scrapet homepage/main page van nieuwssites
- Slaat raw HTML op in `news_pages_raw`
- Site-agnostic (AI extractie doet het zware werk)

#### NewsExtractionService
**Locatie:** `Backend/services/news_extraction_service.py`

AI extractie service:
- Gebruikt `OpenAIService` voor structured extraction
- Extracteert laatste 3 artikelen per pagina
- Normaliseert naar `ExtractedNewsPayload` format
- HTML chunking voor grote pagina's

#### News Pages Raw Service
**Locatie:** `Backend/services/news_pages_raw_service.py`

Database service voor raw HTML storage:
- `insert_news_page_raw()` - Insert met deduplicatie
- `fetch_pending_news_pages()` - Haal pending pages op
- `update_news_page_processing_state()` - Update state

### Workers

#### Turkish News Scraper Bot
**Locatie:** `Backend/app/workers/turkish_news_scraper_bot.py`

Stage 1 worker:
- Filtert op scraping sources (`source_key LIKE 'scrape_%'`)
- Scrapet alle geconfigureerde Turkse-Nederlandse nieuwssites
- Slaat raw HTML op in `news_pages_raw`
- Scheduling: 2x per dag (08:00, 20:00 UTC) via GitHub Actions

#### News AI Extractor Bot
**Locatie:** `Backend/app/workers/news_ai_extractor_bot.py`

Stage 2 worker:
- Haalt pending pages op uit `news_pages_raw`
- Gebruikt `NewsExtractionService` voor AI extractie
- Schrijft extracted articles naar `raw_ingested_news`
- Deduplicatie via `ingest_hash` (source_key + url + published_at)

### Database Schema

#### news_pages_raw
**Locatie:** `Infra/supabase/024_news_pages_raw.sql`

Tabel voor raw HTML storage:
- `news_source_key` - Source identifier (e.g., 'scrape_turksemedia_nl')
- `page_url` - URL van gescrapete pagina
- `response_body` - Raw HTML content
- `content_hash` - SHA1 hash voor deduplicatie
- `processing_state` - pending | extracted | error_fetch | error_extract

#### raw_ingested_news
**Bestaand** - Gebruikt voor extracted articles:
- Zelfde structuur als RSS-ingested news
- `source_key` begint met 'scrape_' voor scraping sources
- `category = 'nl_national'` voor Turkish-Dutch news

### Frontend

#### News Categories
**Locatie:** `Frontend/src/lib/routing/newsCategories.ts`

- `turks_nieuws` toegevoegd als eerste categorie in `NL_CATEGORIES`
- Verschijnt automatisch in categorie filter bar

#### News Category Filter Bar
**Locatie:** `Frontend/src/components/news/NewsCategoryFilterBar.tsx`

- Label: "Turks Nieuws"
- Geen wijzigingen nodig - categorie verschijnt automatisch

## Configuratie

### News Sources
**Locatie:** `configs/news_sources.yml`

Scraping sources worden geconfigureerd als normale news sources met:
- `key`: Begint met `scrape_` (e.g., `scrape_turksemedia_nl`)
- `category`: `nl_national` (voor filtering)
- `refresh_minutes`: 720 (12 uur, 2x per dag)
- `source_type`: Impliciet "scraper" (via key prefix)

Voorbeeld configuratie:
```yaml
- key: "scrape_turksemedia_nl"
  name: "Turkse Media"
  url: "https://turksemedia.nl/"
  language: "nl"
  category: "nl_national"
  region: "NL"
  refresh_minutes: 720
  license: "unknown"
  redistribution_allowed: true
  robots_policy: "follow"
```

## API Endpoints

### Get News with Turks Nieuws Category
```
GET /api/v1/news?feed=nl&categories=turks_nieuws
```

Response format (zelfde als andere news endpoints):
```json
{
  "items": [
    {
      "id": 123,
      "title": "Article Title",
      "snippet": "Article snippet...",
      "source": "Turkse Media",
      "published_at": "2025-12-10T08:00:00Z",
      "url": "https://turksemedia.nl/article",
      "image_url": "https://turksemedia.nl/image.jpg",
      "tags": []
    }
  ],
  "total": 9,
  "limit": 20,
  "offset": 0
}
```

## Workflow Scheduling

### GitHub Actions
**Locatie:** `.github/workflows/turkish_news_crawler.yml`

Scheduled workflow:
- **Frequency**: 2x per dag (08:00 en 20:00 UTC)
- **Jobs**:
  1. `scrape`: Runs `turkish_news_scraper_bot`
  2. `extract`: Runs `news_ai_extractor_bot` (na scrape job)

### Manual Execution

```bash
# Stage 1: Scrape websites
python -m app.workers.turkish_news_scraper_bot

# Stage 2: Extract articles with AI
python -m app.workers.news_ai_extractor_bot --limit 20
```

## AI Prompt Engineering

### System Prompt
De AI prompt is geoptimaliseerd voor news article extractie:
- Extracteert laatste 3 artikelen
- Focus op main article listings
- Parse published_at zorgvuldig (niet huidige datum)
- URLs moeten absoluut zijn
- Snippet max 200 woorden

### Prompt Variaties
Voor verschillende sites kunnen prompts worden aangepast in `NewsExtractionService._build_system_prompt()`.

## Troubleshooting

### Geen artikelen in frontend
1. Check of scraping sources correct geconfigureerd zijn in `news_sources.yml`
2. Check `news_pages_raw` tabel voor pending pages
3. Check `raw_ingested_news` voor extracted articles met `source_key LIKE 'scrape_%'`
4. Check worker runs logs voor errors

### AI extractie faalt
1. Check OpenAI API key en quota
2. Check `news_pages_raw.processing_errors` voor details
3. Check AI logs in `ai_logs` tabel
4. Valideer HTML content in `news_pages_raw.response_body`

### Duplicate artikelen
- Deduplicatie gebeurt via `ingest_hash` (source_key + url + published_at)
- Check `raw_ingested_news` voor duplicate `ingest_hash` values

### Website structuur wijzigingen
- AI extractie is robuust voor structuur wijzigingen
- Als extractie kwaliteit daalt, pas system prompt aan in `NewsExtractionService`
- Monitor `processing_errors` voor patterns

## Monitoring

### Key Metrics
- Aantal gescrapete pagina's per run
- Aantal extracted articles per run
- AI extractie success rate
- Duplicate detection rate
- Frontend engagement (clicks op artikelen)

### Database Queries

```sql
-- Check pending pages
SELECT COUNT(*) FROM news_pages_raw WHERE processing_state = 'pending';

-- Check extracted articles
SELECT COUNT(*) FROM raw_ingested_news WHERE source_key LIKE 'scrape_%';

-- Check recent scraping activity
SELECT news_source_key, COUNT(*), MAX(fetched_at)
FROM news_pages_raw
WHERE fetched_at >= NOW() - INTERVAL '24 hours'
GROUP BY news_source_key;

-- Check AI extraction errors
SELECT news_source_key, processing_errors
FROM news_pages_raw
WHERE processing_state = 'error_extract'
ORDER BY fetched_at DESC
LIMIT 10;
```

## Toekomstige Uitbreidingen

- Meer Turkse-Nederlandse nieuwssites toevoegen
- Real-time scraping (webhooks indien beschikbaar)
- Categorisatie van artikelen binnen "Turks Nieuws" (Politiek, Cultuur, etc.)
- Push notifications voor belangrijke artikelen
- Fallback naar CSS selectors als AI extractie faalt

## Gerelateerde Documentatie

- [News Feeds](news_feeds.md) - Feed types en relevance thresholds
- [News Ingest](news_ingest.md) - RSS ingest pipeline
- [News Sources](news_sources.md) - Source configuratie













