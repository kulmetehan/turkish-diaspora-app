---
title: Turkish Diaspora App — Project Context
status: active
last_updated: 2025-01-15
scope: overview
owners: [tda-core]
---

# Turkish Diaspora App — Project Context

A concise narrative of the platform: what it does, how it is architected, and the current phase of delivery. Use this document to onboard new contributors or align stakeholders before diving into detailed runbooks and specs.

## Mission

Deliver a continuously updated map of Turkish-oriented businesses in Dutch cities by combining open data discovery (OSM), AI-assisted classification/verification, and curated presentation layers (admin + public UI). The initial production rollout focused on Rotterdam with plans to expand to The Hague, Amsterdam, and Utrecht.

## System Architecture

| Layer | Responsibilities | Key tech |
| --- | --- | --- |
| Frontend | Public map, admin dashboard, metrics UI, Supabase-authenticated routes. | React 19 + Vite, Tailwind, shadcn/ui, Mapbox GL, Supabase JS. |
| Backend API | REST endpoints, admin auth, metrics snapshot, entry point for workers. | FastAPI (Python 3.11), structlog, asyncpg, Pydantic v2. Routers in `Backend/api/routers/`, mounted via `Backend/app/main.py`. |
| Workers | Discovery, classification, verification, monitoring, news, events, engagement, business (CLI + scheduled runs). | 32+ async workers under `Backend/app/workers`, orchestrated by GitHub Actions + Render cron. |
| Data | Persistent storage and analytics. | Supabase Postgres, category/city YAML configs (`Infra/config`), metrics SQL (`Infra/monitoring`). |
| External services | Inputs and tooling. | OSM Overpass API, OpenAI GPT models, Mapbox vector tiles. |

### High-level data flow

1. **Discovery workers** (`discovery_bot`, `discovery_train_bot`) pull candidate locations from OSM Overpass using grid subdivision, respectful rate limiting, and endpoint rotation. Results land in `locations(state=CANDIDATE)`.
2. **Verification workers** (`verify_locations`, `classify_bot`, `task_verifier`) enrich and verify candidates via OpenAI (structured JSON) and business rules. Successful records become `VERIFIED` with confidence scores and audit logs.
3. **Monitoring workers** (`monitor_bot`, `alert_bot`) revisit aging records and raise incidents based on error/429 thresholds.
4. **News pipeline workers** (`news_ingest_bot`, `news_classify_bot`, `news_ai_extractor_bot`, `news_trending_scraper_worker`) ingest, classify, and process news from RSS feeds and Turkish news sources.
5. **Events pipeline workers** (`event_scraper_bot`, `event_page_fetcher_bot`, `event_ai_extractor_bot`, `event_enrichment_bot`, `event_normalization_bot`, `event_geocoding_bot`, `verify_events`) scrape, extract, enrich, normalize, and verify events from configured sources.
6. **Engagement workers** (`activity_stream_ingest_worker`, `trending_worker`, `digest_worker`, `push_notifications`, `poll_generator_bot`) process user activities, calculate trending scores, send notifications, and generate content.
7. **Business workers** (`google_business_sync`, `promotion_expiry_worker`) sync business data and manage promotions.
8. **API layer** exposes `/api/v1/locations` for the public map (verified + high confidence pending), `/api/v1/admin/**` for metrics and admin operations, `/api/v1/business/**` for business features, and dev tooling under `/dev/**`.
9. **Frontend** consumes APIs, renders Mapbox-based map/list UI, and offers admin workflows protected by Supabase email/password auth.

## Current phase (TDA-107 — Consolidation)

- ✅ Rotterdam OSM discovery production run (151+ locations) with postmortem reports.
- ✅ Automated verification pipeline (`verify_locations.py`) and admin metrics snapshot.
- ✅ Supabase-backed admin auth with hash-routed frontend build on GitHub Pages.
- ✅ Engagement, Community, and Monetization layers completed (EPIC-1.5, EPIC-2.5, EPIC-3: all stories done).
- ✅ Documentation refactor completed - standardized env/config/runbooks, added API reference, feature flags matrix, worker inventory.
- 🔜 City expansion (The Hague → Amsterdam → Utrecht) once discovery/verification runbooks are fully automated.

## Core components & directories

| Path | Highlights |
| --- | --- |
| `Backend/api/routers/` | All API routers (public, admin, community, business, dev) - 50+ routers. |
| `Backend/app/workers/` | 32+ workers: discovery, classification, verification, monitoring, news pipeline, events pipeline, engagement, business operations. |
| `Backend/services/` | OSM service, OpenAI integration, metrics snapshot, audit helpers, business services. |
| `Frontend/src/` | Map + list UI, admin routes, metrics dashboard, UI kit, business pages. |
| `Docs/` | Architecture notes, runbooks, UX guides, QA checklists, environment docs, API reference. |
| `Infra/` | Supabase SQL migrations, monitoring SQL, category/city configuration YML. |
| `.github/workflows/` | Scheduled discovery/verification pipelines, cleanup, alerts, frontend deploy, news/events/engagement automation. |

## Operational touchpoints

- **Metrics & observability** — `/api/v1/admin/metrics/snapshot` feeds the admin dashboard; `Infra/monitoring/metrics_dashboard.sql` keeps KPIs consistent.
- **Secrets & configuration** — `/.env.template` is the source of truth; environment mapping lives in `Docs/env-config.md`.
- **CI/CD** — GitHub Actions drive worker automation (`tda_discovery.yml`, `tda_verification.yml`, etc.) and frontend deploys (`frontend_deploy.yml`). Render hosts the API + long-running workers.
- **Runbooks** — `Docs/runbook.md` (full operational handbook) and `Docs/verify-locations-runbook.md` (focused on promotion pipeline) are the primary incident response resources.

## Stakeholders & next steps

- **Maintainers**: TDA core team (see `owners` in each doc front matter).
- **Immediate goals**:
  - Finish documentation refactor (link integrity, updated examples, consistent front matter).
  - Validate discovery + verification bots for the next city grid.
  - Refresh metrics SQL and dashboard with current schema references.
- **Risks**: Overpass API rate limits, OpenAI cost spikes, Supabase credential rotation, documentation drift (being addressed in this audit).

Keep this context document updated whenever architecture, hosting, or strategic focus changes. Link back here from PRs introducing new subsystems or external integrations.
