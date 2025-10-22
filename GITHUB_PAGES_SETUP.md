# GitHub Pages Deployment Setup

This guide explains how to set up GitHub Pages deployment for the Turkish Diaspora App frontend.

## Prerequisites

1. Your repository must be public or you need GitHub Pro/Team for private repositories
2. You need a Mapbox access token
3. You need a backend API URL (optional - demo data will be used if not provided)

## Setup Steps

### 1. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click on "Settings" tab
3. Scroll down to "Pages" section
4. Under "Source", select "GitHub Actions"

### 2. Set up Repository Secrets

Go to Settings > Secrets and variables > Actions and add the following secrets:

#### Required:
- `VITE_MAPBOX_TOKEN`: Your Mapbox access token (get from https://account.mapbox.com/access-tokens/)

#### Optional:
- `VITE_API_BASE_URL`: Your backend API URL (e.g., https://your-backend.herokuapp.com)
- `VITE_MAPBOX_STYLE`: Mapbox style (default: mapbox://styles/mapbox/light-v11)

### 3. Deploy

1. Push your changes to the `main` branch
2. The existing `frontend_deploy.yml` workflow will automatically build and deploy your app
3. Your app will be available at: `https://yourusername.github.io/turkish-diaspora-app/`

## Configuration

### Environment Variables

The app uses the following environment variables:

- `VITE_API_BASE_URL`: Backend API URL (optional)
- `VITE_MAPBOX_TOKEN`: Mapbox access token (required)
- `VITE_MAPBOX_STYLE`: Mapbox style (optional, defaults to light theme)

### Demo Mode

If no backend URL is provided, the app will run in demo mode with sample Turkish business locations in Bangkok.

## Troubleshooting

### Mapbox Token Error
If you see "An API access token is required to use Mapbox GL", make sure you've set the `VITE_MAPBOX_TOKEN` secret in your repository.

### API Connection Error
If you see connection refused errors, either:
1. Set the `VITE_API_BASE_URL` secret with your backend URL, or
2. The app will automatically fall back to demo data

### Build Failures
Check the Actions tab in your repository for build logs and error messages.

## Local Development

For local development, create a `.env` file in the Frontend directory:

```env
VITE_API_BASE_URL=
VITE_MAPBOX_TOKEN=your_mapbox_token_here
VITE_MAPBOX_STYLE=mapbox://styles/mapbox/light-v11
```

Then run:
```bash
cd Frontend
npm install
npm run dev
```
