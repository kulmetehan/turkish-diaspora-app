#!/bin/bash

# Turkish Diaspora App - GitHub Pages Deployment Script
# This script helps set up and deploy the frontend to GitHub Pages

echo "🚀 Turkish Diaspora App - GitHub Pages Deployment"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "Frontend/package.json" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

echo "📋 Deployment Checklist:"
echo "1. ✅ GitHub Pages enabled in repository settings"
echo "2. 🔑 Repository secrets configured:"
echo "   - VITE_MAPBOX_TOKEN (required)"
echo "   - VITE_API_BASE_URL (optional)"
echo "   - VITE_MAPBOX_STYLE (optional)"
echo "3. 🔄 GitHub Actions workflow created"

echo ""
echo "📝 Next Steps:"
echo "1. Go to your GitHub repository settings"
echo "2. Navigate to 'Secrets and variables' > 'Actions'"
echo "3. Add the following secrets:"
echo "   - VITE_MAPBOX_TOKEN: Your Mapbox access token"
echo "   - VITE_API_BASE_URL: Your backend API URL (optional)"
echo ""
echo "4. Push your changes to the main branch:"
echo "   git add ."
echo "   git commit -m 'Configure GitHub Pages deployment'"
echo "   git push origin main"
echo ""
echo "5. Check the Actions tab for deployment status"
echo "6. Your app will be available at: https://yourusername.github.io/Turkish-Diaspora-App/"
echo ""
echo "📚 For detailed instructions, see GITHUB_PAGES_SETUP.md"

# Build the frontend locally to test
echo ""
echo "🔨 Testing local build..."
cd Frontend
npm install
npm run build:prod

if [ $? -eq 0 ]; then
    echo "✅ Local build successful!"
    echo "📁 Built files are in Frontend/dist/"
else
    echo "❌ Local build failed. Please check the errors above."
    exit 1
fi

echo ""
echo "🎉 Setup complete! Follow the next steps above to deploy."
