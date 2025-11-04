---
title: VerifyLocationsBot Worker Guide
status: active
last_updated: 2025-11-04
scope: backend
owners: [tda-core]
---

# VerifyLocationsBot

Promotes high-confidence locations from `CANDIDATE/PENDING_VERIFICATION` to `VERIFIED` using OpenAI classification results, centralized validation, and audit logging. This README supplements the full runbook (`Docs/verify-locations-runbook.md`).

## Requirements

- `DATABASE_URL` configured (Supabase Postgres)
- `OPENAI_API_KEY` available for non-dry runs
- `SUPABASE_JWT_SECRET` and `ALLOWED_ADMIN_EMAILS` set for admin endpoints
- Optional: adjust `CLASSIFY_MIN_CONF` for experiments

## Usage

```bash
cd Backend
source .venv/bin/activate

# Dry run (recommended initially)
python -m app.workers.verify_locations --limit 50 --dry-run 1

# Production run (writes to database)
python -m app.workers.verify_locations --limit 200 --dry-run 0

# Chunked execution (6 slices)
python -m app.workers.verify_locations --limit 600 --chunks 6 --chunk-index 0 --dry-run 0
```

### Flag reference

| Flag | Default | Notes |
| --- | --- | --- |
| `--limit` | `200` | Max rows processed; combined with chunking for large batches. |
| `--offset` | `0` | Legacy pagination support; usually unused when chunking. |
| `--chunks` / `--chunk-index` | `1` / `0` | Evenly split the workload across multiple executions (GitHub Actions matrix). |
| `--dry-run` | `0` | When `1`, skips writes and audit logging. |
| `--min-confidence` | `0.8` | Override the promotion threshold. |
| `--model` | default | Override OpenAI model ID. |
| `--city`, `--source` | optional | Accepted for future filtering; currently no-op (fetch query does not filter yet). |
| `--log-json` | `0` | Emit JSON logs for machine-readable output. |

## Execution flow

1. Fetch candidate rows (`state` in `CANDIDATE`, `PENDING_VERIFICATION`) ordered by `first_seen_at`.
2. Run `ClassifyService.classify` for each row (OpenAI) and validate payload with `validate_classification_payload`.
3. Persist classification via `update_location_classification`, which enforces:
   - Confidence → state mapping (`>=0.90 → VERIFIED`, `>=0.80 → PENDING_VERIFICATION`, otherwise `CANDIDATE`).
   - No downgrade of existing `VERIFIED` rows; no resurrection of `RETIRED` rows.
   - Audit log entry on success (unless dry-run).
4. Print `[PROMOTE]`, `[SKIP]`, `[ERROR]`, `[RETIRE]` summaries.
5. Return aggregate stats for automation workflows.

## Monitoring & observability

```sql
-- Recently promoted rows (last 24h)
SELECT id, name, category, confidence_score, last_verified_at
FROM locations
WHERE state = 'VERIFIED'
  AND last_verified_at >= NOW() - INTERVAL '24 hours'
ORDER BY last_verified_at DESC
LIMIT 25;

-- Promotion ratio
SELECT
  SUM(CASE WHEN state = 'VERIFIED' THEN 1 ELSE 0 END) AS verified,
  SUM(CASE WHEN state IN ('CANDIDATE','PENDING_VERIFICATION') THEN 1 ELSE 0 END) AS pending
FROM locations;

-- Audit trail for recent promotions
SELECT location_id, action_type, model_used, created_at
FROM ai_logs
WHERE action_type = 'verify_locations.classified'
ORDER BY created_at DESC
LIMIT 20;
```

## Troubleshooting quick hits

| Symptom | Check |
| --- | --- |
| Worker exits immediately with missing key error | Ensure `OPENAI_API_KEY` present or run with `--dry-run`. |
| `promoted=0` despite candidates | Inspect audit logs for `action=ignore` reasons; adjust `--min-confidence` if appropriate. |
| API still returns old data | Verify API health (`/api/v1/locations`), ensure frontend points to correct base URL, confirm worker summary printed `[PROMOTE]`. |
| GitHub Actions job fails | Review logs for OpenAI rate limits or database connectivity; rerun job with adjusted chunk index. |

## Related resources

- Runbook: [`Docs/verify-locations-runbook.md`](../../../Docs/verify-locations-runbook.md)
- Worker implementation: [`verify_locations.py`](./verify_locations.py)
- Classification helpers: [`services/classify_service.py`](../../services/classify_service.py), [`services/ai_validation.py`](../../services/ai_validation.py)
- Metrics snapshot: [`Backend/services/metrics_service.py`](../../services/metrics_service.py)
