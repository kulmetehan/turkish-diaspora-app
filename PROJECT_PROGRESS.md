---
title: Turkish Diaspora App — Progress Log
status: active
last_updated: 2025-11-04
scope: overview
owners: [tda-core]
---

# Turkish Diaspora App — Progress Log

Tracks major epics, delivered stories, and near-term roadmap items. Use this document to understand project maturity and communicate status to stakeholders.

## Timeline highlights

| Period | Milestone |
| --- | --- |
| Q2 2025 | Monorepo established (`Backend`, `Frontend`, `Docs`, `Infra`) with Supabase schema and FastAPI skeleton. |
| Q3 2025 | OSM discovery pipeline, AI classification service, and verification bots delivered (TDA-7/8/10/11). |
| Oct 2025 | Rotterdam production rollout (151+ OSM OVERPASS discoveries) + VerifyLocationsBot automation (TDA-110). |
| Nov 2025 | Documentation consolidation (this audit), environment template standardization, metrics snapshot hardening. |

## Delivered capabilities

- **Discovery**: OSM-only provider with adaptive grids, endpoint rotation, and defensive JSON parsing. Backed by `Infra/config/categories.yml` and `Infra/config/cities.yml`.
- **AI pipeline**: Classification (`classify_bot`), verification (`verify_locations.py`), audit logging, confidence thresholds, monitor/alert bots.
- **Admin experience**: Supabase email/password auth, `/admin` dashboard with metrics snapshot and location management placeholders.
- **Frontend UX**: Mapbox-based map/list hybrid, search + filters bottom sheet, UI kit on hash router for GitHub Pages.
- **Automation**: GitHub Actions workflows for discovery, verification, monitoring, cleanup, and frontend deployment.

## Current focus (TDA-107 — Consolidation)

1. **Documentation refresh** — unify env/runbook references, central index (`Docs/README.md`), link integrity, updated examples. *(In progress)*
2. **City expansion readiness** — validate discovery grids + verification thresholds for The Hague and Amsterdam. *(Next)*
3. **Metrics & alerting** — cross-check SQL vs `/admin/metrics/snapshot`, ensure alert bot thresholds reflect OSM-only pipeline. *(Next)*

## Upcoming priorities

- Finalize doc refactor (runbook, worker guides, design system, CI/CD notes).
- Dry-run discovery/verification on next city grid with new env template.
- Update frontend documentation (remove Vite boilerplate, document admin flows, QA scenarios).
- Confirm Render/GitHub Actions secrets post-rotation using new template.

## Dependencies & risks

| Risk | Mitigation |
| --- | --- |
| Overpass API availability | Continue endpoint rotation, monitor 429/5xx bursts via alert bot, maintain contact-friendly user agent. |
| OpenAI cost spikes | Support dry-run mode, allow optional `OPENAI_API_KEY`, monitor metrics snapshot for usage. |
| Documentation drift | Adopt single source (`Docs/README.md`, `.env.template`), enforce updates in PR checklist. |
| Secrets divergence | Keep `/.env.template` synchronized and referenced across Render, GitHub Actions, Supabase. |

## Reference documents

- Architecture overview — [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md)
- Runbook (operations) — [`Docs/runbook.md`](./Docs/runbook.md)
- Metrics snapshot — [`Infra/monitoring/metrics_dashboard.md`](./Infra/monitoring/metrics_dashboard.md)
- Environment guide — [`Docs/env-config.md`](./Docs/env-config.md)
- Documentation inventory — [`Docs/docs_inventory.md`](./Docs/docs_inventory.md)

Keep this progress log updated whenever an epic closes, new city expansion begins, or major architectural changes occur.
