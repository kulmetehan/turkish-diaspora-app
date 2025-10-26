# Admin Auth (TDA-124)

This adds Supabase email/password login for admins, client route protection, and server-side JWT validation with an allowlist.

## Env variables

Backend (.env on Render/GitHub Actions):

```bash
# REQUIRED for DB
DATABASE_URL=<postgres-connection-string>

# REQUIRED for Admin Auth (server-side only)
SUPABASE_JWT_SECRET=<supabase-jwt-secret>   # never expose to frontend
ALLOWED_ADMIN_EMAILS=<comma-separated-emails>  # e.g. "wwwlamarkanl@gmail.com"

# Optional
OPENAI_API_KEY=<optional>
OPENAI_MODEL=gpt-4.1-mini
ENVIRONMENT=local
```

Frontend (Vite env):

```bash
VITE_SUPABASE_URL=<https://your-supabase-project.supabase.co>
VITE_SUPABASE_ANON_KEY=<public-anon-key>
# existing
VITE_API_BASE_URL=<https://tda-api.onrender.com>
```

Important:
- SUPABASE_JWT_SECRET and ALLOWED_ADMIN_EMAILS are backend-only. Do not expose them on the client.
- Do not commit real secrets.

## How it works

Frontend:
- `src/lib/supabaseClient.ts` initializes Supabase.
- `src/hooks/useAuth.ts` tracks session and exposes `isAuthenticated`, `userEmail`, `accessToken`.
- `src/components/auth/RequireAdmin.tsx` redirects unauthenticated users to `/login`.
- `src/pages/LoginPage.tsx` provides email/password login with shadcn/ui.
- `src/pages/AdminHomePage.tsx` is a protected placeholder.
- Routes added in `src/main.tsx`: `/login`, `/admin`.
- `src/lib/api.ts` exports `authFetch()` and `whoAmI()` which attach `Authorization: Bearer <token>` to backend requests.

Backend:
- `app/core/auth.py` validates Supabase JWT with `SUPABASE_JWT_SECRET` and checks email against `ALLOWED_ADMIN_EMAILS`.
- `api/routers/admin_auth.py` exposes `GET /api/v1/admin/whoami` (returns `{ ok: true, admin_email }`).
- Router is registered in `app/main.py`.

## Manual test

1) In Supabase Dashboard, ensure an admin user exists (e.g. `wwwlamarkanl@gmail.com`). Put the same email in `ALLOWED_ADMIN_EMAILS`.

2) Frontend:
- Navigate to `/login`.
- Sign in with email/password. You should be redirected to `/admin`.

3) From the admin page (or console), call:

```ts
import { whoAmI } from "@/lib/api";
whoAmI().then(console.log)
```

The backend should validate the token and reply:

```json
{ "ok": true, "admin_email": "wwwlamarkanl@gmail.com" }
```

4) Logout or remove session and try to visit `/admin` → you should be redirected back to `/login`.

## Notes
- No public signup in UI.
- No ORM added; backend continues to use async DB access.
- Real security is server-side via JWT verification and email allowlist.


