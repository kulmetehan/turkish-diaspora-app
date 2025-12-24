---
title: Location State Pipeline
status: active
last_updated: 2025-01-15
scope: backend, workers, data-quality
owners: [tda-core]
---

# Location State Pipeline

This document describes the location state machine, which workers interact with it, and how to prevent records from getting stuck in intermediate states.

## State Machine

The location state machine has five states:

```
CANDIDATE → PENDING_VERIFICATION → VERIFIED
                ↓
             RETIRED
                ↑
            SUSPENDED (from VERIFIED)
```

### State Definitions

- **CANDIDATE**: Raw discovered location, unreviewed. All new discoveries start here.
- **PENDING_VERIFICATION**: AI classified with confidence ≥0.80 but <0.90. Borderline cases that need review.
- **VERIFIED**: Approved and visible in the app. Requires confidence ≥0.90 and action="keep".
- **RETIRED**: Explicitly rejected (action="ignore") or no longer valid. Not visible in app.
- **SUSPENDED**: Temporarily hidden (e.g., by monitor_bot if location becomes stale). Can be reactivated.

## State Transitions

### Canonical Function: `update_location_classification()`

**Location**: `Backend/services/db_service.py::update_location_classification()`

This is the **single source of truth** for state transitions. All workers must use this function.

**Transition Rules:**

| Input | Output State |
|-------|--------------|
| `action="ignore"` | `RETIRED` |
| `action="keep"` + `confidence ≥ 0.90` | `VERIFIED` |
| `action="keep"` + `0.80 ≤ confidence < 0.90` | `PENDING_VERIFICATION` |
| `action="keep"` + `confidence < 0.80` | `CANDIDATE` |

**No-Downgrade Rules:**
- `VERIFIED` → Never demoted (always stays `VERIFIED`)
- `RETIRED` → Never resurrected (unless `allow_resurrection=True`)

## Worker Responsibilities

### DiscoveryBot
- **Input**: None (creates new records)
- **Output**: `CANDIDATE`
- **File**: `Backend/app/workers/discovery_bot.py`
- **Notes**: All discovered locations start as `CANDIDATE` (line 160)

### VerifyLocationsBot (PRIMARY)
- **Input**: `CANDIDATE`, `PENDING_VERIFICATION`
- **Output**: `VERIFIED` (conf ≥0.90), `PENDING_VERIFICATION` (0.80≤conf<0.90), `CANDIDATE` (conf<0.80), `RETIRED` (action="ignore")
- **File**: `Backend/app/workers/verify_locations.py`
- **Notes**: **This is the primary verification flow**. Processes both CANDIDATE and PENDING_VERIFICATION records (line 93). Uses AI classification via `ClassifyService`.

### ClassifyBot (LEGACY)
- **Input**: `CANDIDATE`, `PENDING_VERIFICATION`
- **Output**: `PENDING_VERIFICATION` (conf ≥0.80), `CANDIDATE` (conf <0.80), `RETIRED` (action="ignore")
- **File**: `Backend/app/workers/classify_bot.py`
- **Notes**: **Legacy tool for bulk re-classification**. Not used in normal operations. Prefer `verify_locations` for new workflows.

### TaskVerifier
- **Input**: `CANDIDATE`, `PENDING_VERIFICATION` (with conf ≥0.90)
- **Output**: `VERIFIED` (auto-promote heuristic), or stamps `last_verified_at`
- **File**: `Backend/app/workers/task_verifier.py`
- **Notes**: Heuristic-based auto-promotion (no AI call). Only promotes high-confidence records with Turkish cues.

### MonitorBot
- **Input**: `VERIFIED`
- **Output**: `VERIFIED` (updates `next_check_at`, enqueues verification tasks)
- **File**: `Backend/app/workers/monitor_bot.py`
- **Notes**: Monitors freshness of verified locations. Updates `next_check_at` and enqueues verification tasks. Does NOT set locations to SUSPENDED. SUSPENDED is a terminal state defined in the enum but not actively used by any worker.

## Preventing Stuck Records

### Common Scenarios

**1. CANDIDATE never classified**
- **Cause**: `verify_locations` or `classify_bot` not run for certain sources/cities
- **Prevention**: Ensure `verify_locations` processes all CANDIDATE records regardless of source
- **Detection**: Stale candidate metrics (see below)

**2. PENDING_VERIFICATION never promoted**
- **Cause**: Records with 0.80 ≤ confidence < 0.90 stay in PENDING_VERIFICATION
- **Prevention**: `verify_locations` re-classifies PENDING_VERIFICATION records, should eventually promote if confidence increases
- **Detection**: Monitor PENDING_VERIFICATION backlog (>100 records older than 7 days)

**3. OSM vs Google pipeline mismatch**
- **Cause**: Workers filter by `source='GOOGLE_PLACES'`, excluding OSM records
- **Prevention**: `verify_locations` does NOT filter by source by default (line 93)
- **Detection**: Check stale candidates grouped by source

### Stale Candidate Metrics

The metrics service includes `stale_candidates_count`:

- Counts `CANDIDATE` records older than N days (default 7)
- Grouped by `source` and optionally by `city` (via bbox)
- Surfaces in admin dashboard for monitoring

**Alert threshold**: If stale CANDIDATE count > 100, highlight in dashboard.

## Best Practices

### For New Workers

If creating a new worker that interacts with locations:

1. **Always use `update_location_classification()`** - Don't write state directly
2. **Respect no-downgrade rules** - Never demote VERIFIED, never resurrect RETIRED
3. **Log state transitions** - Use structured logging with `state_before` and `state_after`
4. **Handle errors gracefully** - Stamp `last_verified_at` even on errors to avoid hot loops

### For Admin Actions

- Use admin API endpoints that call `update_location_classification()`
- For manual overrides, use `allow_resurrection=True` only when explicitly needed
- Document reason for state changes in `notes` field

## Monitoring

### Key Metrics

- **Stale CANDIDATE count**: Records in CANDIDATE older than 7 days
- **PENDING_VERIFICATION backlog**: Records in PENDING_VERIFICATION older than 7 days
- **State distribution**: Count of records per state (for health checks)

### Queries

```sql
-- Stale candidates by source
SELECT source, COUNT(*) as stale_count
FROM locations
WHERE state = 'CANDIDATE'
  AND first_seen_at < NOW() - INTERVAL '7 days'
GROUP BY source;

-- PENDING_VERIFICATION backlog
SELECT COUNT(*) as pending_count
FROM locations
WHERE state = 'PENDING_VERIFICATION'
  AND last_verified_at < NOW() - INTERVAL '7 days';

-- State distribution
SELECT state, COUNT(*) as count
FROM locations
GROUP BY state
ORDER BY count DESC;
```

## Troubleshooting

**Many records stuck in CANDIDATE:**
1. Check if `verify_locations` is running regularly
2. Verify `verify_locations` doesn't filter by source/city incorrectly
3. Check for errors in `verify_locations` logs
4. Review stale candidate metrics in admin dashboard

**PENDING_VERIFICATION backlog:**
1. Ensure `verify_locations` processes PENDING_VERIFICATION (it does by default)
2. Check confidence thresholds - may need to adjust `verify_min_conf` in `ai_config`
3. Consider running `verify_locations` with lower `--min-confidence` to process borderline cases

**VERIFIED locations disappearing:**
1. Check `monitor_bot` - may be suspending stale locations
2. Verify no-downgrade rule is working (VERIFIED should never be demoted)
3. Check for manual admin overrides that may have changed state







