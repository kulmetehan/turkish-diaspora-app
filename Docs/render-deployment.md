# Render Frontend Deployment Guide

## Environment Variables

### Deployment-Specific Requirements

Both GitHub Pages and Render deployments require the same environment variables, but they are configured differently:

#### GitHub Pages (via GitHub Secrets)

Configure these in **Repository Settings → Secrets and variables → Actions**:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `VITE_API_BASE_URL` | ✅ | Backend API base URL (host only, no `/api/v1`, no trailing slash) | `https://turkish-diaspora-app.onrender.com` |
| `VITE_SUPABASE_URL` | ✅ | Supabase project URL | `https://xxx.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | ✅ | Supabase anonymous key | `eyJhbGc...` |
| `VITE_MAPBOX_TOKEN` | ✅ | Mapbox access token | `pk.eyJ1...` |
| `VITE_MAPBOX_STYLE` | Optional | Mapbox style URL | `mapbox://styles/mapbox/standard` |

**Note**: The GitHub Actions workflow (`.github/workflows/frontend_deploy.yml`) automatically sets `VITE_BASE_PATH=/turkish-diaspora-app/` for GitHub Pages builds.

#### Render (via Render Environment Variables)

Configure these in **Render Dashboard → Your Static Site → Environment**:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `VITE_API_BASE_URL` | ✅ | Backend API base URL (host only, no `/api/v1`, no trailing slash) | `https://turkish-diaspora-app.onrender.com` |
| `VITE_SUPABASE_URL` | ✅ | Supabase project URL | `https://xxx.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | ✅ | Supabase anonymous key | `eyJhbGc...` |
| `VITE_MAPBOX_TOKEN` | ✅ | Mapbox access token | `pk.eyJ1...` |
| `VITE_BASE_PATH` | Optional | Base path for deployment (defaults to `/` for Render) | `/` |
| `VITE_MAPBOX_STYLE` | Optional | Mapbox style URL | `mapbox://styles/mapbox/standard` |

**Important**: 
- `VITE_API_BASE_URL` must be set to `https://turkish-diaspora-app.onrender.com` (the backend service URL)
- Do NOT include `/api/v1` or a trailing slash in `VITE_API_BASE_URL` - the frontend code automatically appends `/api/v1` to all API paths
- Environment variables must be set in Render **before** building. If you add them after the build, trigger a new deployment

## Render Service Configuration

### Build Command

Use the build script that creates `.env.production` from environment variables:

```bash
cd Frontend && bash build.sh
```

Or manually:

```bash
cd Frontend && npm run build
```

**Important**: Environment variables must be set in Render **before** building. If you add them after the build, you need to trigger a new deployment.

### Start Command

For static site hosting:

```bash
cd Frontend && npx serve -s dist -l 3000
```

Or use a simple HTTP server:

```bash
cd Frontend/dist && python3 -m http.server 3000
```

## Troubleshooting

### Problem: API calls go to `127.0.0.1:8000`

**Cause**: `VITE_API_BASE_URL` is not set or not available during build.

**Solution**:
1. Check that `VITE_API_BASE_URL` is set in Render environment variables
2. Ensure the variable name starts with `VITE_` (required by Vite)
3. Trigger a new deployment after setting the variable
4. Check the build logs to verify the variable is being read

### Problem: Environment variables not available during build

**Cause**: Render may not pass environment variables to the build process automatically.

**Solution**:
1. Use the `build.sh` script which explicitly creates `.env.production`
2. Or set environment variables in the Render dashboard before building
3. Check Render build logs to see if variables are being read

### Problem: Build succeeds but app shows errors

**Cause**: Environment variables were set after the build, or build cache is stale.

**Solution**:
1. Clear Render build cache
2. Trigger a new deployment
3. Verify variables are set before build starts

## Verification

### After Deployment

1. **Check Browser Console**: Open the deployed site and check the browser console. You should see API calls going to:
   ```
   https://turkish-diaspora-app.onrender.com/api/v1/...
   ```
   
   ❌ **Wrong**: If you see `tda-api.onrender.com` or `127.0.0.1:8000`, the environment variable was not set correctly during build.

2. **Check Build Logs**: In Render build logs, look for:
   ```
   VITE_API_BASE_URL=https://turkish-diaspora-app.onrender.com
   ```
   
   If you see `VITE_API_BASE_URL=NOT SET` or an old URL, update the environment variable and trigger a new deployment.

### Common Issues

**Problem**: API calls go to `tda-api.onrender.com` instead of `turkish-diaspora-app.onrender.com`

**Cause**: `VITE_API_BASE_URL` environment variable in Render is set to the old URL or not set at all.

**Solution**:
1. Go to Render Dashboard → Your Static Site → Environment
2. Find or add `VITE_API_BASE_URL`
3. Set value to: `https://turkish-diaspora-app.onrender.com` (no trailing slash, no `/api/v1`)
4. Save and trigger a new deployment
5. Wait for build to complete and verify in browser console

## Related Documentation

- `GITHUB_PAGES_SETUP.md` - GitHub Pages deployment
- `Docs/env-config.md` - Environment variable reference

