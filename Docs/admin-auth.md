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

### City and District Management

Authenticated admins can manage cities and districts through the Cities page (`#/admin/cities`), providing a web-based interface for configuring discovery grids without manually editing YAML files.

#### Features

- **City management**: Add, edit, and delete cities with center coordinates (latitude/longitude)
- **District management**: Add, edit, and delete districts for each city
- **Coordinate precision**: Input fields support 6 decimal precision (e.g., `52.157284, 4.493417`)
- **Automatic bounding box calculation**: Bounding boxes are automatically calculated from district center coordinates (±0.015 degrees)
- **Direct YAML writing**: Changes are written directly to `Infra/config/cities.yml` with automatic timestamped backups
- **Expandable districts view**: View all districts per city in an expandable section with center coordinates
- **Validation**: All coordinates are validated to ensure they fall within valid WGS84 ranges

#### API Endpoints

- `GET /api/v1/admin/cities` - List all cities with readiness metrics
- `GET /api/v1/admin/cities/{city_key}` - Get full city details including all districts
- `POST /api/v1/admin/cities` - Create a new city
- `PUT /api/v1/admin/cities/{city_key}` - Update city information
- `DELETE /api/v1/admin/cities/{city_key}` - Delete a city and all its districts
- `POST /api/v1/admin/cities/{city_key}/districts` - Add a district to a city
- `PUT /api/v1/admin/cities/{city_key}/districts/{district_key}` - Update a district
- `DELETE /api/v1/admin/cities/{city_key}/districts/{district_key}` - Delete a district

#### Adding a City

1. Navigate to `#/admin/cities` in the admin interface
2. Click "Add City"
3. Enter city name, country code (default: NL), and center coordinates
4. Optionally add districts during city creation
5. Center coordinates must have 6 decimal precision (e.g., `52.157284`)

#### Managing Districts

1. On any city card, click "Expand Districts" to view all districts
2. Click "Add District" to create a new district
3. Enter district name and center coordinates
4. Bounding box is automatically calculated (±0.015 degrees from center)
5. Use "Edit" and "Delete" buttons on individual districts to manage them

#### Backup Mechanism

Before each write operation, a timestamped backup is created:
- Backup location: `Infra/config/cities.yml.backup.{YYYYMMDD_HHMMSS}`
- Maximum 5 backups are kept (older backups are automatically removed)
- Backups can be restored manually if needed

For detailed information about the YAML structure and how discovery uses city configurations, see [`Docs/city-grid.md`](./city-grid.md).

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
- Admin routes: `Backend/api/routers/admin_auth.py`, `Backend/api/routers/admin_metrics.py`, `Backend/api/routers/admin_cities.py`
- City management UI: `Frontend/src/pages/AdminCitiesPage.tsx`
- City management service: `Backend/services/cities_config_service.py`
- Admin navigation: [`Docs/admin-navigation.md`](./admin-navigation.md) — navigation architecture and structure
