---
title: Quick Start Guide
status: active
last_updated: 2025-11-04
scope: setup
owners: [tda-core]
---

# Turkish Diaspora App — Quick Start

Spin up the full stack (FastAPI backend, workers, React frontend) on a new machine in under 30 minutes. For deeper operations and troubleshooting, jump to `Docs/runbook.md` once you complete this guide.

## 1. Prerequisites

- **Python 3.11+** (matching `Backend/runtime.txt`)
- **Node.js 20+** (LTS) with npm
- **PostgreSQL connection** — Supabase recommended; local Postgres works for development
- **OpenAI API key** (optional for dry-runs, required for full verification pipeline)
- **Mapbox publishable token** (optional; without it the map falls back to a placeholder grid)

Install auxiliary tooling if you prefer:

```bash
# macOS example
brew install python@3.11 node@20
pipx install uv        # optional: faster backend dependency management
```

## 2. Clone and bootstrap

```bash
git clone <repository-url>
cd turkish-diaspora-app

# Copy canonical environment template
cp .env.template Backend/.env
# Optional: extract only the Vite keys for the frontend dev server
grep '^VITE_' .env.template > Frontend/.env.development
```

Edit `Backend/.env` and provide at least:

- `DATABASE_URL`
- `SUPABASE_JWT_SECRET`
- `ALLOWED_ADMIN_EMAILS`
- `OPENAI_API_KEY` (leave blank for classification dry-runs)

For the frontend add, inside `Frontend/.env.development`:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_MAPBOX_TOKEN=<your-mapbox-token>
VITE_SUPABASE_URL=<https://...supabase.co>
VITE_SUPABASE_ANON_KEY=<anon-key>
```

## 3. Backend setup

```bash
cd Backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Verify database connectivity and configuration
python - <<'PY'
from services.db_service import init_db_pool
import asyncio
asyncio.run(init_db_pool())
print("✅ DATABASE_URL connected")
PY

# Launch FastAPI with auto-reload
uvicorn app.main:app --reload
```

Smoke tests (new terminal):

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/version
```

## 4. Frontend setup

```bash
cd Frontend
npm install
npm run dev
```

Open `http://localhost:5173/#/` for the public map and `http://localhost:5173/#/admin` for the protected admin view (requires Supabase login). See `Frontend/DEV_SETUP.md` for advanced options and troubleshooting.

## 5. Optional worker smoke tests

Run these only after the backend is healthy and the database contains seed data:

```bash
cd Backend
source .venv/bin/activate

# Discovery — dry run over a small slice
python -m app.workers.discovery_bot --city rotterdam --categories bakery --limit 5 --dry-run

# Classification demo (dry run, requires OPENAI_API_KEY)
python -m app.workers.classify_bot --limit 5 --dry-run

# Verification dry run
python -m app.workers.verify_locations --limit 5 --dry-run 1
```

Check metrics snapshot (requires admin JWT from Supabase):

```bash
curl -H "Authorization: Bearer <admin-jwt>" \
  http://127.0.0.1:8000/api/v1/admin/metrics/snapshot | jq .
```

## 6. Next steps

- Follow `Docs/runbook.md` for cron scheduling, troubleshooting, and incident response.
- Review `Docs/env-config.md` before promoting changes to Render or rotating secrets.
- Consult `Docs/docs_gap_analysis.md` for outstanding documentation improvements.
- Keep your local `.env` files out of git: `Backend/.env` is ignored by default.

Need more detail? The runbook links to all workers, health checks, and rollback procedures.
