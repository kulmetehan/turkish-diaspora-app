# Turkish Diaspora App — Frontend

React + TypeScript application delivering the public map, admin dashboard, and metrics UI for the Turkish Diaspora App.

## Stack

- React 19, TypeScript, Vite
- Tailwind CSS with design tokens (see `Docs/design-system.md`)
- shadcn/ui pattern (`class-variance-authority`, `tailwind-merge`)
- Mapbox GL for map rendering
- Supabase Auth (email/password) for admin routes
- State helpers: custom hooks (`useSearch`, `useMapStore`, etc.)

## Directory overview

| Path | Purpose |
| --- | --- |
| `src/App.tsx` | Public map entry point using `useSearch` and map/list components. |
| `src/components/` | UI primitives (`ui/`), filters, bottom sheet, map widgets, auth guards. |
| `src/pages/` | Route components (`AdminHomePage`, `LoginPage`, `UiKit`). |
| `src/lib/` | API clients (`api.ts`, `apiAdmin.ts`), theme helpers, Supabase client. |
| `src/hooks/` | Domain hooks (`useSearch`, map store, theme). |
| `src/styles/` | Tailwind config (`index.css`, token definitions). |

## Scripts

```bash
npm install         # install dependencies
npm run dev         # start Vite dev server (http://localhost:5173/#/)
npm run build       # production build -> dist/
npm run preview     # preview production build (http://localhost:4173/#/)
```

## Environment variables (`VITE_*`)

Set in `Frontend/.env.development` (local) and GitHub Actions secrets for deployment.

- `VITE_API_BASE_URL` — Backend base URL (required).
- `VITE_MAPBOX_TOKEN` — Mapbox publishable token (required for full map).
- `VITE_SUPABASE_URL` — Supabase project URL.
- `VITE_SUPABASE_ANON_KEY` — Supabase anon/public key.
- Optional extras: `VITE_MAPBOX_STYLE`, analytics tokens.

## Routes and navigation

- `#/` — Public map + list view.
- `#/admin` — Authenticated admin dashboard (requires Supabase session).
- `#/login` — Supabase email/password login screen.
- `#/ui-kit` — Component showroom (keep updated when adding new primitives).

## Testing checklist

- Verify map renders with markers and list updates as filters change.
- Confirm bottom sheet (mobile) passes QA script (`Docs/qa/bottom-sheet-test.md`).
- Run `npm run build && npm run preview` before deploying to GitHub Pages.
- Ensure admin login flows through Supabase and metrics tab loads `/api/v1/admin/metrics/snapshot`.

## Deployment

Automated via GitHub Actions (`frontend_deploy.yml`). See [`GITHUB_PAGES_SETUP.md`](../GITHUB_PAGES_SETUP.md) for details. Deployments rely on the `VITE_*` secrets listed above.

## Related documentation

- `Docs/design-system.md` — UI guidelines and tokens
- `Docs/frontend-search.md` — Search/filter implementation notes
- `Docs/map-ux-upgrade.md` — Mapbox migration and UX goals
- `Docs/runbook.md` — Operational runbook (includes frontend troubleshooting)
