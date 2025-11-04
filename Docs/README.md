---
title: Documentation Index
status: active
last_updated: 2025-11-04
scope: overview
owners: [tda-core]
---

# Documentation Index

Curated entry points into the Turkish Diaspora App documentation set. Each section links to the most relevant Markdown files inside the repository.

## Setup & Environment

- [`QUICK_START.md`](../QUICK_START.md) — fastest path to run backend, frontend, and workers locally.
- [`Docs/env-config.md`](./env-config.md) — canonical environment variables, secrets mapping, verification steps.
- [`Docs/TDA111 - Environment Blueprint en Config.md`](<./TDA111 - Environment Blueprint en Config.md>) — story notes for the consolidated env deliverable.
- [`README.md`](../README.md) — high-level project overview and architecture summary.

## Backend & Data Pipeline

- [`Docs/discovery-osm.md`](./discovery-osm.md) — OSM discovery provider integration and rate limiting strategy.
- [`Docs/discovery-config.md`](./discovery-config.md) — category mappings (to be updated for OSM-first configs).
- [`Docs/automation.md`](./automation.md) — GitHub Actions matrix for discovery runs.
- [`Docs/osm-discovery-improvements.md`](./osm-discovery-improvements.md) — production hardening notes.
- [`Docs/city-grid.md`](./city-grid.md) — city/district grid definitions.
- [`Backend/app/workers/README_verify_locations.md`](../Backend/app/workers/README_verify_locations.md) — verify worker CLI usage.
- [`Docs/verify-locations-runbook.md`](./verify-locations-runbook.md) — promote & surface workflow.
- [`Docs/ai-schemas.md`](./ai-schemas.md) — AI payload schemas, validation helpers.
- [`Backend/OSM_Discovery_Report_Rotterdam_Production.md`](../Backend/OSM_Discovery_Report_Rotterdam_Production.md) — example production rollout report.

## Frontend & User Experience

- [`Frontend/README.md`](../Frontend/README.md) — frontend architecture, npm scripts, deployment notes (needs update).
- [`Frontend/DEV_SETUP.md`](../Frontend/DEV_SETUP.md) — local dev checklist for the admin/metrics UI.
- [`Docs/design-system.md`](./design-system.md) — tokens, UI rules, shadcn/ui conventions.
- [`Docs/frontend-search.md`](./frontend-search.md) — bottom-sheet search and filter flows.
- [`Docs/map-ux-upgrade.md`](./map-ux-upgrade.md) — Mapbox migration plan and UX goals.
- [`Docs/qa/bottom-sheet-test.md`](./qa/bottom-sheet-test.md) — manual QA scenarios for the mobile bottom sheet.

## Observability & Metrics

- [`Infra/monitoring/metrics_dashboard.md`](../Infra/monitoring/metrics_dashboard.md) — KPI definitions and SQL sources.
- [`Docs/infra-audit.md`](./infra-audit.md) — inventory of services, secrets, and compliance checks.
- [`Docs/self-verify-loop.md`](./self-verify-loop.md) — state machine overview for automated verification cycles.

## Automation, CI/CD & Deployment

- [`GITHUB_PAGES_SETUP.md`](../GITHUB_PAGES_SETUP.md) — frontend deployment steps.
- `.github/workflows/tda_*.yml` — discovery, verification, monitor, alert, cleanup workflows (see comments inside each file).
- Render service configuration — documented across `Docs/env-config.md` and the runbook.

## Runbooks & Operations

- [`Docs/runbook.md`](./runbook.md) — primary developer handbook covering setup, cron jobs, troubleshooting.
- [`Docs/verify-locations-runbook.md`](./verify-locations-runbook.md) — focused runbook for verification & surfacing.
- [`Docs/osm-discovery-report-rotterdam.md`](./osm-discovery-report-rotterdam.md) — high-level report for the Rotterdam rollout (to merge with backend report).

## Meta & Tracking

- [`Docs/docs_inventory.md`](./docs_inventory.md) — full inventory with statuses.
- [`Docs/docs_gap_analysis.md`](./docs_gap_analysis.md) — open gaps and planned updates per doc.
- [`PROJECT_CONTEXT.md`](../PROJECT_CONTEXT.md) — historical context and architecture narrative (update pending).
- [`PROJECT_PROGRESS.md`](../PROJECT_PROGRESS.md) — roadmap / epic tracker (update pending).

Use this index as the entry point for PR reviews and onboarding; update it whenever documentation moves or new guides are added.
