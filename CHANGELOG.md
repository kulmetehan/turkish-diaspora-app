# Changelog

All notable changes to the Turkish Diaspora App project.

## [Unreleased]

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

### Changed
- Admin metrics verified count now matches frontend map count (uses shared filter definition)
- Discovery worker now updates existing records on fuzzy match instead of skipping
- Discovery workflow now queues runs instead of canceling active runs

### Fixed
- Admin metrics count mismatch with frontend map (now aligned using shared filter)
- Discovery workflow self-cancellation issue (now completes successfully)

