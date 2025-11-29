---
title: Environment Config Guide
status: active
last_updated: 2025-11-12
scope: setup
owners: [tda-core]
---

# Environment Config Guide

**Purpose** — Provide a single source of truth for configuring the Turkish Diaspora App across local machines, Render services, and Supabase. Use this guide together with the application runbook and `.env.template` in the repository root.

## File Map

| Location | Purpose |
| --- | --- |
| `/.env.template` | Canonical template for backend + worker variables and Vite keys. Never commit secrets. |
| `Backend/.env` | Local backend + worker configuration (copy from template). Loaded automatically by FastAPI and workers. |
| `Frontend/.env.development` | Optional override for Vite dev server; include only `VITE_*` keys. |
| Render → *Environment* | Production/staging secrets for the FastAPI service and background workers. |
| Supabase → *Project Settings ▸ API* | Source for JWT secret and anon/public keys. |

**Quick start**

```bash
# From repo root
cp .env.template Backend/.env
# (optional) create Frontend/.env.development and copy the VITE_* section
```

## Backend & Workers Variables

The backend and workers read their configuration from `Backend/.env`. All keys are listed in the template. Most deployments only need to adjust the highlighted ones below:

| Key | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | ✅ | Supabase Postgres connection string (use the `postgresql+asyncpg://` form for asyncpg). |
| `SUPABASE_JWT_SECRET` | ✅ | Server-side secret used to validate Supabase admin JWTs (`Settings ▸ API ▸ JWT secret`). |
| `ALLOWED_ADMIN_EMAILS` | ✅ | Comma-separated allowlist for admin accounts (e.g. `ops@example.com,cto@example.com`). |
| `OPENAI_API_KEY` | ✅ for AI features | Required for classify/verify workers and `/dev/ai/*` endpoints. Leave empty to disable AI entrypoints. |
| `OPENAI_MODEL` | optional | Defaults to `gpt-4.1-mini`. Override for experiments. |
| `APP_VERSION` | optional | Displayed by `/version`. Useful for tagging deployments. |
| `ENVIRONMENT` | optional | `local`, `dev`, `staging`, or `prod`. Dev endpoints are only available when set to a dev-like value. |

### Database connection tuning

| Key | Default | Notes |
| --- | --- | --- |
| `DB_POOL_MIN_SIZE` | `1` | Minimum size for the asyncpg pool. Keep `1` locally; raise gradually if the Render instance has spare CPU. |
| `DB_POOL_MAX_SIZE` | `4` | Maximum pool size. Start at `4` for production; increase only after monitoring Supabase load. |
| `DEFAULT_QUERY_TIMEOUT_MS` | `30000` | Fallback timeout used for all database calls. Lower temporarily to reproduce timeout handling. |
| `STATEMENT_TIMEOUT_MS` | `30000` | Passed to Postgres to cancel long-running statements. |
| `IDLE_IN_TX_TIMEOUT_MS` | `60000` | Terminates connections left idle in a transaction. |
| `LOCK_TIMEOUT_MS` | `5000` | Abort when waiting too long for a lock (helps avoid stuck bulk updates). |

> **Reminder:** add the five new keys to Render and `.env` files so the backend, workers, and automated bulk operations share the same limits.

### Discovery & OSM tuning

These values control `OsmPlacesService` and `discovery_bot`. Adjust only if you hit rate limits or need finer-grained discovery.

| Key | Default | Notes |
| --- | --- | --- |
| `OVERPASS_USER_AGENT` | `TurkishDiasporaApp/1.0 (contact: …)` | Required to comply with Overpass API ToS — use a real contact email. |
| `DISCOVERY_RATE_LIMIT_QPS` | `0.15` | Max queries per second shared across workers. |
| `DISCOVERY_SLEEP_BASE_S` / `DISCOVERY_SLEEP_JITTER_PCT` | `3.0` / `0.20` | Sleep between calls with jitter. Increase during production throttling. |
| `DISCOVERY_BACKOFF_SERIES` | `20,60,180,420` | Seconds to wait after repeated failures. |
| `OVERPASS_TIMEOUT_S` | `30` | HTTP timeout in seconds. |
| `DISCOVERY_MAX_RESULTS` | `25` | Max elements returned per Overpass query. |
| `MAX_SUBDIVIDE_DEPTH` | `2` | Quadtree subdivision depth for dense grids. |
| `OSM_TURKISH_HINTS` | `true` | Enables additional filters for Turkish keywords. |
| `OSM_LOG_QUERIES`, `OSM_TRACE` | `false`, `0` | Debug logging switches (verbose; disable in production). |

### Classification, Monitor, and Alert settings

| Area | Keys | Purpose |
| --- | --- | --- |
| Classification | `CLASSIFY_MIN_CONF` | Minimum confidence for keep/ignore decisions. Workers still persist the raw confidence for analytics. |
| Monitor bot | `MONITOR_MAX_PER_RUN`, `MONITOR_BOOTSTRAP_BATCH` | Batch sizes for freshness checks and bootstrap runs. |
| Alert bot | `ALERT_CHECK_INTERVAL_SECONDS`, `ALERT_ERR_RATE_THRESHOLD`, `ALERT_ERR_RATE_WINDOW_MINUTES`, `ALERT_GOOGLE429_THRESHOLD`, `ALERT_GOOGLE429_WINDOW_MINUTES`, `ALERT_WEBHOOK_URL`, `ALERT_CHANNEL`, `ALERT_RUN_ONCE` | Tune the alert cadence and thresholds. Supply webhook/channel when sending notifications to Slack or another service. |

### News ingest settings

| Key | Default | Notes |
| --- | --- | --- |
| `NEWS_INGEST_TIMEOUT_S` | `15` | HTTP timeout for RSS downloads. Raise cautiously if large feeds frequently time out. |
| `NEWS_INGEST_MAX_CONCURRENCY` | `5` | Max concurrent RSS requests. Keep low to avoid hammering publishers; Render cron and GitHub Actions share the same limit. |

## Frontend (Vite) Variables

Create `Frontend/.env.development` (or `.env.production`) when you need to override defaults:

| Key | Required | Description |
| --- | --- | --- |
| `VITE_API_BASE_URL` | ✅ | Base URL of the FastAPI backend. Required for all environments. |
| `VITE_MAPBOX_TOKEN` | ✅ for live maps | Publishable Mapbox token for Map GL tiles. Leave blank to disable map rendering. |
| `VITE_MAPBOX_STYLE` | optional | Mapbox style URL for all maps. Default: `"mapbox://styles/mapbox/standard"`. Override to use a different Mapbox style (e.g., `"mapbox://styles/mapbox/streets-v12"` or `"mapbox://styles/mapbox/light-v11"`). See `Docs/mapbox-style-config.md` for change guidelines. |
| `VITE_SUPABASE_URL` | ✅ | Supabase project URL for admin login. |
| `VITE_SUPABASE_ANON_KEY` | ✅ | Supabase anon/public key used by the frontend. |

> **Tip:** keep frontend `.env` files scoped to `VITE_*` variables so sensitive backend keys never leak into the browser bundle.

## Render & Supabase Checklist

1. **Render (Backend service)**
   - Copy all backend keys from `Backend/.env`.
   - Double-check `OVERPASS_USER_AGENT` uses a production contact address.
   - Set `ENVIRONMENT=prod` to disable dev-only endpoints.
   - Optional: pin `APP_VERSION` to the git SHA deployed.

2. **Render (Background workers)**
   - Reuse the same variable set as the backend service.
   - Workers launched by GitHub Actions also need `DATABASE_URL`, `OPENAI_API_KEY`, and OSM settings via workflow secrets.

3. **Supabase**
   - Retrieve `SUPABASE_JWT_SECRET` (Settings ▸ API ▸ JWT settings).
   - Copy the anon/public keys for Vite (`VITE_SUPABASE_ANON_KEY`).
   - Ensure Row Level Security policies align with worker access needs.

4. **GitHub Actions Secrets**
   - `DATABASE_URL`, `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY` (service role) are required for the discovery and verification workflows.
   - Keep secrets synchronized after rotations.

## Verification Steps

After editing `.env` or rotating secrets, run the following smoke checks:

```bash
# Backend health
cd Backend
source .venv/bin/activate
uvicorn app.main:app --reload
# Expect: http://127.0.0.1:8000/health -> {"status": "ok"}

# Discovery bot dry run (reads Overpass config)
python -m app.workers.discovery_bot --city rotterdam --categories bakery --limit 5 --dry-run

# Verify locations dry run (requires OpenAI + admin secrets)
python -m app.workers.verify_locations --limit 5 --dry-run 1

# Metrics endpoint (uses Supabase JWT secret)
curl -s http://127.0.0.1:8000/api/v1/admin/metrics/snapshot \
  -H "Authorization: Bearer <supabase-admin-jwt>"
```

If any command fails, re-check the corresponding section in `/.env.template` and confirm the value is present in the active environment.

## Related Documents

- `Docs/runbook.md` — full developer handbook covering setup, workers, cron jobs, and troubleshooting.
- `Docs/TDA111 - Environment Blueprint en Config.md` — historical blueprint; keep aligned with this guide.
- `.env.template` — living template; update it whenever new keys are introduced.
