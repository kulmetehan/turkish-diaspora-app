---
title: Business Analytics Dashboard
status: active
last_updated: 2025-01-XX
scope: monetization
owners: [tda-core]
---

# Business Analytics Dashboard

## Overview

Business Analytics Dashboard provides business account owners with insights into their claimed locations' performance, engagement metrics, and trending status.

## Requirements

### Key Metrics

1. **Overview Metrics**
   - Total claimed locations
   - Total views (location page views)
   - Total likes/reactions
   - Total check-ins
   - Total notes
   - Trending locations count

2. **Per-Location Metrics**
   - Views over time
   - Engagement breakdown (reactions, check-ins, notes, favorites)
   - Trending status and score
   - Activity timeline

3. **Engagement Metrics**
   - Engagement rate (interactions / views)
   - Most engaged locations
   - Activity trends (daily/weekly/monthly)
   - User demographics (if available)

4. **Trending Analytics**
   - Trending locations list
   - Trending score over time
   - Comparison with other locations
   - Trending factors (check-ins, reactions, etc.)

## Data Sources

### Primary Sources

1. **activity_stream** table
   - All user interactions (check-ins, reactions, notes, favorites)
   - Filtered by location_id and business account's claimed locations
   - Time-series data for trends

2. **business_location_claims** table
   - Links business accounts to locations
   - Claim status (approved locations only)

3. **locations** table
   - Location metadata
   - Trending status (if available)

4. **trending_locations** table (if exists)
   - Trending scores and rankings

### Aggregation Strategy

- Real-time queries for current metrics
- Optional caching table (`business_analytics`) for performance
- Time-windowed aggregations (1 day, 7 days, 30 days, 90 days)

## API Endpoints

### `GET /business/analytics/overview`
Returns overall statistics for the business account:
```json
{
  "total_locations": 5,
  "total_views": 1234,
  "total_engagement": 567,
  "trending_locations": 2,
  "period": "7d"
}
```

### `GET /business/analytics/locations/{location_id}`
Returns detailed metrics for a specific location:
```json
{
  "location_id": 123,
  "views": 456,
  "check_ins": 78,
  "reactions": 45,
  "notes": 12,
  "favorites": 23,
  "trending_score": 0.85,
  "is_trending": true
}
```

### `GET /business/analytics/engagement`
Returns engagement metrics across all locations:
```json
{
  "total_engagement": 567,
  "engagement_rate": 0.46,
  "top_locations": [...],
  "activity_timeline": [...]
}
```

### `GET /business/analytics/trending`
Returns trending statistics:
```json
{
  "trending_locations": [...],
  "trending_scores": [...],
  "comparison_data": {...}
}
```

## Frontend Components

1. **BusinessAnalyticsPage**
   - Overview dashboard with key metrics
   - Time period selector (1d, 7d, 30d, 90d)
   - Charts using recharts library

2. **AnalyticsCard**
   - Reusable metric card component
   - Shows metric value, label, and trend indicator

3. **LocationAnalytics**
   - Per-location detailed view
   - Engagement breakdown charts
   - Activity timeline

## Performance Considerations

- Use database indexes on activity_stream (location_id, created_at)
- Consider materialized views for frequently accessed aggregations
- Implement caching for expensive queries
- Pagination for large datasets

## Privacy & Access Control

- Only business account owners and members can access analytics
- Data filtered by business_account_id
- No access to competitor data
- Respect user privacy (aggregated data only)

## Future Enhancements

- Export analytics to CSV/PDF
- Email reports (weekly/monthly)
- Custom date ranges
- Comparison with industry averages
- Predictive analytics



















