# Turkish Diaspora App - Quick Start Guide

## Prerequisites

- **Python 3.10+** (for Backend)
- **Node.js 18+** (for Frontend)
- **Git** (for version control)
- **Supabase Account** (for database)

## Environment Setup

### 1. Clone and Navigate
```bash
git clone <repository-url>
cd "Turkish Diaspora App"
```

### 2. Backend Setup
```bash
# Navigate to Backend
cd Backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp ../Docs/env-template.txt .env
# Edit .env with your configuration
```

### 3. Frontend Setup
```bash
# Navigate to Frontend
cd Frontend

# Install dependencies
npm install

# Create environment file (if needed)
# Add VITE_MAPBOX_TOKEN=your_token to .env
```

## Development Commands

### Backend Development

#### Start FastAPI Server
```bash
cd Backend
source .venv/bin/activate
uvicorn app.main:app --reload
```
- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/health

#### Run Discovery Bot
```bash
cd Backend
source .venv/bin/activate

# Basic discovery (Rotterdam)
python -m app.workers.discovery_bot --city rotterdam --limit 50

# With specific categories
python -m app.workers.discovery_bot --city rotterdam --categories restaurant,bakery --limit 100

# Dry run (recommended first)
python -m app.workers.discovery_bot --city rotterdam --limit 50 --dry-run 1
```

#### Run Verification Bot
```bash
cd Backend
source .venv/bin/activate

# Verify candidates (dry run first)
python -m app.workers.verify_locations --city rotterdam --limit 50 --dry-run 1

# Actual verification
python -m app.workers.verify_locations --city rotterdam --limit 200 --dry-run 0

# Process specific source
python -m app.workers.verify_locations --source OSM_OVERPASS --limit 100 --dry-run 0
```

#### Run Classification Bot
```bash
cd Backend
source .venv/bin/activate

# Classify locations
python -m app.workers.classify_bot --limit 50 --dry-run 1
```

### Frontend Development

#### Start Development Server
```bash
cd Frontend
npm run dev
```
- **Frontend**: http://localhost:5173
- **Hot Reload**: Enabled automatically

#### Build for Production
```bash
cd Frontend
npm run build
```

#### Preview Production Build
```bash
cd Frontend
npm run preview
```

## Database Operations

### Database Connection
```bash
# Check database connection
cd Backend
source .venv/bin/activate
python -c "from app.db import get_db; print('Database connected')"
```

### Database Monitoring
```sql
-- Check recent locations
SELECT id, name, category, source, state, created_at
FROM locations
ORDER BY created_at DESC
LIMIT 20;

-- Check state distribution
SELECT state, COUNT(*) as count
FROM locations
GROUP BY state
ORDER BY count DESC;

-- Check AI logs
SELECT action, COUNT(*) as count
FROM ai_logs
WHERE created_at > NOW() - INTERVAL '1 day'
GROUP BY action
ORDER BY count DESC;
```

### Database Health Check
```bash
cd Backend
source .venv/bin/activate

# Check connection pool
python -c "
from app.db import get_db
import asyncio
async def check():
    async with get_db() as db:
        result = await db.execute('SELECT 1')
        print('Database connection: OK')
asyncio.run(check())
"
```

## Monitoring Commands

### Check API Health
```bash
# Backend health
curl http://127.0.0.1:8000/health

# Frontend health (if running)
curl http://localhost:5173
```

### Check Worker Status
```bash
cd Backend
source .venv/bin/activate

# Check discovery bot status
python -c "
from app.workers.discovery_bot import main
print('Discovery bot: Ready')
"

# Check verification bot status
python -c "
from app.workers.verify_locations import main
print('Verification bot: Ready')
"
```

### Check AI Services
```bash
cd Backend
source .venv/bin/activate

# Test AI classification
python -c "
from app.services.classify_service import ClassifyService
import asyncio
async def test():
    service = ClassifyService()
    result = await service.classify('Test Turkish Restaurant')
    print(f'AI Classification: {result}')
asyncio.run(test())
"
```

## Configuration Files

### Backend Configuration
- **`.env`**: Environment variables (database, API keys)
- **`requirements.txt`**: Python dependencies
- **`app/config.py`**: Application configuration

### Frontend Configuration
- **`package.json`**: Node.js dependencies
- **`vite.config.ts`**: Vite build configuration
- **`tailwind.config.ts`**: Tailwind CSS configuration

### Infrastructure Configuration
- **`Infra/config/categories.yml`**: Business category mappings
- **`Infra/config/cities.yml`**: City and district configurations
- **`Infra/supabase/`**: Database migrations

## Troubleshooting

### Common Issues

#### Backend Issues
```bash
# Check Python version
python --version

# Check virtual environment
which python

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check database connection
python -c "from app.db import get_db; print('DB OK')"
```

#### Frontend Issues
```bash
# Check Node version
node --version

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check build
npm run build
```

#### Database Issues
```bash
# Check environment variables
echo $DATABASE_URL

# Test connection
cd Backend
source .venv/bin/activate
python -c "import os; print('DB URL:', os.getenv('DATABASE_URL'))"
```

### Log Files
- **Backend Logs**: Check console output for structured logging
- **Frontend Logs**: Check browser console for errors
- **Database Logs**: Check Supabase dashboard for query logs

## Production Deployment

### Backend Deployment
```bash
# Build for production
cd Backend
pip install -r requirements.txt

# Set production environment variables
export DATABASE_URL="your_production_db_url"
export OPENAI_API_KEY="your_openai_key"

# Run with production settings
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend Deployment
```bash
# Build for production
cd Frontend
npm run build

# Deploy dist/ folder to your hosting service
# (GitHub Pages, Netlify, Vercel, etc.)
```

## Key Documentation

- **`.cursorrules`**: Cursor AI context and coding standards
- **`PROJECT_CONTEXT.md`**: Comprehensive project overview
- **`README.md`**: Basic project information
- **`Docs/`**: Detailed documentation and planning files

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the documentation in `Docs/`
3. Check the project context files
4. Review recent work in `Backend/OSM_Discovery_Report_Rotterdam_Production.md`

## Recent Updates

- **October 2025**: Rotterdam production rollout completed (151+ locations)
- **VerifyLocationsBot**: Automated verification pipeline implemented
- **Enhanced Error Handling**: Improved OSM API error handling
- **Category Mapping**: Enhanced Turkish business detection

This quick start guide should get you up and running with the Turkish Diaspora App development environment.
