# Viewport BBox Filtering - Manual QA Test Plan

This document outlines manual QA steps to verify the viewport/bbox filtering implementation and CORS configuration.

## Quick QA Checklist (Non-Developer)

- Open https://kulmetehan.github.io/turkish-diaspora-app/ → within 1 second orange markers appear and stay visible.
- Pan and zoom the map → no white flash or marker wipe; markers update smoothly.
- Click the "X" / back button in the detail panel → panel closes, the page does **not** reload.
- Optional: open DevTools → Console and confirm there is only **one** `style.load` log within the first second, and `setData` logs show a non-zero feature count.

## Prerequisites

1. Backend server running on `http://127.0.0.1:8000` (or configured API base URL)
2. Frontend dev server running
3. Database with test locations including:
   - Location ID 1314 ("Şerifoğlu Rotterdam") at (51.8867507, 4.4875573)
   - Location ID 1316 ("Ganii Kebap") at (51.8881570, 4.4882612)
   - Other locations distributed across the map

## Test Cases

### 1. Zoomed In - All Markers in View Appear

**Objective**: Verify that when zoomed into a specific area, all locations within the viewport are displayed.

**Steps**:
1. Open the application in a browser
2. Navigate to Rotterdam area (around coordinates 51.92, 4.48)
3. Zoom in to a level where you can see individual markers (zoom level > 14)
4. Pan the map to ensure locations 1314 and 1316 are both in view

**Expected Results**:
- Both location 1314 ("Şerifoğlu Rotterdam") and 1316 ("Ganii Kebap") should be visible as markers on the map
- All other locations within the viewport should also be visible
- No locations outside the viewport should be visible
- Loading indicator should appear briefly when viewport changes

**Pass Criteria**: All locations within the viewport are displayed, including both 1314 and 1316 when they are in view.

---

### 2. Pan Map - Refetch Triggers, Stale Response Discarded

**Objective**: Verify that panning the map triggers a new API request and that stale responses are properly discarded.

**Steps**:
1. Open browser DevTools → Network tab
2. Filter network requests to show only requests to `/api/v1/locations`
3. Zoom into an area with visible markers
4. Pan the map quickly in different directions
5. Observe the network requests

**Expected Results**:
- New API requests are made when the map stops panning (after debounce delay)
- Requests include `bbox` query parameter with current viewport bounds
- Previous in-flight requests are cancelled (check for cancelled requests in Network tab)
- Only the latest response updates the map markers
- Loading indicator appears during fetch operations

**Pass Criteria**: 
- Requests are debounced (not fired on every move event)
- Stale requests are cancelled
- Map updates only with the latest response

---

### 3. Fully Zoomed Out - All Locations Appear (Pagination)

**Objective**: Verify that when fully zoomed out, all available locations are loaded, including pagination if needed.

**Steps**:
1. Open browser DevTools → Network tab
2. Filter network requests to show only requests to `/api/v1/locations` and `/api/v1/locations/count`
3. Zoom out completely (zoom level <= 2 or view entire country/world)
4. Observe network requests and map markers

**Expected Results**:
- First, a request to `/api/v1/locations/count` is made (without bbox parameter)
- Then, requests to `/api/v1/locations` are made with pagination (limit=10000, offset=0, etc.)
- If total count > 10000, multiple paginated requests are made
- All locations in the database (subject to filters) are displayed on the map
- Loading indicator shows progress during pagination

**Pass Criteria**:
- Count endpoint is called first
- Pagination works correctly (multiple pages if needed)
- All locations are eventually displayed
- No duplicate markers appear

---

### 4. Filters Combined with Bbox

**Objective**: Verify that search and category filters work correctly in combination with bbox filtering.

**Steps**:
1. Zoom into an area with multiple locations
2. Apply a category filter (e.g., "restaurant")
3. Apply a search filter (e.g., type a location name)
4. Pan the map to a different area
5. Observe the filtered results

**Expected Results**:
- Category filter works: only locations matching the category are shown
- Search filter works: only locations matching the search query are shown
- Filters are applied to the bbox-filtered results (client-side filtering)
- When panning, new locations are fetched based on bbox, then filtered by category/search
- Filtered list updates correctly as viewport changes

**Pass Criteria**:
- Filters work correctly with bbox filtering
- No locations appear that don't match the filters
- Filtering happens after bbox fetch (client-side)

---

### 5. Regression Test - Locations 1314 and 1316 Both Render

**Objective**: Verify that the original issue (location 1314 not rendering) is fixed.

**Steps**:
1. Navigate to Rotterdam area
2. Zoom in to a level where both locations 1314 and 1316 should be visible
3. Ensure both locations are within the viewport
4. Check the map for markers
5. Check the browser console for any errors

**Expected Results**:
- Both location 1314 ("Şerifoğlu Rotterdam") and 1316 ("Ganii Kebap") are visible as markers
- Both markers are clickable and show correct information
- No console errors related to feature IDs or rendering
- Both locations appear in the location list when filtered

**Pass Criteria**: Both locations 1314 and 1316 render correctly when in viewport.

---

### 6. Edge Cases

#### 6.1 Empty Viewport / No Locations in Bbox

**Steps**:
1. Pan to an area with no locations (e.g., ocean or remote area)
2. Observe the map and list

**Expected Results**:
- Map shows no markers
- Location list is empty
- No errors in console
- Loading indicator appears and disappears

**Pass Criteria**: Application handles empty results gracefully.

#### 6.2 Rapid Panning/Zooming

**Steps**:
1. Rapidly pan and zoom the map multiple times
2. Observe network requests and map behavior

**Expected Results**:
- Requests are properly debounced
- Stale requests are cancelled
- Map eventually shows correct markers for final viewport
- No memory leaks or performance issues

**Pass Criteria**: Application handles rapid viewport changes without issues.

#### 6.3 Invalid Bbox Parameter (Backend Test)

**Steps**:
1. Manually test API endpoint with invalid bbox:
   - `GET /api/v1/locations?bbox=invalid`
   - `GET /api/v1/locations?bbox=4.1,51.8` (too few values)
   - `GET /api/v1/locations?bbox=4.7,51.8,4.1,52.0` (west >= east)
   - `GET /api/v1/locations?bbox=4.1,52.0,4.7,51.8` (south >= north)

**Expected Results**:
- All invalid bbox parameters return HTTP 400 with clear error messages
- Error messages indicate what's wrong with the bbox parameter

**Pass Criteria**: Backend properly validates bbox parameter and returns appropriate errors.

---

## Browser Console Checks

During testing, check the browser console for:

1. **No errors**: Should be no JavaScript errors or warnings
2. **Network requests**: Verify bbox parameter is included in requests
3. **Feature IDs**: Verify GeoJSON features have top-level `id` property (check in Network response)

## Network Request Verification

In DevTools Network tab, verify:

1. **Request URL format**: 
   - With bbox: `/api/v1/locations?bbox=4.1,51.8,4.7,52.0&limit=1000&offset=0`
   - Without bbox (zoomed out): `/api/v1/locations?limit=10000&offset=0`
   - Count endpoint: `/api/v1/locations/count` or `/api/v1/locations/count?bbox=...`

2. **Request cancellation**: Check for cancelled requests when viewport changes rapidly

3. **Response times**: Verify responses are reasonable (< 1-2 seconds for typical queries)

## Performance Checks

1. **Initial load**: Map should load and display markers within 2-3 seconds
2. **Viewport changes**: New markers should appear within 1-2 seconds after pan/zoom stops
3. **Memory usage**: No memory leaks after extended use (pan/zoom for 5+ minutes)
4. **Network efficiency**: No unnecessary duplicate requests

## Regression Checklist

- [ ] Locations 1314 and 1316 both render when in viewport
- [ ] No console errors
- [ ] Map clustering still works correctly
- [ ] Location selection (clicking markers) still works
- [ ] Location list updates correctly
- [ ] Search and category filters still work
- [ ] Mobile view works correctly
- [ ] Desktop view works correctly

## CORS Verification

### Browser Console/Network Checks

1. **Open DevTools → Network tab** when accessing the app from https://kulmetehan.github.io
2. **Filter by "locations"** to see API requests
3. **Check Response Headers** for:
   - `Access-Control-Allow-Origin: https://kulmetehan.github.io` (should be present)
   - `Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD`
   - `Access-Control-Allow-Headers: *`

### Curl Verification Commands

#### Preflight Check (OPTIONS)
```bash
curl -i -X OPTIONS "https://turkish-diaspora-app.onrender.com/api/v1/locations" \
  -H "Origin: https://kulmetehan.github.io" \
  -H "Access-Control-Request-Method: GET"
```

**Expected Response:**
```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://kulmetehan.github.io
Access-Control-Allow-Methods: GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD
Access-Control-Allow-Headers: *
```

#### Actual Request with Origin
```bash
curl -i "https://turkish-diaspora-app.onrender.com/api/v1/locations/count?bbox=4.35,51.84,4.60,52.00" \
  -H "Origin: https://kulmetehan.github.io"
```

**Expected Response:**
```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://kulmetehan.github.io
Content-Type: application/json

{"count": <number>}
```

#### Health Endpoint Check
```bash
curl -i "https://turkish-diaspora-app.onrender.com/health"
```

**Expected Response:**
```
HTTP/1.1 200 OK
Content-Type: application/json

{"ok": true}
```

#### HEAD Root Endpoint Check
```bash
curl -i -X HEAD "https://turkish-diaspora-app.onrender.com/"
```

**Expected Response:**
```
HTTP/1.1 200 OK
```

## Notes

- The debounce delay is set to 200ms - viewport changes should trigger requests after user stops panning/zooming
- When fully zoomed out, the app fetches all locations with pagination (up to 10,000 per page)
- Bbox format is `west,south,east,north` in WGS84 degrees
- The implementation uses AbortController to cancel in-flight requests
- CORS middleware is configured to allow requests from https://kulmetehan.github.io
- Programmatic map movements (e.g., when selecting a location) do not trigger viewport change callbacks to prevent infinite loops

