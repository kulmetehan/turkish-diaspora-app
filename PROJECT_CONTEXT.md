---
title: Turkish Diaspora App — Project Context
status: active
last_updated: 2025-11-04
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
| Backend API | REST endpoints, admin auth, metrics snapshot, entry point for workers. | FastAPI (Python 3.11), structlog, asyncpg, Pydantic v2. |
| Workers | Discovery, classification, verification, monitoring, alerting (CLI + scheduled runs). | Async workers under `Backend/app/workers`, orchestrated by GitHub Actions + Render cron. |
| Data | Persistent storage and analytics. | Supabase Postgres, category/city YAML configs (`Infra/config`), metrics SQL (`Infra/monitoring`). |
| External services | Inputs and tooling. | OSM Overpass API, OpenAI GPT models, Mapbox vector tiles. |

### High-level data flow

1. **DiscoveryBot** pulls candidate locations from OSM Overpass using grid subdivision, respectful rate limiting, and endpoint rotation. Results land in `locations(state=CANDIDATE)`.
2. **ClassifyBot** and **VerifyLocationsBot** enrich and verify candidates via OpenAI (structured JSON) and business rules. Successful records become `VERIFIED` with confidence scores and audit logs.
3. **MonitorBot** revisits aging records, while **AlertBot** raises incidents based on error/429 thresholds.
4. **API layer** exposes `/api/v1/locations` for the public map (verified + high confidence pending), `/api/v1/admin/**` for metrics and admin operations, and dev tooling under `/dev/**`.
5. **Frontend** consumes APIs, renders Mapbox-based map/list UI, and offers admin workflows protected by Supabase email/password auth.

## Current phase (TDA-107 — Consolidation)

- ✅ Rotterdam OSM discovery production run (151+ locations) with postmortem reports.
- ✅ Automated verification pipeline (`verify_locations.py`) and admin metrics snapshot.
- ✅ Supabase-backed admin auth with hash-routed frontend build on GitHub Pages.
- 🔄 Documentation refactor (this sweep) to standardize env/config/runbooks.
- 🔜 City expansion (The Hague → Amsterdam → Utrecht) once discovery/verification runbooks are fully automated.

## Core components & directories

| Path | Highlights |
| --- | --- |
| `Backend/app/workers/` | Discovery, classify, verify, monitor, alert workers with CLI entrypoints. |
| `Backend/services/` | OSM service, OpenAI integration, metrics snapshot, audit helpers. |
| `Frontend/src/` | Map + list UI, admin routes, metrics dashboard, UI kit. |
| `Docs/` | Architecture notes, runbooks, UX guides, QA checklists, environment docs. |
| `Infra/` | Supabase SQL migrations, monitoring SQL, category/city configuration YML. |
| `.github/workflows/` | Scheduled discovery/verification pipelines, cleanup, alerts, frontend deploy. |

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
