---
title: Automated Discovery Runs
status: active
last_updated: 2025-11-04
scope: automation
owners: [tda-core]
---

# Automated Discovery Runs

Documentation for the GitHub Actions workflows that replace the legacy Render cronjobs. These jobs execute `discovery_bot` across categories and grid chunks to keep the database stocked with fresh candidates.

## Workflows

| Workflow | Trigger | Matrix | Command |
| --- | --- | --- | --- |
| `tda_discovery.yml` | Scheduled (`0 */2 * * *`) + manual | `category` × `chunk_index` (6 chunks) | `python -m app.workers.discovery_bot --city rotterdam --categories ${{ matrix.category }} --chunks 6 --chunk-index ${{ matrix.chunk_index }}` |
| `tda_discovery_fast.yml` | Manual dispatch | Same as above but limited grids | Debug / smoke tests for discovery settings |

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

## Next steps

- Add matrices for additional cities once `Infra/config/cities.yml` contains validated grids.
- Consider reducing chunk count when targeting smaller cities to avoid idle actions.
- Keep OSM contact email up to date in `OVERPASS_USER_AGENT` and workflow env settings.
