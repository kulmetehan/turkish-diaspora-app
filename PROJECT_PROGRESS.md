---
title: Turkish Diaspora App — Progress Log
status: active
last_updated: 2025-01-15
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
| Jan 2025 | Engagement, Community, and Monetization layers completed: Push Notifications, User Groups, Premium Features, Business Analytics, Google Business Sync, Promoted Locations & News (EPIC-1.5, EPIC-2.5, EPIC-3: 8/8 stories done). |

## Delivered capabilities

- **Discovery**: OSM-only provider with adaptive grids, endpoint rotation, and defensive JSON parsing. Backed by `Infra/config/categories.yml` and `Infra/config/cities.yml`.
- **AI pipeline**: Classification (`classify_bot`), verification (`verify_locations.py`), audit logging, confidence thresholds, monitor/alert bots.
- **Admin experience**: Supabase email/password auth, `/admin` dashboard with metrics snapshot and location management placeholders.
- **Frontend UX**: Mapbox-based map/list hybrid, search + filters bottom sheet, UI kit on hash router for GitHub Pages.
- **Automation**: GitHub Actions workflows for discovery, verification, monitoring, cleanup, weekly digest emails, and frontend deployment.
- **Engagement features**: Referral program, social sharing (Web Share API), weekly digest email automation, push notifications (Web Push API with service worker).
- **Community features**: Moderation tools, reporting system, community guidelines UI, user groups (create, join, activity feeds).
- **Monetization features**: Business accounts API, location claiming flow, verified badge system, premium subscriptions (Stripe integration), business analytics dashboard, Google Business sync, promoted locations (trending + feed), promoted news posts (one-time payment via Stripe).

## Current focus (TDA-107 — Consolidation)

1. **Documentation refresh** — unify env/runbook references, central index (`Docs/README.md`), link integrity, updated examples. *(Completed)*
2. **Engagement layer completion** — Weekly Digest automation implemented, roadmap status synchronized. *(Completed)*
3. **Monetization layer completion** — Promoted Locations and Promoted News implemented with Stripe one-time payment integration, promotion expiry worker, and ranking logic updates. *(Completed)*
4. **City expansion readiness** — validate discovery grids + verification thresholds for The Hague and Amsterdam. *(Next)*
5. **Metrics & alerting** — cross-check SQL vs `/admin/metrics/snapshot`, ensure alert bot thresholds reflect OSM-only pipeline. *(Next)*

## Upcoming priorities

### Immediate next steps (ready to implement)

1. **City Expansion** (TDA-107 — High priority)
   - Discovery and verification for The Hague, Amsterdam, Utrecht
   - Validate discovery grids and verification thresholds
   - Production rollout following Rotterdam pattern
   - Estimated: 13 story points per city
   - Reference: `Backend/OSM_Discovery_Report_Rotterdam_Production.md`, `Infra/config/cities.yml`

### Medium-term priorities

- **Enterprise Analytics** (EPIC-4 — High priority): Large-scale dashboards for cities, governments, and enterprise partners
- **Booking System** (EPIC-4 — Medium priority): Reservation and appointment system for businesses
- **Catering/Horeca Integrations** (EPIC-4 — Medium priority): Integration with hospitality partners
- **Marketplace Infrastructure** (EPIC-4 — High priority): Marketplace for deals, coupons, products, and services

### Documentation & maintenance

- ✅ Documentation refactor completed (January 2025): API surface map, feature flags matrix, worker inventory, schema reconciliation, roadmap index.
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

## Recent changes (January 2025)

### Promoted Content Implementation (EPIC-3 Completion)
- **Promoted Locations**: One-time payment system for boosting locations in trending lists and activity feed
  - Database: `promoted_locations` table with promotion types (trending, feed, both)
  - Backend: `PromotionService` for promotion management, `StripeService` extended for payment intents
  - API: `/api/v1/promotions` endpoints for creating, listing, and canceling promotions
  - Ranking: Trending endpoint boosts promoted locations by 1.5x, activity feed prioritizes promoted content
  - Frontend: `BusinessPromotionsPage` with forms for location/news promotion, visual indicators in feeds
  - Worker: `promotion_expiry_worker.py` runs daily at 00:00 UTC via GitHub Actions to mark expired promotions
  - Documentation: Added to `Docs/env-config.md` (pricing config), `Docs/runbook.md` (worker schedule)

- **Promoted News**: One-time payment system for promoting news posts at top of feed
  - Database: `promoted_news` table linked to business accounts
  - Backend: Integrated with existing news feed, promotion service handles lifecycle
  - API: Unified promotion endpoints support both locations and news
  - Ranking: News feed shows promoted posts first, then regular news
  - Frontend: Promotion form and management UI integrated with business account flow

### Weekly Digest Email Automation
- Created GitHub Actions workflow: `.github/workflows/tda_weekly_digest.yml`
- Schedule: Weekly on Monday 09:00 UTC
- Worker: `Backend/app/workers/digest_worker.py` (fully implemented)
- Email service: `Backend/services/email_service.py` (SMTP-based)
- Documentation: Added to `Docs/runbook.md` scheduled automation section

### Roadmap Status Updates
- **EPIC-1.5 (Engagement Layer)**: Status → "Done" (4/4 stories done)
  - ✅ Referral Program — Done
  - ✅ Social Sharing UX — Done (Web Share API implementation)
  - ✅ Weekly Digest Email — Done (automation complete)
  - ✅ Push Notifications — Done (Web Push API with service worker, notification workers)
- **EPIC-2.5 (Community Layer)**: Status → "Done" (4/4 stories done)
  - ✅ Moderation Tools — Done
  - ✅ Reporting System — Done
  - ✅ Community Guidelines — Done (UI + backend)
  - ✅ User Groups — Done (create, join, activity feeds, membership management)
- **EPIC-3 (Monetization Layer)**: Status → "Done" (8/8 stories done)
  - ✅ Business Accounts API — Done
  - ✅ Location Claiming Flow — Done
  - ✅ Verified Badge System — Done
  - ✅ Premium Features — Done (Stripe integration, subscription management, feature gating)
  - ✅ Promoted Locations — Done (trending + feed promotion with one-time payment via Stripe)
  - ✅ Promoted News — Done (business-created news posts with one-time payment via Stripe)
  - ✅ Business Analytics Dashboard — Done (overview, per-location, engagement, trending metrics)
  - ✅ Google Business Sync — Done (OAuth flow, sync worker, status tracking)

## Reference documents

- Architecture overview — [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md)
- Roadmap & backlog — [`Docs/Roadmap_Backlog.md`](./Docs/Roadmap_Backlog.md)
- Roadmap index — [`Docs/roadmap/index.md`](./Docs/roadmap/index.md)
- Runbook (operations) — [`Docs/runbook.md`](./Docs/runbook.md)
- API reference — [`Docs/api/api-surface-map.md`](./Docs/api/api-surface-map.md)
- Feature flags — [`Docs/ops/feature-flags.md`](./Docs/ops/feature-flags.md)
- Database schema — [`Docs/db/schema-reconciliation.md`](./Docs/db/schema-reconciliation.md)
- Metrics snapshot — [`Infra/monitoring/metrics_dashboard.md`](./Infra/monitoring/metrics_dashboard.md)
- Environment guide — [`Docs/env-config.md`](./Docs/env-config.md)
- Documentation inventory — [`Docs/docs_inventory.md`](./Docs/docs_inventory.md)

Keep this progress log updated whenever an epic closes, new city expansion begins, or major architectural changes occur.
