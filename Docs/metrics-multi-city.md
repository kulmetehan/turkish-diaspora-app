---
title: Multi-City Metrics
status: active
last_updated: 2025-01-XX
scope: backend, frontend, admin
owners: [tda-core]
---

# Multi-City Metrics

This document explains how multi-city metrics work in the Turkish Diaspora App, from city configuration to metrics computation to admin dashboard display.

## City Configuration

Cities are defined in `Infra/config/cities.yml` with the following structure:

```yaml
cities:
  rotterdam:
    city_name: "Rotterdam"
    country: "NL"
    districts:
      centrum:
        lat_min: 51.9150
        lat_max: 51.9350
        lng_min: 4.4500
        lng_max: 4.4950
      # ... more districts
  vlaardingen:
    city_name: "Vlaardingen"
    country: "NL"
    districts:
      centrum:
        lat_min: 51.9000
        lat_max: 51.9250
        # ... bbox
```

**Requirements for metrics:**
- Cities must have `districts` defined with bounding boxes (`lat_min`, `lat_max`, `lng_min`, `lng_max`)
- Cities without districts are skipped in metrics computation (can't compute bbox)
- Each district's bbox is used to compute the union bbox for the entire city

## Metrics Computation

### Backend: `metrics_service.py`

The `_city_progress(city_key: str)` function:

1. **Loads city from `cities.yml`** via `load_cities_config()`
2. **Computes union bbox** from all districts using `_compute_city_bbox(city_key)`
3. **Queries locations** using the shared verified filter (`get_verified_filter_sql`)
4. **Returns `CityProgressData`** with:
   - `verified_count` - Locations matching verified filter (state=VERIFIED, confidence≥0.80, etc.)
   - `candidate_count` - Locations with state=CANDIDATE within bbox
   - `coverage_ratio` - verified_count / (verified_count + candidate_count)
   - `growth_weekly` - Percentage growth comparing current week vs previous week

### Multi-City Snapshot

`generate_metrics_snapshot()`:

1. Loads all cities from `cities.yml`
2. For each city with districts:
   - Calls `_city_progress(city_key)`
   - Adds to `city_progress.cities` dict
3. Returns `MetricsSnapshot` with `city_progress: CityProgress(cities={...})`

**Error handling:**
- Cities without districts are skipped (logged as warning)
- If all cities fail, falls back to Rotterdam only
- Missing `cities.yml` file raises exception

## API Endpoints

### GET `/api/v1/admin/metrics/snapshot`

Returns metrics snapshot with multi-city support:

```json
{
  "city_progress": {
    "cities": {
      "rotterdam": {
        "verified_count": 150,
        "candidate_count": 50,
        "coverage_ratio": 0.75,
        "growth_weekly": 5.2
      },
      "vlaardingen": {
        "verified_count": 20,
        "candidate_count": 10,
        "coverage_ratio": 0.67,
        "growth_weekly": 10.0
      }
    }
  }
}
```

**Backward compatibility:**
- The response also includes `rotterdam` as a direct field for legacy clients
- Frontend normalization handles both structures

### GET `/api/v1/admin/cities`

Returns city overview with readiness status:

```json
{
  "cities": [
    {
      "city_key": "rotterdam",
      "city_name": "Rotterdam",
      "has_districts": true,
      "districts_count": 11,
      "verified_count": 150,
      "candidate_count": 50,
      "coverage_ratio": 0.75,
      "growth_weekly": 5.2,
      "readiness_status": "active",
      "readiness_notes": "City is active with discovery and verification running."
    }
  ]
}
```

## Frontend Admin Dashboard

### City Selector

The admin dashboard (`MetricsDashboard.tsx`) includes:

1. **City selector dropdown** - Loads cities from `/api/v1/admin/cities`
2. **Dynamic metrics display** - Shows metrics for selected city
3. **Worker run controls** - Uses selected city when triggering discovery/verification

### Metrics Display

- **Verified count card** - Shows count for selected city
- **Coverage ratio** - Shows coverage for selected city
- **Weekly growth** - Shows growth for selected city
- All metrics update when city selector changes

### Worker Controls

When running workers (discovery, classify, verify), the selected city is passed to the backend:

```typescript
const payload = {
  bot: "discovery",
  city: selectedCity, // e.g., "vlaardingen"
  category: selectedCategory,
};
```

## Adding a New City

To add a new city (e.g., Den Haag) to metrics:

### 1. Add to `cities.yml`

```yaml
den_haag:
  city_name: "Den Haag"
  country: "NL"
  districts:
    centrum:
      lat_min: 52.0700
      lat_max: 52.0900
      lng_min: 4.2900
      lng_max: 4.3200
    # ... more districts
```

### 2. Verify Metrics

- Metrics will automatically include the new city once districts are defined
- Check `/api/v1/admin/metrics/snapshot` to verify city appears in `city_progress.cities`
- Check `/api/v1/admin/cities` to verify readiness status

### 3. Frontend (Automatic)

- City selector will automatically include the new city
- No frontend code changes needed

## Troubleshooting

**City not appearing in metrics:**
- Verify city has `districts` defined in `cities.yml`
- Check that districts have valid bbox (lat_min < lat_max, lng_min < lng_max)
- Check backend logs for `failed_to_compute_city_bbox` warnings

**Metrics showing zero for a city:**
- Verify locations exist in the database within the city's bbox
- Check that locations have correct state (VERIFIED for verified_count, CANDIDATE for candidate_count)
- Verify bbox coordinates are correct (use a map tool to visualize)

**City selector empty:**
- Check that `/api/v1/admin/cities` endpoint returns cities
- Verify cities have `has_districts: true` (only cities with districts appear in selector)
- Check browser console for API errors

## Performance Considerations

- Metrics computation queries all locations within bbox - ensure indexes exist on `lat`, `lng`, `state`
- For cities with many districts, union bbox computation is O(n) where n = number of districts
- Metrics snapshot generation is sequential per city - consider parallelization if >10 cities

## Future Enhancements

- **Caching**: Cache city progress metrics for 5-10 minutes to reduce DB load
- **Parallel computation**: Compute metrics for multiple cities in parallel
- **District-level metrics**: Show metrics per district, not just per city
- **Historical trends**: Track city metrics over time (daily/weekly snapshots)







