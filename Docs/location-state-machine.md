# Location State Machine

This document describes the location state machine and how locations transition through different states in the Turkish Diaspora App.

## State Overview

Locations can be in one of the following states:

- **CANDIDATE**: Raw discovered location, unreviewed. Default state for newly discovered locations.
- **PENDING_VERIFICATION**: AI classified with confidence ≥0.80 but <0.90. Awaiting further verification.
- **VERIFIED**: Approved and visible in the app. Confidence ≥0.90. Terminal state - never demoted.
- **RETIRED**: Explicitly considered not relevant / no longer valid. Terminal state - never resurrected (unless explicitly allowed).
- **SUSPENDED**: Defined in enum but not actively used by any worker. Treated as a terminal state (excluded from processing) but no worker sets locations to this state.

## State Transitions

The state machine follows this flow:

```
[NEW DISCOVERY]
    ↓
CANDIDATE (confidence_score = NULL)
    ↓
[AI Classification via verify_locations]
    ↓
    ├─→ action="ignore" → RETIRED
    │
    └─→ action="keep"
         ├─→ confidence < 0.80 → CANDIDATE (stays)
         ├─→ 0.80 ≤ confidence < 0.90 → PENDING_VERIFICATION
         └─→ confidence ≥ 0.90 → VERIFIED
              ↓
         [VERIFIED is terminal - never demoted]
```

## Components That Change State

### Discovery Workers

- **`discovery_bot`** / **`discovery_train_bot`**: Create new locations with state `CANDIDATE`
  - These workers discover locations from OSM Overpass API
  - All newly inserted locations start as `CANDIDATE`

### Admin Manual Creation

- **`POST /api/v1/admin/locations`**: Admin UI action for hand-picked additions
  - Inserts with `source = ADMIN_MANUAL` and a generated `place_id`
  - Immediately calls `update_location_classification(..., confidence_score=0.90)` to promote the record to `VERIFIED`
  - Notes include `[manual add by <admin email>]` and the action is logged via `audit_admin_action`
  - Manual entries must include valid lat/lng coordinates so they satisfy the verified filter used by the public map

### Verification Workers

- **`verify_locations`** (PRIMARY): Main verification worker that performs classification-based transitions
  - Processes both `CANDIDATE` and `PENDING_VERIFICATION` records
  - Uses `ClassifyService` to classify locations via OpenAI
  - Calls `update_location_classification()` which derives state from `action` + `confidence_score`
  - This is the **primary** worker for normal verification operations

- **`classify_bot`** (LEGACY): Legacy worker that sets `PENDING_VERIFICATION` but does not promote to `VERIFIED`
  - Maintained for backward compatibility and bulk re-classification tasks
  - Uses the same `update_location_classification()` function
  - For normal operations, prefer `verify_locations` instead

- **`task_verifier`**: Heuristically promotes locations with high confidence + Turkish cues
  - Uses `should_force_promote()` heuristic
  - Can promote directly to `VERIFIED` if confidence ≥0.90 and Turkish indicators present

## State Derivation Rules

The central function `update_location_classification()` in `Backend/services/db_service.py` derives state as follows:

- `action="ignore"` → `state="RETIRED"`
- `action="keep"` + `confidence >= 0.90` → `state="VERIFIED"`
- `action="keep"` + `0.80 <= confidence < 0.90` → `state="PENDING_VERIFICATION"`
- `action="keep"` + `confidence < 0.80` → `state="CANDIDATE"`

## No-Downgrade Rules

The system enforces protection against accidental data loss:

- **VERIFIED locations are never demoted**: Once a location reaches `VERIFIED`, it stays `VERIFIED` even if re-classified with lower confidence
- **RETIRED locations are never resurrected**: Unless `allow_resurrection=True` is explicitly passed, `RETIRED` locations cannot be promoted back to other states

## Why Locations Remain CANDIDATE

Many locations may remain in `CANDIDATE` state for legitimate reasons:

1. **Not yet classified**: No verification worker has run on them yet, or filters exclude them from processing
2. **Low confidence**: AI classification returned `action="keep"` but confidence < 0.80
3. **Worker scheduling**: Verification workers may not run frequently enough to process all candidates
4. **Geographic filters**: Workers may be configured to only process specific cities/sources

This is **expected behavior**, not a bug. The system is designed to be conservative and only promote locations with sufficient confidence.

## Central State Management

All state transitions go through `update_location_classification()` in `Backend/services/db_service.py`. This ensures:

- Consistent state derivation rules
- No-downgrade protection
- Audit trail via `last_verified_at` timestamp
- Notes field updates for traceability

Workers and admin actions should always use this function rather than directly updating the `state` column.

