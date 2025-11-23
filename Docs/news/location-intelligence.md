# NEWS – Location Intelligence Layer (N2.2)

## Overview
- Purpose: add deterministic geo signals to the news pipeline so editorial tools can filter *local (NL)* vs *origin (TR)* coverage.
- Scope: RSS ingest → AI classification → deterministic tagging → storage.
- State machine is unchanged; only metadata on `raw_ingested_news` gains new columns.

## Config Registry
- File: `configs/news_city_tags.yml`
- Structure:
  - `version`
  - `nl` / `tr` arrays containing `city_key`, `city_name`, `aliases`.
- Loader: `app.models.news_city_tags`
  - `get_aliases(country)` → `{alias: CityTag}`
  - `match_city(text)` → first matching alias (NFKD + punctuation stripping)
  - Cache reset via `clear_city_tags_cache()`
- Editing rules:
  1. Keep aliases lowercase, include common abbreviations.
  2. Align `city_key` with downstream dashboards (rotterdam, amsterdam, den_haag, etc.).
  3. Run `pytest Backend/tests/test_news_city_tags.py` after updates.

## AI Classification Enhancements
- File: `services/news_classification_service.py`
- Prompt adds guidance to output `location_mentions` alongside relevance scores/topics.
- Schema change:
  ```json
  {
    "location_mentions": [
      {"city_key": "rotterdam", "country": "nl", "confidence": 0.92}
    ]
  }
  ```
- Storage: migration `013_news_location_mentions.sql` adds `location_mentions JSONB DEFAULT '[]'`.
- `ai_logs` automatically includes the richer payload because `OpenAIService` logs the parsed model output.

## Deterministic Tagging Layer
- Library: `services/news_location_tagging.py`
  - Inputs: `title`, `summary`, `content`, AI mentions.
  - Steps:
    1. Normalize article text and look for NL/TR aliases via `match_city`.
    2. Merge with AI-provided mentions, dedupe, and compute `matches` context.
    3. Tag rules:
       - NL matches only → `local`
       - TR matches only → `origin`
       - Both / none → `none`
- Worker hook: `app/workers/news_classify_bot.py`
  - After AI success, derive `(location_tag, location_context)` and persist together with scores.
  - Context stored as JSON for future analytics (`matches[].source`, `alias`, `confidence`).
- Storage: migration `014_news_location_tags.sql` adds `location_tag TEXT` and `location_context JSONB`.

## Deployment & Ops
1. Apply migrations in order: `013` then `014`.
2. Deploy backend so workers know about new columns and prompt schema.
3. Recycle news bots (ingest + classify) to ensure new code + config loaded.
4. Monitor:
   - `worker_runs` counters for `news_classify` (should show higher payload sizes from JSONB writes).
   - `ai_logs` to confirm `location_mentions` populated.

## Troubleshooting
- **Empty `location_mentions`:** Check OpenAI prompt drift or rate limits; fallback tagging still uses text aliases.
- **False `origin` tags:** Review `configs/news_city_tags.yml` for overly broad aliases; keep them literal names only.
- **Tests fail due to `.env`:** Run `PYTHON_DOTENV_SKIP_DOTENV=1 Backend/.venv/bin/python -m pytest …` to avoid restricted env files.
- **New city needed:** Add to YAML, run loader tests, redeploy without code changes.

## Related Artifacts
- Config source: `configs/news_city_tags.yml`
- Loader tests: `Backend/tests/test_news_city_tags.py`
- Tagging tests + fixtures: `Backend/tests/test_news_location_tagging.py`, `Backend/tests/fixtures/news_location_samples.json`
- Worker regression test: `Backend/tests/test_news_classify_worker.py`
- Migrations: `Infra/supabase/013_news_location_mentions.sql`, `Infra/supabase/014_news_location_tags.sql`


