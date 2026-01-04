# Turkish Diaspora App

> **Status**: 🚀 Alpha Release Ready  
> An AI-assisted location discovery and verification platform for Turkish communities in the Netherlands. The system continuously discovers new venues, classifies their relevance, verifies quality, and publishes curated data to an interactive map.

## Architecture at a glance

- **Backend** — FastAPI (Python 3.11) with async workers for discovery, classification, verification, monitoring, and alerting. All persistence uses Supabase Postgres via `asyncpg`.
- **Frontend** — React + Vite + TypeScript with Tailwind and shadcn/ui. Served on GitHub Pages with Mapbox GL maps and admin tooling guarded by Supabase Auth.
- **Data sources** — OSM Overpass API (discovery), OpenAI (classification/verification), Supabase (storage + metrics), Mapbox (tiles).
- **Automation** — GitHub Actions orchestrate discovery/verification runs; Render hosts backend services and long-running workers.

## Core capabilities

- **Discovery & Verification**: OSM-based grid discovery with adaptive rate limiting, AI classification, and automated verification pipeline (`CANDIDATE → VERIFIED`) with full audit trails.
- **Interactive Map**: Mapbox-based public map with location markers, search, filters, and bottom-sheet UX.
- **Engagement Layer**: Referral program, social sharing, weekly digest emails, push notifications (Web Push API).
- **Community Features**: User groups, moderation tools, reporting system, community guidelines.
- **Monetization**: Business accounts, location claiming, verified badges, premium subscriptions (Stripe), business analytics dashboard, promoted content, Google Business sync.
- **Admin Dashboard**: Metrics snapshot, location management, user administration, protected by Supabase Auth.
- **Automation**: GitHub Actions workflows for discovery, verification, monitoring, alerts, and scheduled tasks.

## Getting started

1. Follow [`QUICK_START.md`](./QUICK_START.md) to provision the backend, frontend, and optional workers locally.
2. Copy `/.env.template` to `Backend/.env` and adjust secrets as described in [`Docs/env-config.md`](./Docs/env-config.md).
3. Browse to `http://localhost:5173/#/` (public map) or `#/admin` (protected area) once both services are running.
4. Consult the runbook for day-to-day operations, cron jobs, and troubleshooting: [`Docs/runbook.md`](./Docs/runbook.md).

## Documentation index

See [`Docs/README.md`](./Docs/README.md) for a curated index grouped by topic:

- Setup & environment (env template, quick start, TDA-111 blueprint)
- Backend & data pipeline (discovery, verification, AI schemas, bots)
- Frontend UX (design system, search, map UX, QA checklists)
- Data-Ops & automation (city grids, OSM improvements, production reports)
- Observability & metrics (metrics dashboard, infra audit)
- CI/CD & deployment (Render, GitHub Pages, GitHub workflows)
- Runbooks and incident response (developer handbook, verify locations runbook)

## Repository layout

| Path | Description |
| --- | --- |
| `Backend/` | FastAPI service, workers, services, configs, reports. |
| `Frontend/` | React/Vite application (public map, admin UI, metrics dashboard). |
| `Docs/` | Living documentation (architecture, runbooks, UX guides, QA). |
| `Infra/` | Supabase SQL migrations, monitoring SQL, config YAMLs. |
| `.github/workflows/` | CI/CD automation for discovery, verification, alerts, frontend deploys. |
| `QUICK_START.md` | Condensed setup instructions. |
| `PROJECT_CONTEXT.md` | Historical project context and architectural overview. |
| `PROJECT_PROGRESS.md` | Epic/story tracker and milestone history. |

## CI/CD & hosting

- **Backend & workers** run on Render; secrets mirror `/.env.template` naming. Watch the `tda_*` workflows for scheduled jobs.
- **Frontend** builds through `frontend_deploy.yml` and is hosted on GitHub Pages (hash router for static hosting compatibility).
- **Automation workflows** (`tda_discovery.yml`, `tda_verification.yml`, `tda_monitor.yml`, `tda_alert.yml`, `tda_cleanup.yml`) execute discovery, verification, monitoring, and housekeeping tasks on schedules or manual triggers.

## Contributing

We welcome contributions! Please see [`CONTRIBUTING.md`](./CONTRIBUTING.md) for development setup, code style guidelines, and the PR process.

**Quick guidelines:**
- Open issues or questions in the repository before large changes
- Keep documentation in sync — update `Docs/env-config.md` and `Docs/README.md` when adding new services or env keys
- Run linting/tests relevant to touched areas; workers should be exercised with `--dry-run` flags locally
- For operational incidents, follow the escalation and troubleshooting guidance in the runbook

Questions? Reach out to the TDA core maintainers (`owners` in each doc front matter) or raise a discussion in the repo.

## License

See [`LICENSE`](./LICENSE) for license information.
