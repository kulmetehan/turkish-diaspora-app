---
title: Automated Discovery Runs
status: active
last_updated: 2025-01-XX
scope: automation
owners: [tda-core]
---

# Automated Discovery Runs

Documentation for the GitHub Actions workflows that automate discovery and verification workers.

## Active Workflows

| Workflow | Trigger | Purpose | Command |
| --- | --- | --- | --- |
| `discovery-train.yml` | Scheduled (`*/30 * * * *`) + manual | Sequential discovery orchestration | `python -m app.workers.discovery_train_bot --max-jobs 1` |
| `tda_verification.yml` | Scheduled (`*/30 * * * *`) + manual | Primary verification pipeline | `python -m app.workers.verify_locations --limit 1500` |

## Deprecated Workflows

The following workflows have been **disabled** and replaced by Discovery Train:

| Workflow | Status | Reason |
| --- | --- | --- |
| `tda_discovery.yml` | **DEPRECATED** | Replaced by `discovery-train.yml` - parallel runs overload OSM API |
| `tda_discovery_fast.yml` | **DEPRECATED** | Replaced by `discovery-train.yml` - parallel runs overload OSM API |
| `tda_discovery_vlaardingen.yml` | **DEPRECATED** | Replaced by `discovery-train.yml` - parallel runs overload OSM API |
| `tda_discovery_schiedam.yml` | **DEPRECATED** | Replaced by `discovery-train.yml` - parallel runs overload OSM API |

**Migration Rationale**: The old workflows ran many `discovery_bot` instances in parallel (e.g., 54 jobs for Rotterdam: 9 categories × 6 chunks), which could overload the OSM Overpass API. Discovery Train processes jobs sequentially from the `discovery_jobs` queue, respecting rate limits and ensuring orderly execution.

See `Docs/discovery-train.md` for full documentation on the Discovery Train system.

### Secrets required

| Secret | Notes |
| --- | --- |
| `DATABASE_URL` | Supabase Postgres connection string. |
| `OPENAI_API_KEY` | Optional for discovery (kept for consistency). |
| `SUPABASE_URL`, `SUPABASE_KEY` | Service role key (if downstream services need it). |
| `OVERPASS_*`, `DISCOVERY_*`, `MAX_SUBDIVIDE_DEPTH`, `OSM_TURKISH_HINTS` | Provide overrides to match production defaults when needed. |

Secrets mirror the names in `/.env.template`. When rotating secrets, update GitHub Actions, Render services, and the template simultaneously.

## Runtime settings

Workflows provide baseline environment variables:

```yaml
DISCOVERY_RATE_LIMIT_QPS: "0.15"
DISCOVERY_SLEEP_BASE_S: "3.0"
DISCOVERY_SLEEP_JITTER_PCT: "0.20"
OVERPASS_TIMEOUT_S: "30"
DISCOVERY_MAX_RESULTS: "25"
MAX_SUBDIVIDE_DEPTH: "2"
OSM_TURKISH_HINTS: "true"
```

Adjust these via workflow overrides when preparing large city launches or reacting to rate-limit feedback.

## Monitoring jobs

- Review GitHub Actions logs (`Actions ▸ tda_discovery`) for `[NEW]`, `[SKIP]`, `[RETRY]` output.
- Inspect Overpass call metrics via `overpass_calls` table (see `Docs/osm-discovery-improvements.md`).
- Alerting handled separately (`tda_monitor.yml`, `tda_alert.yml`).

## Local dry-run before deployment

```bash
cd Backend
source .venv/bin/activate
python -m app.workers.discovery_bot \
  --city rotterdam \
  --categories restaurant \
  --limit 50 \
  --dry-run
```

Confirm expected behavior before merging changes that affect discovery parameters.

## Discovery Train

Discovery Train (`discovery-train.yml`) is the primary automated discovery mechanism:

- **Frequency**: Every 30 minutes (processes 1 job per run)
- **Queue-based**: Jobs are enqueued via `scripts/enqueue_discovery_jobs.py`
- **Sequential**: Processes jobs one at a time to respect OSM rate limits
- **Multi-city**: Supports all cities defined in `cities.yml`

To enqueue jobs for a city:
```bash
python -m scripts.enqueue_discovery_jobs --city rotterdam
```

See `Docs/discovery-train.md` for full documentation.

## Verification Pipeline

The verification workflow (`tda_verification.yml`) runs independently:

- **Frequency**: Every 30 minutes
- **Worker**: `verify_locations` (PRIMARY verification flow)
- **Limit**: 1500 records per run
- **Purpose**: Promotes CANDIDATE/PENDING_VERIFICATION to VERIFIED

This is the primary verification pipeline. The legacy `classify_bot` is now a manual tool only.

See `Docs/state-pipeline.md` and `Docs/verify-locations-runbook.md` for details.

## Adjusting Workflow Frequency

To change Discovery Train frequency, edit `.github/workflows/discovery-train.yml`:
- Cron schedule: `*/30 * * * *` (every 30 minutes)
- `--max-jobs` parameter: Increase to process multiple jobs per run

To change verification frequency, edit `.github/workflows/tda_verification.yml`:
- Cron schedule: `*/30 * * * *` (every 30 minutes)
- `--limit` parameter: Adjust based on processing capacity

## Next steps

- Monitor Discovery Train job queue size (check `discovery_jobs` table)
- Adjust `--max-jobs` if queue backlog grows
- Keep OSM contact email up to date in `OVERPASS_USER_AGENT` and workflow env settings
