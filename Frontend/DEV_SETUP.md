---
title: Frontend Development Setup
status: active
last_updated: 2025-11-04
scope: frontend
owners: [tda-frontend]
---

# Frontend Development Setup

Quick checklist for running the frontend locally with the admin dashboard and metrics tab.

## 1. Environment variables

Create `Frontend/.env.development` with the Vite keys:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_MAPBOX_TOKEN=<mapbox-token>
VITE_SUPABASE_URL=<https://your-project.supabase.co>
VITE_SUPABASE_ANON_KEY=<anon-key>
```

Ensure the backend is running at `VITE_API_BASE_URL` (see `QUICK_START.md`).

## 2. Install & run

```bash
cd Frontend
npm install
npm run dev
# Open http://localhost:5173/#/
```

Admin routes use hash routing, so navigate to `http://localhost:5173/#/admin` after authenticating.

## 3. Metrics tab dependency

The metrics dashboard lazily loads Recharts and expects the backend metrics endpoint to respond:

```bash
curl -H "Authorization: Bearer <supabase-admin-jwt>" \
  http://127.0.0.1:8000/api/v1/admin/metrics/snapshot | jq .
```

If the endpoint returns 401/403, verify `SUPABASE_JWT_SECRET` and admin credentials in the backend `.env`.

## 4. Troubleshooting

| Issue | Fix |
| --- | --- |
| `Failed to resolve import "recharts"` | Ensure `npm install` ran inside `Frontend/` (Recharts is a direct dependency). |
| Blank map tiles | Confirm `VITE_MAPBOX_TOKEN` is set and valid. |
| API 401/403 | Backend must be running; check Supabase session and `VITE_API_BASE_URL`. |
| Admin redirects to login | Ensure Supabase anon key + URL match backend project; check Supabase user allowlist. |

## 5. Useful scripts

- `npm run build && npm run preview` — verify production build locally (`http://localhost:4173/#/`).
- `npm run lint` — lint checks (if configured).

For deeper operational guidance see `Docs/runbook.md` and `Docs/frontend-search.md`.
