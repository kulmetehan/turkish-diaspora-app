---
title: Turkish Diaspora App — Runbook
status: active
last_updated: 2025-01-15
scope: runbook
owners: [tda-core]
---

# Turkish Diaspora App — Runbook

Operational handbook for developers and operators. Covers setup, workers, automation schedules, observability, and incident response for the Turkish Diaspora App.

## 1. Scope & prerequisites

- **Stack**: FastAPI (Python 3.11), async workers, Supabase Postgres, React/Vite frontend, Mapbox GL.
- **Environments**: local development, Render (API + workers), GitHub Actions (scheduled automation).
- **Secrets**: managed via `/.env.template` → `Backend/.env`, Render environment, GitHub Actions secrets, Supabase settings.

Before following any procedure, copy the canonical template and fill in required keys:

```bash
cp .env.template Backend/.env
# edit Backend/.env → DATABASE_URL, SUPABASE_JWT_SECRET, ALLOWED_ADMIN_EMAILS, OPENAI_API_KEY (optional) etc.
```

See [`Docs/env-config.md`](./env-config.md) for the authoritative variable list and validation steps.

## 2. Local bootstrap checklist

1. **Backend**
   ```bash
   cd Backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   # health checks
   curl http://127.0.0.1:8000/health
   curl http://127.0.0.1:8000/version
   ```

2. **Frontend**
   ```bash
   cd Frontend
   npm install
   npm run dev
   # open http://localhost:5173/#/ and http://localhost:5173/#/admin
   ```

3. **Database sanity** (optional but recommended)
   ```bash
   cd Backend
   source .venv/bin/activate
   python - <<'PY'
   from services.db_service import init_db_pool
   import asyncio
   asyncio.run(init_db_pool())
   print('✅ DATABASE_URL connected')
   PY
   ```
   
   For database schema information and migration conflicts, see [`Docs/db/schema-reconciliation.md`](./db/schema-reconciliation.md).

## 3. Workers & manual operations

| Worker | Module | Typical use | Notes |
| --- | --- | --- | --- |
| Discovery | `app.workers.discovery_bot` | Fetch new candidates from OSM. | Uses OSM-only provider; configure rate limits via env vars. |
| Discovery Train | `app.workers.discovery_train_bot` | Collect training data for discovery. | Training data collection for ML improvements. |
| Classify | `app.workers.classify_bot` | Assign keep/ignore + category (OpenAI). | Respects `CLASSIFY_MIN_CONF`. Dry-run recommended for testing. |
| Reclassify Other | `app.workers.reclassify_other` | Reclassify locations with "other" category. | Bulk reclassification for miscategorized locations. |
| Verify & surface | `app.workers.verify_locations` | Promote high-confidence records to `VERIFIED`. | `--city`/`--source` flags exist but currently informational (filters handled in SQL). |
| Task Verifier | `app.workers.task_verifier` | Heuristic-based location verification. | Auto-promotes high-confidence records with Turkish cues. |
| Verification Consumer | `app.workers.verification_consumer` | Consumes verification tasks from queue. | Processes verification tasks enqueued by monitor_bot. |
| Monitor | `app.workers.monitor_bot` | Refresh `next_check_at` for stale records. | Uses env-based caps (`MONITOR_MAX_PER_RUN`). |
| Alert | `app.workers.alert_bot` | Emit alerts for error spikes, 429 bursts. | Configure webhook/channel via env vars. |
| News Ingest | `app.workers.news_ingest_bot` | Ingest news from RSS feeds. | RSS feed ingestion pipeline. |
| News Classify | `app.workers.news_classify_bot` | Classify news articles for relevance. | AI classification of ingested news. |
| News AI Extractor | `app.workers.news_ai_extractor_bot` | Extract structured data from news articles. | AI extraction for news content. |
| News Trending Scraper | `app.workers.news_trending_scraper_worker` | Scrape trending topics from X (Twitter). | X API integration for trending topics. |
| Turkish News Scraper | `app.workers.turkish_news_scraper_bot` | Scrape Turkish news sources. | Turkish news source scraping. |
| Event Scraper | `app.workers.event_scraper_bot` | Scrape events from configured sources. | Event source scraping into `event_raw`. |
| Event Page Fetcher | `app.workers.event_page_fetcher_bot` | Fetch full HTML pages for AI extraction. | Fetches event detail pages. |
| Event AI Extractor | `app.workers.event_ai_extractor_bot` | Extract structured event data via AI. | OpenAI extraction from event pages. |
| Event Enrichment | `app.workers.event_enrichment_bot` | Enrich events with AI-generated metadata. | AI enrichment for event records. |
| Event Normalization | `app.workers.event_normalization_bot` | Normalize events into candidate table. | Normalizes `event_raw` into `events_candidate`. |
| Event Geocoding | `app.workers.event_geocoding_bot` | Geocode event locations to lat/lng coordinates. | Uses Nominatim API with fallback strategy. See [`Docs/events/ES-0.10-event-geocoding.md`](./events/ES-0.10-event-geocoding.md). |
| Verify Events | `app.workers.verify_events` | Verify and promote events to public. | Promotes verified events to public API. |
| Activity Stream Ingest | `app.workers.activity_stream_ingest_worker` | Process user activities into activity stream. | Ingests check-ins, reactions, notes into activity feed. |
| Trending | `app.workers.trending_worker` | Calculate trending scores for locations. | Updates trending_locations table with scores. |
| Content Curation | `app.workers.content_curation_bot` | Curate content for feed. | Content curation for activity feed. |
| Poll Generator | `app.workers.poll_generator_bot` | Generate daily polls. | Creates daily poll questions. |
| Digest | `app.workers.digest_worker` | Generate weekly digest emails. | Weekly email digest automation. |
| Push Notifications | `app.workers.push_notifications` | Send push notifications for polls, trending, activity. | Requires VAPID keys. Use `--type` to filter notification types. |
| Promotion Expiry | `app.workers.promotion_expiry_worker` | Mark expired promotions as 'expired' status. | Runs daily to update promotion status. |
| Google Business Sync | `app.workers.google_business_sync` | Sync location data from Google Business Profiles. | Requires Google OAuth credentials. Runs periodically for opted-in businesses. |

### CLI examples

```bash
# Discovery dry run (Rotterdam, bakery only)
python -m app.workers.discovery_bot \
  --city rotterdam \
  --categories bakery \
  --limit 50 \
  --dry-run

# Classification dry run (requires OPENAI)
python -m app.workers.classify_bot --limit 25 --dry-run

# Verification dry run
python -m app.workers.verify_locations --limit 50 --dry-run 1

# Verification production run with chunking (6 slices)
python -m app.workers.verify_locations --limit 600 --chunks 6 --chunk-index 0 --dry-run 0

# Discovery run with worker run tracking (writes to worker_runs table)
python -m app.workers.discovery_bot \
  --city rotterdam \
  --worker-run-id <uuid>

# Monitor freshness (no writes)
python -m app.workers.monitor_bot --limit 200 --dry-run

# Alert bot once-off (no webhook configured)
python -m app.workers.alert_bot --once 1

# Push notifications (all types)
python -m app.workers.push_notifications --type all --dry-run 0

# Push notifications (poll only)
python -m app.workers.push_notifications --type poll --dry-run 0

# Google Business sync
python -m app.workers.google_business_sync --limit 50 --dry-run 0

# Promotion expiry (marks expired promotions)
python -m app.workers.promotion_expiry_worker

# Event geocoding (geocode event locations to lat/lng)
python -m app.workers.event_geocoding_bot --limit 50
```

### Worker output cheat sheet

- **Discovery**: Logs Overpass endpoint, results inserted, skips (duplicates). Output stored in `locations` with `state=CANDIDATE`.
- **Classification**: Prints `[KEEP|IGNORE]` decisions with confidence, logs to `ai_logs`.
- **Verify**: `[PROMOTE]`, `[SKIP]`, `[ERROR]` lines summarise action; audit logs persisted.
- **Monitor**: Reports updated `next_check_at` count and skipped terminal states.
- **Alert**: Summaries of error rate, 429 bursts, optional webhook POST status.
- **Push Notifications**: Logs sent/failed counts per notification type, writes to `push_notification_log`.
- **Google Business Sync**: Logs sync status per location, updates `google_business_sync` table.
- **Event Geocoding**: Logs `event_geocoding_success`/`event_geocoding_failed` with coordinates and country, updates `events_candidate` with `lat`/`lng`/`country`.

Refer to [`Docs/worker-runs.md`](./worker-runs.md) for run-tracking conventions and guidance on generating `worker_runs` IDs for CLI usage.

## 4. Scheduled automation

| Workflow | Schedule | Command | Secrets required |
| --- | --- | --- | --- |
| `tda_discovery.yml` | `0 */2 * * *` (every 2h) | Runs discovery for each category × chunk. | `DATABASE_URL`, `OPENAI_API_KEY` (optional), `SUPABASE_URL`, `SUPABASE_KEY`, OSM env vars. |
| `tda_discovery_fast.yml` | Manual trigger | Lightweight discovery slices (debug). | Same as above. |
| `tda_verification.yml` | `15 */6 * * *` | Batches verify locations (`verify_locations.py`). | `DATABASE_URL`, `OPENAI_API_KEY`, admin secrets. |
| `tda_monitor.yml` | `*/60 * * * *` | Monitor freshness loop. | `DATABASE_URL`. |
| `tda_alert.yml` | `*/5 * * * *` | Alert thresholds (error/429). | `DATABASE_URL`, alert webhook/channel. |
| `tda_cleanup.yml` | `0 4 * * *` | Housekeeping / backlog cleanup. | `DATABASE_URL`. |
| `frontend_deploy.yml` | On `main` push | Builds + deploys GitHub Pages site. | `VITE_*` secrets, `MAPBOX` token, GH Pages deploy key. |
| `tda_news_ingest.yml` | `*/30 * * * *` | `python -m app.workers.news_ingest_bot` | `DATABASE_URL`. |
| `tda_weekly_digest.yml` | `0 9 * * 1` (weekly Monday 09:00 UTC) | `python -m app.workers.digest_worker --once` | `DATABASE_URL`, `SMTP_*`, `FRONTEND_URL`. |
| `tda_push_notifications.yml` | `*/15 * * * *` (every 15 min) | `python -m app.workers.push_notifications --type all` | `DATABASE_URL`, `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`. |
| `tda_google_business_sync.yml` | `0 2 * * *` (daily 02:00 UTC) | `python -m app.workers.google_business_sync --limit 100` | `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`. |
| `tda_promotion_expiry.yml` | `0 0 * * *` (daily 00:00 UTC) | `python -m app.workers.promotion_expiry_worker` | `DATABASE_URL`. |

Render cron jobs (if configured) should mirror the same commands/secrets as above. Keep `.env.template` synchronized so Service → Worker → GitHub Actions share names. For NewsIngestBot specifically, create a Render cron task (or background worker) that runs `python -m app.workers.news_ingest_bot` with `DATABASE_URL` (and optional `NEWS_INGEST_*` overrides) in the worker environment.

## 5. Observability

- **Metrics snapshot**: `GET /api/v1/admin/metrics/snapshot` (requires Supabase admin JWT). Feeds admin dashboard.
- **Key KPI queries**: see `Infra/monitoring/metrics_dashboard.sql`.
- **Logs**: Workers use structlog JSON. In GitHub Actions, download artifacts or inspect step logs.
- **Alert thresholds**: Controlled via env (`ALERT_*`). Default err rate threshold = 10% over 60 minutes, Google 429 threshold kept for legacy compatibility.

### Useful SQL snippets

```sql
-- Newly discovered candidates (24h)
SELECT id, name, category, source, state, first_seen_at
FROM locations
WHERE first_seen_at >= NOW() - INTERVAL '24 hours'
ORDER BY first_seen_at DESC;

-- Verification promotion summary
SELECT state, COUNT(*)
FROM locations
GROUP BY state
ORDER BY COUNT(*) DESC;

-- AI log error rate (last 60 minutes)
SELECT COUNT(*) FILTER (WHERE is_success IS FALSE OR error_message IS NOT NULL)::float
       / NULLIF(COUNT(*), 0) AS error_rate
FROM ai_logs
WHERE created_at >= NOW() - INTERVAL '60 minutes';
```

## 6. Troubleshooting

| Symptom | Possible cause & fix |
| --- | --- |
| `RuntimeError: DATABASE_URL not set` | Ensure `Backend/.env` is loaded; run `cp .env.template Backend/.env` and populate credentials. |
| Worker exits immediately with `OPENAI_API_KEY missing` | Either supply the key or run with `--dry-run` for local testing. |
| Discovery hitting 429/504 repeatedly | Increase `DISCOVERY_SLEEP_BASE_S`, check Overpass mirrors, confirm respectful `OVERPASS_USER_AGENT`. |
| Empty map frontend | Verify backend reachable at `VITE_API_BASE_URL`, ensure verification promoted enough records (run workers). |
| Admin login fails (401/403) | Check `SUPABASE_JWT_SECRET` matches Supabase project, ensure email is in `ALLOWED_ADMIN_EMAILS`, check Supabase auth logs. |
| Metrics endpoint 503 | Database down or credentials invalid; run the DB sanity snippet and inspect Render logs. |
| Push notifications not delivered | Verify VAPID keys configured, check `push_notification_log` for errors, ensure service worker registered. |
| Stripe webhook failures | Verify `STRIPE_WEBHOOK_SECRET` matches Stripe dashboard, check webhook endpoint accessibility. |
| Google Business sync errors | Check OAuth credentials, verify token refresh logic, inspect `google_business_sync` table for error messages. |

## 7. Incident response

1. **Identify** — review GitHub Actions history, Render logs, metrics snapshot. Note timestamp, failing worker, error signatures.
2. **Stabilize** — pause offending workflow (disable schedule or set `ALERT_RUN_ONCE=1`), increase sleep/backoff if hitting rate limits.
3. **Investigate** — inspect AI logs (`ai_logs` table), worker stdout, Overpass responses.
4. **Remediate** — rerun worker in dry-run to confirm fix, re-enable schedule, commit configuration updates if needed.
5. **Communicate** — document findings in `Docs/docs_gap_analysis.md` (if docs require updates) and share summary with maintainers.

Escalation order: internal TDA core → Supabase support (for auth/db issues) → OSM community/channel (if long outage) → OpenAI support (if API outage).

## 8. References

- `Docs/env-config.md` — environment variables & secrets.
- `Docs/verify-locations-runbook.md` — verification pipeline deep dive.
- `Docs/discovery-osm.md` — provider internals and rate limiting.
- `Infra/monitoring/metrics_dashboard.md` — KPI SQL.
- `Docs/README.md` — full documentation index.

Keep this runbook updated whenever workflows, environment variables, or operational tooling change.
