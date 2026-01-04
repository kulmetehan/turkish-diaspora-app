# Changelog

All notable changes to the Turkish Diaspora App project.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-alpha] - 2025-01-XX

### Alpha Release

This marks the alpha release of the Turkish Diaspora App, ready for initial user testing and feedback.

### Added

#### Engagement Layer (EPIC-1.5)
- Referral program with XP bonuses and tracking
- Social sharing via Web Share API with clipboard fallback
- Weekly digest email automation via GitHub Actions
- Push notifications infrastructure (Web Push API with service worker)

#### Community Layer (EPIC-2.5)
- User groups: create, join, activity feeds, membership management
- Moderation tools for content and user management
- Reporting system for locations, notes, reactions, and users
- Community guidelines UI and backend integration

#### Monetization Layer (EPIC-3)
- Business accounts API with CRUD operations
- Location claiming flow with verification
- Verified badge system for claimed locations
- Premium subscriptions with Stripe integration and feature gating
- Promoted locations: one-time payment for trending and feed promotion
- Promoted news posts: one-time payment for top-of-feed placement
- Business analytics dashboard with views, engagement, and trending metrics
- Google Business Profile sync with OAuth integration

#### Documentation & Infrastructure
- Complete documentation refactor and consolidation
- Environment template standardization (`.env.template`)
- Archive structure for completed epics and legacy documentation
- CONTRIBUTING.md with development guidelines
- LICENSE file (MIT)

### Changed

- Documentation structure: organized archive for completed features
- README.md updated with alpha status and comprehensive feature list
- TypeScript type fixes: resolved all linter errors in FeedPage and SharedLinkCard components
- Code quality improvements: fixed type mismatches and improved type safety

### Fixed

- TypeScript linter errors in `Frontend/src/pages/FeedPage.tsx` (7 errors)
- TypeScript linter error in `Frontend/src/components/prikbord/SharedLinkCard.tsx` (1 error)
- Type safety issues with CurrentUser and UserAuth interfaces

## [Unreleased] (Previous)

### Added
- **Part A: Admin ↔ Frontend Count Parity + Transparency**
  - Shared filter definition module (`Backend/app/core/location_filters.py`) providing single source of truth for verified location filters
  - Admin metrics now use same filters as frontend map (state=VERIFIED, confidence>=0.80, retired excluded, coords required, bbox=Rotterdam)
  - "Filters in effect" badge in Admin dashboard showing active filter criteria
  - Backend tests for filter parity between Admin metrics and public API

- **Part B: Discovery Workflow Completes**
  - GitHub Actions workflow now prevents self-cancellation (`cancel-in-progress: false`)
  - Guard job checks for active runs before starting discovery matrix
  - Run summary step prints completed chunks/total and elapsed time
  - Documentation for discovery workflow runtime expectations and queueing behavior

- **Part C: Soft-Dedupe + Discovery KPIs**
  - Soft-dedupe logic: fuzzy duplicates now update existing records instead of skipping
  - `discovery_runs` table tracks discovery metrics per run
  - Discovery KPIs endpoint (`GET /admin/discovery/kpis?days=30`) with daily aggregates
  - Admin dashboard widget showing inserts vs dedupes vs updates over last 30 days
  - Counters tracked: discovered, inserted, deduped_place_id, deduped_fuzzy, updated_existing, failed

- Database observability improvements: periodic pg_stat_activity sampler logs highlight lingering transactions (`Backend/app/core/db_monitor.py`).
- Admin bulk-update hardened: shared transactional connection, strict payload validation, asyncpg helper fixes, and CORS-safe error responses.

### Changed
- Admin metrics verified count now matches frontend map count (uses shared filter definition)
- Discovery worker now updates existing records on fuzzy match instead of skipping
- Discovery workflow now queues runs instead of canceling active runs

### Fixed
- Admin metrics count mismatch with frontend map (now aligned using shared filter)
- Discovery workflow self-cancellation issue (now completes successfully)
- Idle `SELECT` sessions lingering in `pg_stat_activity` by refactoring asyncpg helpers, enforcing connection context managers, and adding timeouts/monitoring (TDA-107).
- Bulk admin updates returning 500 with `AttributeError` and missing CORS headers; resolved by fixing helper signatures, single-connection transactions, and global exception handling.

