# Investigation Findings - Turkish Diaspora App

**Date:** 2025-01-27  
**Scope:** Read-only investigation of three symptoms  
**Status:** Complete

---

## Executive Summary

Three symptoms were investigated:

1. **Count Mismatch (Part A):** Admin metrics show ~247 VERIFIED locations, but the frontend map displays ~193 markers. Root cause: Admin counts ALL VERIFIED locations within Rotterdam bbox (no confidence/retired filters), while the frontend API filters by `confidence_score >= 0.80` for VERIFIED, excludes `is_retired=true`, and includes high-confidence PENDING_VERIFICATION/CANDIDATE. Additionally, the frontend filters client-side for valid lat/lng coordinates.

2. **CI Cancellation (Part B):** The "TDA Discovery (weekly, chunked)" workflow runs for 1-2 hours then gets canceled. Root cause: The workflow generates 48 sequential jobs (8 categories × 6 chunks) with a 45-minute timeout each, requiring ~36 hours to complete. The workflow runs every 2 hours with `concurrency.group: "tda-discovery"` and `cancel-in-progress: true`, causing each new run to cancel the previous one before completion.

3. **Growth Stall (Part C):** The locations table sits around 6,916 rows. Root cause: Discovery workflows never complete due to cancellation (Part B), so inserts never land. Additionally, aggressive deduplication (`ON CONFLICT (place_id) DO NOTHING` + fuzzy name/lat/lng matching) prevents re-insertion of existing candidates.

---

## Part A: Frontend vs Admin Count Mismatch

### Evidence

#### Admin Metrics Query
**File:** `Backend/services/metrics_service.py:170-217`

The admin metrics `_rotterdam_progress()` function counts VERIFIED locations:

```python
sql_counts = """
    SELECT
      SUM(CASE WHEN state = 'VERIFIED' THEN 1 ELSE 0 END)::int AS verified_count,
      SUM(CASE WHEN state = 'CANDIDATE' THEN 1 ELSE 0 END)::int AS candidate_count
    FROM locations
    WHERE lat BETWEEN $1 AND $2 AND lng BETWEEN $3 AND $4
"""
```

**Key filters:**
- `state = 'VERIFIED'` only
- Bounded to Rotterdam bbox (lat/lng between bounds)
- **No confidence_score filter**
- **No is_retired filter**

#### Frontend API Endpoint
**File:** `Backend/api/routers/locations.py:54-77`

The public `/api/v1/locations` endpoint uses different filters:

```sql
WHERE (
    state = 'VERIFIED'
    AND (confidence_score IS NOT NULL AND confidence_score >= 0.80)
    AND (is_retired = false OR is_retired IS NULL)
) OR (
    state IN ('PENDING_VERIFICATION', 'CANDIDATE')
    AND (confidence_score IS NOT NULL AND confidence_score >= 0.90)
    AND (is_retired = false OR is_retired IS NULL)
)
ORDER BY id DESC
LIMIT $1
```

**Key filters:**
- VERIFIED: `confidence_score >= 0.80` AND `is_retired = false`
- Also includes high-confidence PENDING_VERIFICATION/CANDIDATE (`confidence_score >= 0.90`)
- No bbox filter (returns all locations globally)
- Default limit: 200 (but frontend requests 1000)

#### Frontend Client-Side Filtering
**File:** `Frontend/src/lib/api/location.ts:114-116`

```typescript
const normalized = list
  .map(normalizeLocation)
  .filter((l) => Number.isFinite(l.id) && Number.isFinite(l.lat) && Number.isFinite(l.lng));
```

**Additional filter:**
- Removes locations with null/invalid lat/lng

#### Frontend API Call
**File:** `Frontend/src/lib/api/location.ts:71-91`

```typescript
const params = new URLSearchParams({
  state: "VERIFIED",
  limit: "1000",
  // ...
});
const url = `/locations/?${params.toString()}`;
```

The frontend requests `limit=1000`, but the backend default is 200.

### Root Cause Analysis

The count mismatch occurs because:

1. **Admin counts ALL VERIFIED in Rotterdam bbox** (no confidence/retired filters)
2. **Frontend API filters VERIFIED by confidence >= 0.80 AND is_retired=false**
3. **Frontend API includes high-confidence PENDING_VERIFICATION/CANDIDATE** (not counted by Admin)
4. **Frontend API has no bbox filter** (includes locations outside Rotterdam)
5. **Frontend client-side filters out invalid lat/lng**
6. **Potential limit truncation** if more than 1000 locations match the frontend filters

**Expected delta:**
- Admin ~247 = All VERIFIED in Rotterdam bbox
- Frontend ~193 = VERIFIED with confidence >= 0.80 AND is_retired=false + high-confidence PENDING/CANDIDATE, minus invalid lat/lng

**Missing locations likely include:**
- VERIFIED with confidence < 0.80
- VERIFIED with is_retired=true
- VERIFIED with null/invalid lat/lng

### Verification SQL Queries (Read-Only)

To verify the hypothesis, run these queries in Supabase:

```sql
-- Admin count (matches _rotterdam_progress)
SELECT COUNT(*) AS admin_count
FROM locations
WHERE lat BETWEEN 51.85 AND 51.98
  AND lng BETWEEN 4.35 AND 4.55
  AND state = 'VERIFIED';

-- Frontend API count (VERIFIED only, with filters)
SELECT COUNT(*) AS frontend_verified_count
FROM locations
WHERE state = 'VERIFIED'
  AND (confidence_score IS NOT NULL AND confidence_score >= 0.80)
  AND (is_retired = false OR is_retired IS NULL);

-- Frontend API count (includes PENDING/CANDIDATE)
SELECT COUNT(*) AS frontend_total_count
FROM locations
WHERE (
    state = 'VERIFIED'
    AND (confidence_score IS NOT NULL AND confidence_score >= 0.80)
    AND (is_retired = false OR is_retired IS NULL)
) OR (
    state IN ('PENDING_VERIFICATION', 'CANDIDATE')
    AND (confidence_score IS NOT NULL AND confidence_score >= 0.90)
    AND (is_retired = false OR is_retired IS NULL)
);

-- Count with valid lat/lng (frontend client-side filter)
SELECT COUNT(*) AS frontend_valid_coords_count
FROM locations
WHERE (
    state = 'VERIFIED'
    AND (confidence_score IS NOT NULL AND confidence_score >= 0.80)
    AND (is_retired = false OR is_retired IS NULL)
) OR (
    state IN ('PENDING_VERIFICATION', 'CANDIDATE')
    AND (confidence_score IS NOT NULL AND confidence_score >= 0.90)
    AND (is_retired = false OR is_retired IS NULL)
)
AND lat IS NOT NULL
AND lng IS NOT NULL;

-- Breakdown by confidence score (VERIFIED only, Rotterdam bbox)
SELECT 
  CASE 
    WHEN confidence_score IS NULL THEN 'NULL'
    WHEN confidence_score < 0.80 THEN '< 0.80'
    WHEN confidence_score >= 0.80 THEN '>= 0.80'
  END AS confidence_bucket,
  COUNT(*) AS count
FROM locations
WHERE lat BETWEEN 51.85 AND 51.98
  AND lng BETWEEN 4.35 AND 4.55
  AND state = 'VERIFIED'
GROUP BY confidence_bucket
ORDER BY confidence_bucket;
```

### Next Steps (No Code Changes)

1. Run the verification SQL queries to quantify the deltas
2. Compare Admin count vs Frontend API count with filters applied
3. Identify if limit truncation is occurring (check if frontend count = 1000 exactly)
4. Decide on alignment strategy:
   - Option A: Make Admin metrics match Frontend filters (confidence >= 0.80, exclude retired)
   - Option B: Make Frontend API match Admin metrics (no confidence filter, include retired)
   - Option C: Add separate metrics for both definitions

---

## Part B: "TDA Discovery (weekly, chunked)" Cancellation

### Evidence

#### Workflow Configuration
**File:** `.github/workflows/tda_discovery.yml`

```yaml
name: TDA Discovery (weekly, chunked)

on:
  schedule:
    - cron: "0 */2 * * *"    # every 2 hours

concurrency:
  group: "tda-discovery"
  cancel-in-progress: true

jobs:
  discovery:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    strategy:
      fail-fast: false
      max-parallel: 1
      matrix:
        category: [bakery, restaurant, supermarket, barber, mosque, travel_agency, butcher, fast_food]
        chunk_index: [0, 1, 2, 3, 4, 5]   # 6 chunks
```

**Key configuration:**
- **Schedule:** Every 2 hours (`0 */2 * * *`)
- **Concurrency group:** `tda-discovery` with `cancel-in-progress: true`
- **Matrix:** 8 categories × 6 chunks = **48 jobs total**
- **Job timeout:** 45 minutes each
- **Max parallel:** 1 (jobs run sequentially)

#### Time Calculation

**Total time to complete one workflow run:**
- 48 jobs × 45 minutes = 2,160 minutes = **36 hours**

**Workflow schedule:**
- Runs every 2 hours
- Each run cancels the previous one due to `cancel-in-progress: true`

**Result:**
- Workflow starts at T=0
- At T=2h, new run starts → cancels T=0 run (only ~3-4 jobs completed)
- At T=4h, new run starts → cancels T=2h run (only ~3-4 jobs completed)
- **Cycle repeats indefinitely; workflow never completes**

#### Sequence Diagram

```
Time  | Workflow Run | Jobs Completed | Status
------|-------------|----------------|--------
0:00  | Run A starts | 0/48          | Running
2:00  | Run B starts | ~3/48         | Run A canceled
4:00  | Run C starts | ~3/48         | Run B canceled
6:00  | Run D starts | ~3/48         | Run C canceled
...   | ...          | ...            | ...
```

#### Discovery Bot Implementation
**File:** `Backend/app/workers/discovery_bot.py:317-402`

The discovery bot has a safety timeout of 25 minutes:

```python
safety_timeout_s = 25 * 60  # 25 minutes safety timeout
```

However, the GitHub Actions job timeout is 45 minutes, so the bot may still be running when the next workflow run starts.

### Root Cause

The workflow is **mathematically impossible to complete** because:

1. **48 sequential jobs** × 45 minutes = **36 hours** required
2. **Workflow runs every 2 hours** with `cancel-in-progress: true`
3. **Each new run cancels the previous one** before it can finish
4. **Maximum jobs completed per run:** ~3-4 jobs (out of 48) before cancellation

**The workflow has never completed because it cancels itself every 2 hours.**

### Other Workflows

**File:** `.github/workflows/tda_discovery_fast.yml`

- Uses concurrency group `tda-discovery-fast` (different group, no conflict)
- Runs daily at 2 AM (no overlap with the 2-hour schedule)

### Next Steps (No Code Changes)

1. Review GitHub Actions run history to confirm cancellation pattern
2. Check if any workflow run has ever completed all 48 jobs
3. Consider one of these fixes:
   - **Option A:** Change schedule to run less frequently (e.g., daily or weekly)
   - **Option B:** Reduce matrix size (fewer categories/chunks)
   - **Option C:** Set `cancel-in-progress: false` to allow queuing
   - **Option D:** Use separate concurrency groups per category/chunk
   - **Option E:** Reduce job timeout or optimize discovery bot to complete faster

---

## Part C: Locations Growth Stalled ~6,916

### Evidence

#### Discovery Insert Logic
**File:** `Backend/app/workers/discovery_bot.py:183-235`

```python
async def insert_candidates(rows: List[Dict[str, Any]]) -> int:
    # ...
    for row in rows:
        place_id = row.get("place_id")
        name = row.get("name")
        lat = row.get("lat")
        lng = row.get("lng")
        # Skip if already exists by place_id or fallback fuzzy key
        if await _exists_by_place_id(place_id) or await _exists_by_fuzzy(name, lat, lng):
            continue
        # Insert as new candidate
        sql = """
            INSERT INTO locations (...)
            VALUES (...)
            ON CONFLICT (place_id) DO NOTHING
        """
```

**Deduplication mechanisms:**
1. **Pre-check:** `_exists_by_place_id()` and `_exists_by_fuzzy()` (name + lat/lng rounded to 4 decimals)
2. **Database constraint:** `ON CONFLICT (place_id) DO NOTHING`

#### Fuzzy Deduplication
**File:** `Backend/app/workers/discovery_bot.py:168-181`

```python
async def _exists_by_fuzzy(name: Optional[str], lat: Optional[float], lng: Optional[float]) -> bool:
    sql = """
        SELECT 1 FROM locations
        WHERE LOWER(TRIM(name)) = LOWER(TRIM($1))
          AND ROUND(CAST(lat AS numeric), 4) = ROUND(CAST($2 AS numeric), 4)
          AND ROUND(CAST(lng AS numeric), 4) = ROUND(CAST($3 AS numeric), 4)
        LIMIT 1
    """
```

**Deduplication is aggressive:**
- Exact name match (case-insensitive, trimmed)
- Lat/lng rounded to 4 decimal places (~11 meters precision)

#### Workflow Cancellation Impact
**See Part B for details**

- Discovery workflows never complete due to cancellation
- Only ~3-4 jobs complete per run before cancellation
- **Most inserts never happen because workflows are canceled**

#### Database Schema
**File:** `Infra/supabase/0001_init.sql:18-52`

```sql
CREATE TABLE IF NOT EXISTS public.locations (
    id                  bigserial PRIMARY KEY,
    place_id            text UNIQUE,
    -- ...
    first_seen_at       timestamptz NOT NULL DEFAULT now(),
    -- ...
);
```

The table tracks `first_seen_at` for time-series analysis.

### Root Cause Analysis

Growth is stalled because:

1. **Workflows never complete** (Part B) → Most inserts never happen
2. **Aggressive deduplication** prevents re-insertion of existing candidates
3. **No new areas being discovered** → Grid is exhausted, but workflow cancellation prevents verification

**Hypothesis:**
- The table has ~6,916 rows from initial discovery runs
- Subsequent discovery runs are canceled before inserts complete
- Deduplication prevents re-insertion of existing candidates
- **Net result: No growth because workflows are canceled**

### Verification SQL Queries (Read-Only)

To verify the hypothesis, run these queries in Supabase:

```sql
-- Daily inserts over last 60 days
SELECT 
  date_trunc('day', first_seen_at)::date AS day,
  COUNT(*) AS new_locations
FROM locations
WHERE first_seen_at >= NOW() - INTERVAL '60 days'
GROUP BY day
ORDER BY day DESC;

-- Total locations by state
SELECT 
  state,
  COUNT(*) AS count
FROM locations
GROUP BY state
ORDER BY count DESC;

-- Recent inserts (last 14 days)
SELECT COUNT(*) AS recent_inserts
FROM locations
WHERE first_seen_at >= NOW() - INTERVAL '14 days';

-- Duplicate detection (same name + lat/lng)
SELECT 
  LOWER(TRIM(name)) AS normalized_name,
  ROUND(CAST(lat AS numeric), 4) AS rounded_lat,
  ROUND(CAST(lng AS numeric), 4) AS rounded_lng,
  COUNT(*) AS duplicate_count
FROM locations
WHERE lat IS NOT NULL AND lng IS NOT NULL
GROUP BY normalized_name, rounded_lat, rounded_lng
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 20;

-- Locations by source/provider
SELECT 
  source,
  COUNT(*) AS count
FROM locations
GROUP BY source
ORDER BY count DESC;
```

### Next Steps (No Code Changes)

1. Run the verification SQL queries to confirm growth stall
2. Check `first_seen_at` distribution to identify when growth stopped
3. Review GitHub Actions logs to count actual inserts per canceled run
4. Consider one of these fixes:
   - **Option A:** Fix workflow cancellation (Part B) to allow completion
   - **Option B:** Reduce deduplication aggressiveness (allow re-insertion with updates)
   - **Option C:** Expand city grid or add new cities to discover
   - **Option D:** Add metrics to track deduplication rate (inserts vs skipped)

---

## Summary of Root Causes

| Symptom | Root Cause | Evidence |
|---------|-----------|----------|
| **Count Mismatch** | Admin counts ALL VERIFIED (no confidence/retired filters), Frontend filters by confidence >= 0.80 and excludes retired | Different SQL queries, different filters |
| **CI Cancellation** | 48 jobs × 45 min = 36 hours required, but workflow runs every 2 hours with `cancel-in-progress: true` | Workflow config, time calculation |
| **Growth Stall** | Workflows never complete (Part B) + aggressive deduplication prevents re-insertion | Discovery bot code, ON CONFLICT, fuzzy matching |

---

## Recommended Next Steps (No Code Changes Yet)

1. **Run verification SQL queries** to quantify the deltas and confirm hypotheses
2. **Review GitHub Actions run history** to confirm cancellation pattern
3. **Check database time-series** to identify when growth stopped
4. **Decide on alignment strategy** for each symptom:
   - Part A: Choose Admin vs Frontend filter definition
   - Part B: Choose workflow scheduling/concurrency strategy
   - Part C: Fix Part B first, then consider deduplication adjustments

---

## Files Referenced

- `Backend/services/metrics_service.py` - Admin metrics calculation
- `Backend/api/routers/locations.py` - Frontend API endpoint
- `Frontend/src/lib/api/location.ts` - Frontend API client
- `Frontend/src/components/MarkerLayer.tsx` - Map clustering
- `.github/workflows/tda_discovery.yml` - Discovery workflow
- `Backend/app/workers/discovery_bot.py` - Discovery bot implementation
- `Infra/supabase/0001_init.sql` - Database schema

---

**Investigation completed. No code changes made. Ready for review and decision on fixes.**

