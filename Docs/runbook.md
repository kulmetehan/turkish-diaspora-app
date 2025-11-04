---
title: Turkish Diaspora App — Runbook
status: active
last_updated: 2025-11-04
scope: runbook
owners: [tda-core]
---

# Turkish Diaspora App — Runbook

Operational handbook for developers and operators. Covers setup, workers, automation schedules, observability, and incident response for the Turkish Diaspora App.

## 1. Scope & prerequisites

- **Stack**: FastAPI (Python 3.11), async workers, Supabase Postgres, React/Vite frontend, Mapbox GL.
- **Environments**: local development, Render (API + workers), GitHub Actions (scheduled automation).
- **Secrets**: managed via `/.env.template` → `Backend/.env`, Render environment, GitHub Actions secrets, Supabase settings.

Before following any procedure, copy the canonical template and fill in required keys:

```bash
cp .env.template Backend/.env
# edit Backend/.env → DATABASE_URL, SUPABASE_JWT_SECRET, ALLOWED_ADMIN_EMAILS, OPENAI_API_KEY (optional) etc.
```

See [`Docs/env-config.md`](./env-config.md) for the authoritative variable list and validation steps.

## 2. Local bootstrap checklist

1. **Backend**
   ```bash
   cd Backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   # health checks
   curl http://127.0.0.1:8000/health
   curl http://127.0.0.1:8000/version
   ```

2. **Frontend**
   ```bash
   cd Frontend
   npm install
   npm run dev
   # open http://localhost:5173/#/ and http://localhost:5173/#/admin
   ```

3. **Database sanity** (optional but recommended)
   ```bash
   cd Backend
   source .venv/bin/activate
   python - <<'PY'
   from services.db_service import init_db_pool
   import asyncio
   asyncio.run(init_db_pool())
   print('✅ DATABASE_URL connected')
   PY
   ```

## 3. Workers & manual operations

| Worker | Module | Typical use | Notes |
| --- | --- | --- | --- |
| Discovery | `app.workers.discovery_bot` | Fetch new candidates from OSM. | Uses OSM-only provider; configure rate limits via env vars. |
| Classify | `app.workers.classify_bot` | Assign keep/ignore + category (OpenAI). | Respects `CLASSIFY_MIN_CONF`. Dry-run recommended for testing. |
| Verify & surface | `app.workers.verify_locations` | Promote high-confidence records to `VERIFIED`. | `--city`/`--source` flags exist but currently informational (filters handled in SQL). |
| Monitor | `app.workers.monitor_bot` | Refresh `next_check_at` for stale records. | Uses env-based caps (`MONITOR_MAX_PER_RUN`). |
| Alert | `app.workers.alert_bot` | Emit alerts for error spikes, 429 bursts. | Configure webhook/channel via env vars. |

### CLI examples

```bash
# Discovery dry run (Rotterdam, bakery only)
python -m app.workers.discovery_bot \
  --city rotterdam \
  --categories bakery \
  --limit 50 \
  --dry-run

# Classification dry run (requires OPENAI)
python -m app.workers.classify_bot --limit 25 --dry-run

# Verification dry run
python -m app.workers.verify_locations --limit 50 --dry-run 1

# Verification production run with chunking (6 slices)
python -m app.workers.verify_locations --limit 600 --chunks 6 --chunk-index 0 --dry-run 0

# Monitor freshness (no writes)
python -m app.workers.monitor_bot --limit 200 --dry-run

# Alert bot once-off (no webhook configured)
python -m app.workers.alert_bot --once 1
```

### Worker output cheat sheet

- **Discovery**: Logs Overpass endpoint, results inserted, skips (duplicates). Output stored in `locations` with `state=CANDIDATE`.
- **Classification**: Prints `[KEEP|IGNORE]` decisions with confidence, logs to `ai_logs`.
- **Verify**: `[PROMOTE]`, `[SKIP]`, `[ERROR]` lines summarise action; audit logs persisted.
- **Monitor**: Reports updated `next_check_at` count and skipped terminal states.
- **Alert**: Summaries of error rate, 429 bursts, optional webhook POST status.

## 4. Scheduled automation

| Workflow | Schedule | Command | Secrets required |
| --- | --- | --- | --- |
| `tda_discovery.yml` | `0 */2 * * *` (every 2h) | Runs discovery for each category × chunk. | `DATABASE_URL`, `OPENAI_API_KEY` (optional), `SUPABASE_URL`, `SUPABASE_KEY`, OSM env vars. |
| `tda_discovery_fast.yml` | Manual trigger | Lightweight discovery slices (debug). | Same as above. |
| `tda_verification.yml` | `15 */6 * * *` | Batches verify locations (`verify_locations.py`). | `DATABASE_URL`, `OPENAI_API_KEY`, admin secrets. |
| `tda_monitor.yml` | `*/60 * * * *` | Monitor freshness loop. | `DATABASE_URL`. |
| `tda_alert.yml` | `*/5 * * * *` | Alert thresholds (error/429). | `DATABASE_URL`, alert webhook/channel. |
| `tda_cleanup.yml` | `0 4 * * *` | Housekeeping / backlog cleanup. | `DATABASE_URL`. |
| `frontend_deploy.yml` | On `main` push | Builds + deploys GitHub Pages site. | `VITE_*` secrets, `MAPBOX` token, GH Pages deploy key. |

Render cron jobs (if configured) should mirror the same commands/secrets as above. Keep `.env.template` synchronized so Service → Worker → GitHub Actions share names.

## 5. Observability

- **Metrics snapshot**: `GET /api/v1/admin/metrics/snapshot` (requires Supabase admin JWT). Feeds admin dashboard.
- **Key KPI queries**: see `Infra/monitoring/metrics_dashboard.sql`.
- **Logs**: Workers use structlog JSON. In GitHub Actions, download artifacts or inspect step logs.
- **Alert thresholds**: Controlled via env (`ALERT_*`). Default err rate threshold = 10% over 60 minutes, Google 429 threshold kept for legacy compatibility.

### Useful SQL snippets

```sql
-- Newly discovered candidates (24h)
SELECT id, name, category, source, state, first_seen_at
FROM locations
WHERE first_seen_at >= NOW() - INTERVAL '24 hours'
ORDER BY first_seen_at DESC;

-- Verification promotion summary
SELECT state, COUNT(*)
FROM locations
GROUP BY state
ORDER BY COUNT(*) DESC;

-- AI log error rate (last 60 minutes)
SELECT COUNT(*) FILTER (WHERE is_success IS FALSE OR error_message IS NOT NULL)::float
       / NULLIF(COUNT(*), 0) AS error_rate
FROM ai_logs
WHERE created_at >= NOW() - INTERVAL '60 minutes';
```

## 6. Troubleshooting

| Symptom | Possible cause & fix |
| --- | --- |
| `RuntimeError: DATABASE_URL not set` | Ensure `Backend/.env` is loaded; run `cp .env.template Backend/.env` and populate credentials. |
| Worker exits immediately with `OPENAI_API_KEY missing` | Either supply the key or run with `--dry-run` for local testing. |
| Discovery hitting 429/504 repeatedly | Increase `DISCOVERY_SLEEP_BASE_S`, check Overpass mirrors, confirm respectful `OVERPASS_USER_AGENT`. |
| Empty map frontend | Verify backend reachable at `VITE_API_BASE_URL`, ensure verification promoted enough records (run workers). |
| Admin login fails (401/403) | Check `SUPABASE_JWT_SECRET` matches Supabase project, ensure email is in `ALLOWED_ADMIN_EMAILS`, check Supabase auth logs. |
| Metrics endpoint 503 | Database down or credentials invalid; run the DB sanity snippet and inspect Render logs. |

## 7. Incident response

1. **Identify** — review GitHub Actions history, Render logs, metrics snapshot. Note timestamp, failing worker, error signatures.
2. **Stabilize** — pause offending workflow (disable schedule or set `ALERT_RUN_ONCE=1`), increase sleep/backoff if hitting rate limits.
3. **Investigate** — inspect AI logs (`ai_logs` table), worker stdout, Overpass responses.
4. **Remediate** — rerun worker in dry-run to confirm fix, re-enable schedule, commit configuration updates if needed.
5. **Communicate** — document findings in `Docs/docs_gap_analysis.md` (if docs require updates) and share summary with maintainers.

Escalation order: internal TDA core → Supabase support (for auth/db issues) → OSM community/channel (if long outage) → OpenAI support (if API outage).

## 8. References

- `Docs/env-config.md` — environment variables & secrets.
- `Docs/verify-locations-runbook.md` — verification pipeline deep dive.
- `Docs/discovery-osm.md` — provider internals and rate limiting.
- `Infra/monitoring/metrics_dashboard.md` — KPI SQL.
- `Docs/README.md` — full documentation index.

Keep this runbook updated whenever workflows, environment variables, or operational tooling change.
