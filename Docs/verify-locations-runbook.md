# Verify & Surface Locations - Runbook

## Overview
This runbook documents the process for verifying and surfacing locations using the existing `verify_locations.py` worker and services. The goal is to promote eligible locations from `CANDIDATE` → `VERIFIED` state and ensure they appear in the frontend.

## Architecture Review

### Existing Services (✅ Confirmed)
- **`Backend/services/classify_service.py`**: Handles AI classification of locations
- **`Backend/services/ai_validation.py`**: Validates classification payloads
- **`Backend/services/audit_service.py`**: Logs all actions for audit trail
- **`Backend/app/workers/verify_locations.py`**: Main worker for verification process

### Worker Behavior (✅ Confirmed)
The `verify_locations.py` worker:
1. Fetches `CANDIDATE` locations from the database
2. Calls `ClassifyService.classify()` for each location
3. Validates results with `validate_classification_payload()`
4. Updates `state` to `VERIFIED` for eligible locations
5. Logs all actions via `AuditService.log()`
6. Supports flags: `--limit`, `--offset`, `--source`, `--city`, `--dry-run`, `--chunks`, `--chunk-index`

### Database Schema (✅ Confirmed)
The database uses the schema from `Infra/supabase/0001_init.sql`:
- `locations` table with columns: `id`, `name`, `address`, `lat`, `lng`, `category`, `state`, `confidence_score`, `last_verified_at`, `is_retired`
- `state` column uses `location_state` enum: `CANDIDATE`, `PENDING_VERIFICATION`, `VERIFIED`, `SUSPENDED`, `RETIRED`
- `ai_logs` table for audit trail

## Commands to Run

### Environment Setup
```bash
cd Backend/
# Load environment variables (worker auto-loads .env via dotenv)
set -a; source ./.env; set +a
```

### 1. Dry Run (Safe Testing)
```bash
cd Backend/
python -m app.workers.verify_locations \
  --source OSM_OVERPASS \
  --limit 50 \
  --dry-run 1
```

### 2. Apply Changes (Production)
```bash
cd Backend/
python -m app.workers.verify_locations \
  --source OSM_OVERPASS \
  --limit 200 \
  --dry-run 0
```

### 3. Parallel Processing (Chunking)
```bash
cd Backend/
python -m app.workers.verify_locations \
  --source OSM_OVERPASS \
  --chunks 3 \
  --chunk-index 0 \
  --limit 300 \
  --dry-run 0
```

## Database Queries for Verification

### State Distribution
```sql
SELECT state, COUNT(*) FROM locations
GROUP BY state ORDER BY 2 DESC;
```

### Recently Verified Locations
```sql
SELECT id, name, category, source, state, last_verified_at
FROM locations
WHERE state = 'VERIFIED' AND is_retired = false
ORDER BY last_verified_at DESC
LIMIT 50;
```

### OSM-Only Verified Locations
```sql
SELECT id, name, category, source, state
FROM locations
WHERE source = 'OSM_OVERPASS' AND state = 'VERIFIED'
ORDER BY id DESC
LIMIT 50;
```

## API Endpoint Testing

### Frontend API Call
The frontend calls: `/api/v1/locations/` with parameters:
- `state: "VERIFIED"` (default)
- `limit: "500"`
- **Note**: `only_turkish` parameter removed - API now returns only Turkish businesses by design

### Backend API Response
The backend API (`Backend/api/routers/locations.py`) returns:
```json
[
  {
    "id": "123",
    "name": "Location Name",
    "lat": 52.1234,
    "lng": 4.5678,
    "category": "bakery",
    "rating": 4.5,
    "state": "VERIFIED"
  }
]
```

### cURL Test
```bash
curl -s "http://localhost:8000/api/v1/locations?state=VERIFIED&limit=20" | jq .
```

## Frontend Integration

### Frontend Code
- **Hook**: `Frontend/src/hooks/useLocations.ts` - Fetches locations from API
- **API Client**: `Frontend/src/lib/api/location.ts` - Handles API calls
- **Main App**: `Frontend/src/App.tsx` - Renders locations on map and list

### Frontend Filters
The frontend applies these filters:
- `onlyTurkish: true` (informational - API returns only Turkish businesses)
- `category` filter
- `minRating` filter
- `search` text filter

## Turkish-Only Verification (✅ Implemented)

### 1. Worker-Level Enforcement
- **Implementation**: `verify_locations.py` now enforces Turkish-only verification
- **Logic**: Only promotes locations with `action: "keep"` (Turkish businesses) to `VERIFIED`
- **Logging**: Non-Turkish businesses are logged with `reason: "not_turkish"`
- **Audit**: All actions logged via `AuditService.log()`

### 2. API Simplification
- **Change**: Removed `only_turkish` parameter from frontend API calls
- **Result**: API naturally returns only Turkish businesses (those that passed verification)
- **Benefit**: Cleaner API, no client-side filtering needed

### 3. Frontend Updates
- **Change**: Removed client-side Turkish filtering logic
- **UI**: Turkish filter now shows as "Alleen Turks (automatisch)" (disabled)
- **Result**: All returned locations are Turkish businesses by design

## Environment Setup

### Required Environment Variables
- `DATABASE_URL`: Database connection string
- `OPENAI_API_KEY`: OpenAI API key for classification
- **Note**: Worker auto-loads `.env` file via `python-dotenv`

## Expected Results

### After Running Worker
1. **Database**: Only Turkish businesses with `state = 'CANDIDATE'` and high confidence scores should be updated to `state = 'VERIFIED'`
2. **API**: `/api/v1/locations/` should return only Turkish businesses (verified locations)
3. **Frontend**: Map and list should display only Turkish businesses
4. **Audit**: All actions logged with Turkish verification enforcement

### Success Criteria
- ✅ `verify_locations.py` runs without errors
- ✅ Database queries show locations with `state = 'VERIFIED'` (Turkish businesses only)
- ✅ API endpoint returns only Turkish businesses
- ✅ Frontend renders only Turkish businesses on map
- ✅ Non-Turkish businesses remain as `CANDIDATE` with audit logs

## Troubleshooting

### Worker Issues
- Check environment variables: `DATABASE_URL`, `OPENAI_API_KEY`
- Verify database connection
- Check OpenAI API key validity

### API Issues
- Verify backend is running on correct port
- Check API endpoint: `/api/v1/locations/`
- Verify database connection in backend

### Frontend Issues
- Check browser console for errors
- Verify API calls are successful
- Check if locations are being filtered correctly

## Smoke Tests

### 1. Environment Check
```bash
cd Backend/
set -a; source ./.env; set +a
echo "DATABASE_URL: $DATABASE_URL"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."
```

### 2. Worker Dry Run
```bash
cd Backend/
python -m app.workers.verify_locations --source OSM_OVERPASS --limit 5 --dry-run 1
```

### 3. Database Verification
```sql
-- Check state distribution
SELECT state, COUNT(*) FROM locations GROUP BY state;

-- Check recently verified Turkish businesses
SELECT id, name, category, source, state, last_verified_at
FROM locations
WHERE state='VERIFIED' AND is_retired=false
ORDER BY last_verified_at DESC
LIMIT 25;
```

### 4. API Smoke Test
```bash
curl -s "http://localhost:8000/api/v1/locations?state=VERIFIED&limit=20" | jq .
```

### 5. Frontend Test
- Start backend: `cd Backend && python -m app.main`
- Start frontend: `cd Frontend && npm run dev`
- Open map on Rotterdam
- Verify only Turkish businesses appear as markers

## Next Steps

1. **Set up environment**: Create `.env` file with proper database connection
2. **Run worker**: Execute verification commands
3. **Verify results**: Check database and API responses
4. **Test frontend**: Ensure only Turkish businesses appear on map
5. **Monitor**: Check audit logs for Turkish verification enforcement

## Notes

- The worker is idempotent and can be run multiple times safely
- Dry-run mode allows testing without making changes
- Chunking supports parallel processing for large datasets
- All actions are logged for audit trail
- **Turkish-only enforcement**: Only Turkish businesses are promoted to VERIFIED
- **API simplification**: No client-side filtering needed - API returns Turkish businesses by design
