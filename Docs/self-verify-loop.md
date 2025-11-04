---
title: Self-Verifying AI Loop
status: active
last_updated: 2025-11-04
scope: data-ops
owners: [tda-core]
---

# Self-Verifying AI Loop

Original concept for combining classification and verification into a single autonomous loop. Current implementation uses separate workers (`classify_bot` + `verify_locations.py`) executed sequentially via automation. This document captures the intended behaviour and current state.

## Goals

- Automatically process new `CANDIDATE` records end-to-end with minimal manual intervention.
- Promote high-confidence Turkish businesses to `VERIFIED` while maintaining audit trails.
- Schedule continuous re-verification via Monitor + Alert bots.

## Current implementation (2025-11)

1. **Discovery** (`discovery_bot`) inserts candidates.
2. **Classification** (`classify_bot`) assigns keep/ignore, category, confidence.
3. **Verification** (`verify_locations.py`) promotes eligible rows and logs audits.
4. **Monitor/Alert** ensure stale items are revisited and errors surfaced.

The proposed combined worker (`self_verify_bot`) has not been implemented; sequential bots remain the production workflow.

## Proposed combined flow (future work)

```
CANDIDATE → classify (OpenAI) → validate → 
  if keep && confidence ≥ threshold → upsert classification → verify → audit
  else → mark skipped / adjust confidence
```

Potential enhancements:

- Share one OpenAI call for classify + verify reasoning (cost reduction).
- Batch operations with circuit breaker when OpenAI fails repeatedly.
- Record richer telemetry (reasons, evidence) for admin review.

## Next steps

- Decide whether combined worker is still required or if sequential automation suffices.
- If built, reuse validation helpers from `services/ai_validation` and metrics logging from `verify_locations`.
- Update this document and runbook once implementation is in place.

For day-to-day operations refer to `Docs/runbook.md` and `Docs/verify-locations-runbook.md`.
