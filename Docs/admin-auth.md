---
title: Admin Auth (TDA-124)
status: active
last_updated: 2025-11-04
scope: frontend
owners: [tda-frontend]
---

# Admin Auth (TDA-124)

Adds Supabase email/password login for admins, client route protection, and server-side JWT validation with an allowlist.

## Environment variables

**Backend (`Backend/.env`)**

```bash
DATABASE_URL=<postgres-connection-string>
SUPABASE_JWT_SECRET=<supabase-jwt-secret>
ALLOWED_ADMIN_EMAILS=admin@example.com,ops@example.com
OPENAI_API_KEY=<optional>
OPENAI_MODEL=gpt-4.1-mini
ENVIRONMENT=dev
```

**Frontend (`Frontend/.env.development`)**

```bash
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=<public-anon-key>
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Secrets are documented centrally in `Docs/env-config.md`.

## How it works

### Frontend

- `src/lib/supabaseClient.ts` creates Supabase client.
- `src/hooks/useAuth.ts` tracks session, exposes `isAuthenticated`, `userEmail`, `accessToken`.
- `src/components/auth/RequireAdmin.tsx` guards admin routes (`#/admin`).
- `src/pages/LoginPage.tsx` renders email/password login (shadcn/ui form pattern).
- `src/pages/AdminHomePage.tsx` is wrapped by `RequireAdmin` to ensure only authenticated admins can view data.
- `src/lib/api.ts` exposes `authFetch` and `whoAmI()` to include `Authorization: Bearer <token>` headers.

### Backend

- `app/core/auth.py` validates Supabase JWT with `SUPABASE_JWT_SECRET`, ensures email is in `ALLOWED_ADMIN_EMAILS`.
- `Backend/api/routers/admin_auth.py` exposes `GET /api/v1/admin/whoami` returning `{ ok, admin_email }`.
- Admin-specific routers (metrics, locations) depend on the same auth dependency.

### Manual Location Creation (ADMIN_MANUAL)

- Authenticated admins can create verified locations via `POST /api/v1/admin/locations`.
- The backend stamps `source = ADMIN_MANUAL`, generates a unique `place_id`, and calls `update_location_classification` with `confidence_score = 0.90` so the row enters the map immediately as `VERIFIED`.
- The action automatically records `[manual add by <admin email>]` in notes and logs an `admin_location_create` audit entry in `ai_logs`.
- Inputs must include lat/lng within the valid WGS84 range and a canonical category key (from `categories.yml`) to keep the public map filters consistent.

## Manual test

1. Create admin user in Supabase dashboard (Auth ▸ Users). Add email to `ALLOWED_ADMIN_EMAILS`.
2. Start backend + frontend locally.
3. Visit `#/login`, sign in with admin credentials. Expect redirect to `#/admin`.
4. From console run:
   ```ts
   import { whoAmI } from "@/lib/api";
   whoAmI().then(console.log);
   ```
   Expected: `{ ok: true, admin_email: "admin@example.com" }`.
5. Logout (Supabase) and attempt to visit `#/admin` → redirected back to login.

## Troubleshooting

| Issue | Fix |
| --- | --- |
| 401/403 on `whoAmI` | Check JWT secret, ensure email is in allowlist, verify Supabase session exists. |
| Admin loop after login | Ensure frontend and backend share the same Supabase project (URL + anon key). |
| Token decode error | Confirm backend `ENVIRONMENT` includes `local/dev` to allow dev routes; validate Supabase JWT secret. |

## References

- Frontend supabase client: `Frontend/src/lib/supabaseClient.ts`
- Auth hook: `Frontend/src/hooks/useAuth.ts`
- Backend auth dependency: `Backend/app/core/auth.py`
- Admin routes: `Backend/api/routers/admin_auth.py`, `Backend/api/routers/admin_metrics.py`
