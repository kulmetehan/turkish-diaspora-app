# OSM Discovery Provider

This document describes the OSM (OpenStreetMap) provider integration for the Turkish Diaspora App discovery system.

## Overview

The OSM provider uses the Overpass API to discover places of interest, providing an alternative to Google Places API. This allows for cost-effective discovery without API rate limits or costs.

## Configuration

### Environment Variables

Set the following environment variables to use the OSM provider:

```bash
DATA_PROVIDER=osm
OVERPASS_ENDPOINT=https://overpass-api.de/api/interpreter
OVERPASS_TIMEOUT_S=25
DISCOVERY_RATE_LIMIT_QPS=0.5
```

### Provider Selection

The system automatically selects the provider based on the `DATA_PROVIDER` environment variable:
- `google` (default): Uses Google Places API
- `osm`: Uses Overpass API

## OSM Tag Mapping

Categories in `Infra/config/categories.yml` now support `osm_tags` configuration:

```yaml
categories:
  bakery:
    google_types:
      - "bakery"
    osm_tags:
      any:
        - { shop: "bakery" }
  
  mosque:
    google_types:
      - "mosque"
      - "place_of_worship"
    osm_tags:
      all:
        - { amenity: "place_of_worship" }
        - { religion: "muslim" }
```

### Tag Structure

- `any`: OR conditions - any of the specified tags will match
- `all`: AND conditions - all specified tags must match

## Rate Limiting

The OSM provider implements rate limiting to be respectful to the Overpass API:

- **Default rate**: 0.5 requests per second
- **Configurable**: Set via `DISCOVERY_RATE_LIMIT_QPS` environment variable
- **Token bucket**: Implements token bucket algorithm for smooth rate limiting
- **Retry logic**: Automatically retries on 429 responses with `Retry-After` header

## Usage

### Running Discovery with OSM

```bash
# Set environment
export DATA_PROVIDER=osm

# Run discovery bot
python -m app.workers.discovery_bot \
  --city rotterdam \
  --categories bakery,restaurant,supermarket \
  --nearby-radius-m 1000 \
  --grid-span-km 8 \
  --max-cells-per-category 30 \
  --max-total-inserts 200 \
  --inter-call-sleep-s 0.3 \
  --language nl
```

### Dry Run (Limited Results)

For testing, use a smaller scope:

```bash
export DATA_PROVIDER=osm
python -m app.workers.discovery_bot \
  --city rotterdam \
  --categories bakery,restaurant \
  --nearby-radius-m 500 \
  --grid-span-km 4 \
  --max-cells-per-category 10 \
  --max-total-inserts 50
```

## Validation

### OSM Mapping Validator

Validate the OSM tag configuration:

```bash
python Backend/scripts/validate_osm_mapping.py
```

This script checks:
- All categories have `osm_tags`
- `osm_tags` structure is valid
- Tag key-value pairs are non-empty strings

### Expected Output

```
🔍 Validating OSM mapping in categories.yml...

📊 Validation Results:
  Total categories: 6
  Categories with osm_tags: 6
  Validation errors: 0

✅ All categories have valid osm_tags configuration!
```

## Data Normalization

The OSM provider normalizes Overpass API results to match the internal place schema:

```json
{
  "id": "node/123456789",
  "displayName": {"text": "Bakkerij Ali"},
  "formattedAddress": "Hoofdstraat 123, 3011 Rotterdam",
  "location": {"lat": 51.9244, "lng": 4.4777},
  "types": ["shop=bakery"],
  "rating": null,
  "userRatingCount": null,
  "businessStatus": null,
  "websiteUri": "https://example.com"
}
```

## Logging

All OSM operations are logged with structured JSON:

```json
{
  "event": "osm_search_start",
  "provider": "osm",
  "lat": 51.9244,
  "lng": 4.4777,
  "radius": 1000,
  "max_results": 20
}
```

## Known Limitations

1. **Coordinate Precision**: OSM data may have lower coordinate precision than Google Places
2. **Business Hours**: OSM doesn't provide business hours information
3. **Ratings**: OSM doesn't have user ratings or review counts
4. **Real-time Data**: OSM data may be less frequently updated than Google Places

## Troubleshooting

### Common Issues

1. **Timeout Errors**: Increase `OVERPASS_TIMEOUT_S` if queries timeout
2. **Rate Limiting**: Reduce `DISCOVERY_RATE_LIMIT_QPS` if getting 429 errors
3. **No Results**: Check OSM tag mapping in categories.yml

### Debug Mode

Enable debug logging to see detailed query information:

```bash
export LOG_LEVEL=DEBUG
python -m app.workers.discovery_bot --city rotterdam --categories bakery
```

## Performance Considerations

- **Query Complexity**: Complex queries with many tags may timeout
- **Rate Limiting**: Respect the 0.5 QPS default to avoid being blocked
- **Grid Size**: Smaller grid cells may return more accurate results
- **Category Selection**: Limit categories to reduce query complexity

## Support

For issues with OSM discovery:
1. Check the validation script output
2. Review structured logs for error details
3. Verify environment variable configuration
4. Test with a single category first
