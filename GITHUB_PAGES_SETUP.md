---
title: GitHub Pages Deployment Setup
status: active
last_updated: 2025-11-04
scope: deployment
owners: [tda-frontend]
---

# GitHub Pages Deployment Setup

How to deploy the frontend to GitHub Pages using the automated workflow.

## Prerequisites

- Repository has GitHub Pages enabled (`Settings ▸ Pages ▸ Source → GitHub Actions`).
- Publishable Mapbox token.
- Backend API URL (Render or local tunnel) exposed via `VITE_API_BASE_URL`.
- Supabase project URL and anon key for admin auth.

## Secrets to configure

Navigate to `Settings ▸ Secrets and variables ▸ Actions` and add:

| Secret | Description |
| --- | --- |
| `VITE_API_BASE_URL` | Backend base URL (e.g., `https://tda-api.onrender.com`). Required. |
| `VITE_MAPBOX_TOKEN` | Mapbox publishable token. Required for map rendering. |
| `VITE_SUPABASE_URL` | Supabase project URL. |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon/public key. |

Optional: additional `VITE_MAPBOX_STYLE` or analytics tokens as needed.

## Deployment workflow

`/.github/workflows/frontend_deploy.yml`:

1. Triggered on pushes to `main` (and manual dispatch).
2. Installs dependencies, runs `npm run build`.
3. Deploys the `dist/` folder via `actions/deploy-pages@v4`.

To trigger manually: `Actions ▸ frontend_deploy ▸ Run workflow`.

## Local verification

```bash
cd Frontend
npm run build
npm run preview
# Open http://localhost:4173/#/
```

Ensure `.env.production` (if used) contains the same `VITE_*` keys you configured in GitHub secrets.

## Troubleshooting

| Issue | Fix |
| --- | --- |
| Blank map / token error | Confirm `VITE_MAPBOX_TOKEN` secret is set and not restricted to different origin. |
| API calls failing | Verify `VITE_API_BASE_URL` points to live backend and supports CORS for GitHub Pages domain. |
| Admin login loops | Ensure Supabase anon key + URL match deployed backend environment. |
| Workflow failure | Inspect `frontend_deploy` logs; rerun with `ACTIONS_STEP_DEBUG=true` if needed. |

## Related docs

- `Docs/env-config.md` — environment variable mapping.
- `Frontend/README.md` — project scripts and architectural notes.
- `Docs/runbook.md` — operational procedures (includes frontend troubleshooting).
