#!/bin/bash
# Build script for Render deployment
# This script creates .env.production from environment variables before building

set -e

echo "🔨 Building frontend for production..."

# Create .env.production file from environment variables
# Render passes environment variables to the build process
cat > .env.production << EOF
# Generated during build - do not commit
VITE_BASE_PATH=${VITE_BASE_PATH:-/}
VITE_API_BASE_URL=${VITE_API_BASE_URL}
VITE_MAPBOX_TOKEN=${VITE_MAPBOX_TOKEN}
VITE_MAPBOX_STYLE=${VITE_MAPBOX_STYLE:-mapbox://styles/mapbox/standard}
VITE_SUPABASE_URL=${VITE_SUPABASE_URL}
VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}
EOF

echo "✅ Created .env.production"
echo "📋 Environment variables:"
echo "   VITE_API_BASE_URL=${VITE_API_BASE_URL:-NOT SET}"
echo "   VITE_MAPBOX_TOKEN=${VITE_MAPBOX_TOKEN:+SET}"
echo "   VITE_SUPABASE_URL=${VITE_SUPABASE_URL:+SET}"

# Validate critical environment variables
if [ -z "$VITE_API_BASE_URL" ]; then
  echo "❌ ERROR: VITE_API_BASE_URL is not set!"
  echo "   Please set VITE_API_BASE_URL in Render environment variables."
  echo "   Expected: https://turkish-diaspora-app.onrender.com"
  exit 1
fi

# Warn if using old API URL
if [[ "$VITE_API_BASE_URL" == *"tda-api.onrender.com"* ]]; then
  echo "⚠️  WARNING: VITE_API_BASE_URL contains 'tda-api.onrender.com'"
  echo "   This is the old backend URL. Update to: https://turkish-diaspora-app.onrender.com"
fi

# Build the application
npm run build

echo "✅ Build complete!"

