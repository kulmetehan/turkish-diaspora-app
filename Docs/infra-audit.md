---
title: Infrastructure Audit
status: active
last_updated: 2025-11-04
scope: infra
owners: [tda-core]
---

# Infrastructure Audit

Snapshot of hosted services, secrets, and operational ownership for the Turkish Diaspora App.

## Services

| Service | Provider | Purpose | Notes |
| --- | --- | --- | --- |
| Backend API | Render (Web Service) | Hosts FastAPI app (`uvicorn`) | Uses `Backend/.env` variables. Configure autoscale + health checks. |
| Background workers | Render (Background Worker) | Long-running classify/verify/monitor tasks (optional) | Use same env keys as backend; schedule via Render cron if not relying on GitHub Actions. |
| Automation | GitHub Actions | Scheduled discovery/verification/monitor/alert workflows | Secrets managed at repo level (`tda_*` workflows). |
| Database | Supabase Postgres | Primary data store for locations, ai_logs, tasks | Service role key used for automation; JWT secret used by backend. |
| Auth | Supabase Auth | Email/password login for admins | Allowlist maintained via `ALLOWED_ADMIN_EMAILS`. |
| Frontend | GitHub Pages | Static hosting for Vite build (hash router) | Deployed by `frontend_deploy.yml`, Mapbox token required. |
| Maps | Mapbox | Vector tiles for frontend | Token stored as `VITE_MAPBOX_TOKEN`. |

## Secrets inventory

| Secret | Location | Rotation cadence |
| --- | --- | --- |
| `DATABASE_URL` | Render (backend + worker), GitHub Actions | Rotate via Supabase; update template + env-config. |
| `SUPABASE_JWT_SECRET` | Render backend, GitHub Actions | Rotate in Supabase settings; update `.env.template`. |
| `ALLOWED_ADMIN_EMAILS` | Render backend | Update when admin roster changes. |
| `OPENAI_API_KEY` | Render backend/worker, GitHub Actions | Rotate quarterly; optional for dry-run modes. |
| `SUPABASE_KEY` (service role) | GitHub Actions (discovery/verification) | Inherit from Supabase; protect carefully. |
| `VITE_SUPABASE_ANON_KEY` | GitHub Pages deploy secrets, local `.env` | Public but rotate alongside Supabase. |
| `VITE_MAPBOX_TOKEN` | GitHub Pages deploy secrets, local `.env` | Rotate per Mapbox policy. |
| Alert webhook | Render worker / GitHub Actions | Optional: Slack/Teams webhook. |

Keep the template (`/.env.template`) synchronized with these secrets to prevent drift.

## Monitoring & alerting

- Metrics API (`/api/v1/admin/metrics/snapshot`) + admin dashboard.
- GitHub Actions notifications on workflow failure.
- Optional Slack webhook for `tda_alert.yml` outputs.
- `overpass_calls` table for OSM mirror health.

## Compliance checks

- Confirm `OVERPASS_USER_AGENT` contains contact email and is shared across services.
- Ensure Supabase RLS policies align with worker access patterns.
- Verify Mapbox token restricted to allowed origins (localhost, GitHub Pages domain).

## Audit cadence

| Task | Frequency |
| --- | --- |
| Secret rotation (OpenAI, Supabase keys, Mapbox token) | Quarterly or upon incident |
| Workflow review (`tda_*`) | Monthly |
| Render service logs & health | Weekly |
| Supabase backup verification | Monthly |

Document findings and follow-ups in this file or link to issues for traceability.
